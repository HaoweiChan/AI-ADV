#!/bin/tcsh

# Source the environment setup script
source scripts/setup_env.sh

# Set default port and host
if ( ! $?PORT ) then
    setenv PORT 8000
endif
if ( ! $?HOST ) then
    setenv HOST 0.0.0.0
endif

echo "Starting Hierarchy Matching API server..."
echo "Host: $HOST"
echo "Port: $PORT"
echo ""

# Build python command
set python_cmd = "python3 -m uvicorn api.server:app --host $HOST --port $PORT --reload"

# Execute based on flag
if ($bsub_flag == 1) then
    module load LSF/mtkgpu
    bsub -Is -J HierAPI -q ML_CPU -app ML_CPU -P d_09017 "$python_cmd"
else if ($utilq_flag == 1) then
    utilq -Is -J hier_api "$python_cmd"
else
    setenv CUDA_VISIBLE_DEVICES ""
    eval "$python_cmd"
endif
