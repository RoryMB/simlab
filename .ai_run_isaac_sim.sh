#!/bin/bash

# Script to run Isaac Sim Python scripts with proper output filtering

if [ $# -eq 0 ]; then
    echo "Usage: $0 <python_file>"
    exit 1
fi

PYTHON_FILE="$1"

# Check if file exists
if [ ! -f "$PYTHON_FILE" ]; then
    echo "Error: File '$PYTHON_FILE' not found"
    exit 1
fi

# Run the script and capture ALL output first
. ./activate-isaacsim.sh
python -u "$PYTHON_FILE" 2>&1 > /tmp/isaac_full_output.txt

# Check if Isaac Sim started up successfully
if grep -q "Simulation App Startup Complete" /tmp/isaac_full_output.txt; then
    # Startup successful - apply normal filtering
    awk '/Simulation App Startup Complete/{flag=1} flag{print}' /tmp/isaac_full_output.txt > /tmp/isaac_filtered_output.txt
    output_file="/tmp/isaac_filtered_output.txt"
else
    # Startup failed - show full output
    output_file="/tmp/isaac_full_output.txt"
fi

# Check line count and display appropriately
lines=$(wc -l < "$output_file")

if [ "$lines" -le 500 ]; then
    cat "$output_file"
else
    head -250 "$output_file"
    echo ""
    echo "... (output truncated, showing first 250 and last 250 lines) ..."
    echo ""
    tail -250 "$output_file"
fi

# Clean up
rm -f /tmp/isaac_full_output.txt /tmp/isaac_filtered_output.txt
