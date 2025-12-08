"""FastAPI server for hierarchy matching API."""

import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from agents.hierarchy_matching_agent import HierarchyMatchingAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Hierarchy Matching API",
    description="API for matching hierarchical paths between golden and target netlists",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class HierarchyMatchingOptions(BaseModel):
    """Options for hierarchy matching."""

    model: str = Field(
        default="llama3.3-70b-instruct",
        description="LLM model to use for matching",
    )
    verbose: bool = Field(default=False, description="Enable verbose output")
    dry_run: bool = Field(
        default=False,
        description="Validate inputs without processing",
    )


class HierarchyMatchingRequest(BaseModel):
    """Request model for hierarchy matching API."""

    version: int = Field(default=1, ge=1, description="API version number")
    target_netlist: str = Field(
        ...,
        description="Path to the target netlist file",
    )
    target_bench_path: Optional[str] = Field(
        default=None,
        description="Path to the target testbench directory",
    )
    target_bench_type: str = Field(
        default="maestro",
        description="Type of target testbench",
    )
    golden_netlist_dict: Dict[str, str] = Field(
        ...,
        description="Dictionary mapping golden identifiers to netlist file paths",
    )
    golden_bench_path: Optional[str] = Field(
        default=None,
        description="Path to the golden testbench directory",
    )
    golden_bench_type: str = Field(
        default="maestro",
        description="Type of golden testbench",
    )
    instance_paths: List[str] = Field(
        default_factory=list,
        description="List of hierarchical instance paths to resolve",
    )
    options: HierarchyMatchingOptions = Field(
        default_factory=HierarchyMatchingOptions,
        description="Additional processing options",
    )

    @field_validator("golden_netlist_dict")
    @classmethod
    def validate_golden_dict_not_empty(cls, v: Dict[str, str]) -> Dict[str, str]:
        if not v:
            raise ValueError("golden_netlist_dict must have at least one entry")
        return v


class HierarchyMatchingResponse(BaseModel):
    """Response model for hierarchy matching API."""

    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    errors: Optional[List[str]] = None


class PathResolutionRequest(BaseModel):
    """Request model for single path resolution."""

    instance_path: str = Field(
        ...,
        description="Hierarchical instance path to resolve",
    )
    golden_key: Optional[str] = Field(
        default=None,
        description="Specific golden netlist key to use",
    )


class PathResolutionResponse(BaseModel):
    """Response model for path resolution."""

    input_path: str
    resolved_path: str
    golden_key: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# Global agent instance (initialized on first request)
_agent_instance: Optional[HierarchyMatchingAgent] = None
_agent_config: Optional[Dict[str, Any]] = None


def get_agent(config: Dict[str, Any]) -> HierarchyMatchingAgent:
    """Get or create agent instance with given config."""
    global _agent_instance, _agent_config

    # Check if we need to reinitialize
    config_key = {
        "target_netlist": config.get("target_netlist"),
        "golden_netlist_dict": str(config.get("golden_netlist_dict")),
    }
    if _agent_instance is None or _agent_config != config_key:
        _agent_instance = HierarchyMatchingAgent(config=config.get("options", {}))
        _agent_instance.llm_client = _agent_instance._init_llm_client()
        _agent_instance._load_netlists(
            config["target_netlist"],
            config["golden_netlist_dict"],
        )
        _agent_config = config_key

    return _agent_instance


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "service": "Hierarchy Matching API",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/v1/hierarchy-matching", response_model=HierarchyMatchingResponse)
async def hierarchy_matching(request: HierarchyMatchingRequest) -> HierarchyMatchingResponse:
    """
    Process hierarchy matching request.

    This endpoint accepts a JSON payload containing target and golden netlist paths,
    along with instance paths to resolve. It returns the matching paths in the
    golden netlists.
    """
    logger.info(f"Received hierarchy matching request: version={request.version}")
    logger.info(f"Target netlist: {request.target_netlist}")
    logger.info(f"Golden netlists: {list(request.golden_netlist_dict.keys())}")

    # Check if dry run
    if request.options.dry_run:
        return HierarchyMatchingResponse(
            success=True,
            message="Dry run validation passed",
            data={
                "target_netlist": request.target_netlist,
                "golden_netlist_dict": request.golden_netlist_dict,
                "instance_paths": request.instance_paths,
            },
        )

    # Validate file existence
    if not os.path.exists(request.target_netlist):
        raise HTTPException(
            status_code=400,
            detail=f"Target netlist not found: {request.target_netlist}",
        )
    for key, path in request.golden_netlist_dict.items():
        if not os.path.exists(path):
            raise HTTPException(
                status_code=400,
                detail=f"Golden netlist [{key}] not found: {path}",
            )

    try:
        # Initialize agent
        agent = HierarchyMatchingAgent(
            config={
                "model": request.options.model,
            }
        )

        # Prepare state
        state = {
            "input_data": {
                "target_netlist": request.target_netlist,
                "golden_netlist_dict": request.golden_netlist_dict,
                "instance_paths": request.instance_paths,
                "model": request.options.model,
            }
        }

        # Process
        result = agent.process(state)

        if result.get("errors"):
            return HierarchyMatchingResponse(
                success=False,
                message="Processing completed with errors",
                data=result.get("analysis_results"),
                errors=result.get("errors"),
            )

        return HierarchyMatchingResponse(
            success=True,
            message="Hierarchy matching completed successfully",
            data={
                "analysis_results": result.get("analysis_results"),
                "report": result.get("report"),
                "metadata": {
                    "target_bench_path": request.target_bench_path,
                    "target_bench_type": request.target_bench_type,
                    "golden_bench_path": request.golden_bench_path,
                    "golden_bench_type": request.golden_bench_type,
                },
            },
        )

    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/resolve-path", response_model=PathResolutionResponse)
async def resolve_single_path(
    request: PathResolutionRequest,
    target_netlist: str,
    golden_netlist_dict: str,
) -> PathResolutionResponse:
    """
    Resolve a single hierarchical path.

    This is a lightweight endpoint for resolving individual paths
    after the netlists have been loaded.
    """
    try:
        # Parse golden_netlist_dict from JSON string
        golden_dict = json.loads(golden_netlist_dict)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid golden_netlist_dict JSON: {e}",
        )

    config = {
        "target_netlist": target_netlist,
        "golden_netlist_dict": golden_dict,
    }

    try:
        agent = get_agent(config)
        result = agent.resolve_path(request.instance_path, request.golden_key)

        return PathResolutionResponse(
            input_path=request.instance_path,
            resolved_path=result.get("resolved_path", "N/A"),
            golden_key=request.golden_key,
            details=result.get("steps"),
        )

    except Exception as e:
        logger.error(f"Error resolving path: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/subcircuits")
async def list_subcircuits(netlist_path: str) -> Dict[str, Any]:
    """
    List subcircuits in a netlist file.

    Useful for exploring available cells before running hierarchy matching.
    """
    if not os.path.exists(netlist_path):
        raise HTTPException(
            status_code=400,
            detail=f"Netlist file not found: {netlist_path}",
        )

    try:
        # Import here to avoid circular imports
        from tools.spice_parser import SpiceParser

        parser = SpiceParser(netlist_path)
        return {
            "netlist_path": netlist_path,
            "subcircuits": list(parser.subckts.keys()),
            "count": len(parser.subckts),
        }

    except Exception as e:
        logger.error(f"Error parsing netlist: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

