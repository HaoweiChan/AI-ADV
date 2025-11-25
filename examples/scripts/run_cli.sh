#!/bin/tcsh

# Source the environment setup script
# This will handle module loading, virtualenv, and flag parsing
source scripts/setup_env.sh

# USER CONFIGURATION:
# Configure input file and options here
set input_file = ""
set config_file = ""
set output_file = ""
set format = "markdown"
set command = "run"

# Parse command line arguments
set i = 1
while ($i <= $#argv)
    set arg = $argv[$i]
    if ( "$arg" == "--bsub" || "$arg" == "--utilq" ) then
        # These are handled by setup_env.sh
        @ i++
        continue
    else if ( "$arg" == "--input" || "$arg" == "-i" ) then
        @ i++
        set input_file = $argv[$i]
    else if ( "$arg" == "--config" || "$arg" == "-c" ) then
        @ i++
        set config_file = $argv[$i]
    else if ( "$arg" == "--output" || "$arg" == "-o" ) then
        @ i++
        set output_file = $argv[$i]
    else if ( "$arg" == "--format" || "$arg" == "-f" ) then
        @ i++
        set format = $argv[$i]
    else if ( "$arg" == "run" || "$arg" == "validate" || "$arg" == "list-examples" ) then
        set command = $arg
    else if ( "$arg" !~ "-*" ) then
        # Positional argument (input file for run command)
        if ( "$command" == "run" && "$input_file" == "" ) then
            set input_file = $arg
        endif
    endif
    @ i++
end

# Build python command
set python_cmd = "python3 -m examples.ui.cli"

if ( "$command" == "run" ) then
    if ( "$input_file" == "" ) then
        echo "✗ Error: Input file is required for 'run' command"
        echo "Usage: $0 run <input_file> [--config <config_file>] [--output <output_file>] [--format <format>]"
        exit 1
    endif
    if ( ! -f "$input_file" ) then
        echo "✗ Error: Input file not found: $input_file"
        exit 1
    endif
    set python_cmd = "$python_cmd run $input_file"
    if ( "$config_file" != "" ) then
        set python_cmd = "$python_cmd --config $config_file"
    endif
    if ( "$output_file" != "" ) then
        set python_cmd = "$python_cmd --output $output_file"
    endif
    set python_cmd = "$python_cmd --format $format"
else if ( "$command" == "validate" ) then
    if ( $#argv < 2 ) then
        echo "✗ Error: validate command requires schema and data files"
        echo "Usage: $0 validate <schema_file> <data_file>"
        exit 1
    endif
    set python_cmd = "$python_cmd validate $argv[1] $argv[2]"
else if ( "$command" == "list-examples" ) then
    set python_cmd = "$python_cmd list-examples"
endif

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

