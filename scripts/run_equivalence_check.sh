#!/bin/tcsh

# Source the environment setup script
source scripts/setup_env.sh

# Parse arguments
# We pass all arguments directly to the python script, except flags handled by setup_env (though setup_env eats them?)
# setup_env parses --bsub and --utilq. We should pass the remaining args to python.
# But setup_env consumes argv? No, it iterates $argv but doesn't shift them out unless modified.
# Actually, setup_env.sh in csh typically doesn't modify the parent shell's argv unless it uses set argv = ...
# The provided setup_env.sh iterates $argv to set flags but doesn't seem to modify it.
# However, we need to filter out --bsub and --utilq before passing to python?
# Or python argparse will complain.

set python_args = ""
foreach arg ($argv)
    if ( "$arg" != "--bsub" && "$arg" != "--utilq" ) then
        set python_args = "$python_args $arg"
    endif
end

# Build python command
set python_cmd = "python3 equivalence_check_cli.py $python_args"

# Execute based on flag
if ($bsub_flag == 1) then
    module load LSF/mtkgpu
    bsub -Is -J EqCheck -q ML_CPU -app ML_CPU -P d_09017 "$python_cmd"
else if ($utilq_flag == 1) then
    utilq -Is -J eq_check "$python_cmd"
else
    setenv CUDA_VISIBLE_DEVICES ""
    eval "$python_cmd"
endif

