#!/bin/bash

selection=$(cat /root/.msfvenom_payloads.txt | fzf --print0)
echo -n "$selection" > /tmp/fzf_selection
tmux load-buffer /tmp/fzf_selection
tmux paste-buffer
