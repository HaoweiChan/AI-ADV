"""Shared agent interfaces for the template."""

from .base_agent import AgentState, BaseAgent
from .equivalence_check_agent import EquivalenceCheckAgent
from .hierarchy_matching_agent import HierarchyMatchingAgent

__all__ = [
    "AgentState",
    "BaseAgent",
    "EquivalenceCheckAgent",
    "HierarchyMatchingAgent",
]



