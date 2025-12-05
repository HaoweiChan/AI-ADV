#!/bin/tcsh

# Source the environment setup script
source scripts/setup_env.sh

# Parse arguments - filter out --bsub and --utilq before passing to python
set python_args = ""
foreach arg ($argv)
    if ( "$arg" != "--bsub" && "$arg" != "--utilq" ) then
        set python_args = "$python_args $arg"
    endif
end

# Build python command
set python_cmd = "python3 hierarchy_matching_cli.py $python_args"

# Execute based on flag
if ($bsub_flag == 1) then
    module load LSF/mtkgpu
    bsub -Is -J LongJob -q ML_CPU -app ML_CPU -P Develop "$python_cmd"
else if ($utilq_flag == 1) then
    utilq -Is -J shortjob_big "$python_cmd"
else
    setenv CUDA_VISIBLE_DEVICES ""
    eval "$python_cmd"
endif
