#!/bin/bash

# Define the directory path
modes_directory="/root/modes"

# Check if the modes directory exists
if [ ! -d "$modes_directory" ]; then
    echo "Error: Modes directory not found."
    exit 1
fi

modes=$(find "$modes_directory" -type f -printf "%P\n" | awk -F/ '{ print ($NF ~ /\./) ? $0 : $0 "/" }')
if [ -z "$modes" ]; then
    echo "No modes found."
    exit 1
fi

# Define the preview command for the right preview window
right_preview_cmd="bat --color=always --style=numbers --line-range=:500 '$modes_directory/{}'"

# Prompt the user to select a mode using fzf with a colored prompt
selected_mode=$(echo -e "$modes" | fzf \
    --preview-window="right:80%:wrap" \
    --preview="$right_preview_cmd" \
    --color=fg:-1,bg:-1,hl:6,fg+:4,pointer:4
)

echo "$selected_mode"
