#!/bin/tcsh

# Source the environment setup script
# This will handle module loading, virtualenv, and flag parsing
source scripts/setup_env.sh

# USER CONFIGURATION:
# Configure Streamlit port and options here
set port = "8501"
set host = "localhost"

# Parse command line arguments
set i = 1
while ($i <= $#argv)
    set arg = $argv[$i]
    if ( "$arg" == "--bsub" || "$arg" == "--utilq" ) then
        # These are handled by setup_env.sh
        @ i++
        continue
    else if ( "$arg" == "--port" || "$arg" == "-p" ) then
        @ i++
        set port = $argv[$i]
    else if ( "$arg" == "--host" || "$arg" == "-h" ) then
        @ i++
        set host = $argv[$i]
    endif
    @ i++
end

# Build python command
set python_cmd = "streamlit run ui/app.py --server.port $port --server.address $host"

# Execute based on flag
if ($bsub_flag == 1) then
    module load LSF/mtkgpu
    bsub -Is -J EDA_UI -q ML_CPU -app ML_CPU -P d_09017 "$python_cmd"
else if ($utilq_flag == 1) then
    utilq -Is -J eda_ui "$python_cmd"
else
    setenv CUDA_VISIBLE_DEVICES ""
    eval "$python_cmd"
endif

