#!/bin/tcsh

# Source the environment setup script
# This will handle module loading, virtualenv, and flag parsing
source scripts/setup_env.sh

# Build python command
set python_cmd = "python3 examples/tests/test_llm.py"

# Execute based on flag
if ($bsub_flag == 1) then
    module load LSF/mtkgpu
    bsub -Is -J LongJob -q ML_CPU -app ML_CPU -P d_09017 "$python_cmd"
else if ($utilq_flag == 1) then
    utilq -Is -J shortjob_big "$python_cmd"
else
    setenv CUDA_VISIBLE_DEVICES ""
    eval "$python_cmd"
endif

