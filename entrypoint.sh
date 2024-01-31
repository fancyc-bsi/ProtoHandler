#!/bin/bash
tmuxp load .tmux.session.yaml
# Create a new session and window for the first command
#tmux new-session -d -s ProtoHandler -n "ProtoHandler-cli"
#tmux send-keys -t ProtoHandler:0 "python3 cli.py --build_api" Enter

# Create a new window for the second command
#tmux new-window -t ProtoHandler:1 -n "ProtoHandler-msf"
#tmux send-keys -t ProtoHandler:1 "msfconsole -q" Enter
#tmux send-keys -t ProtoHandler:1 "clear" Enter
# Attach to the session
#tmux attach-session -t ProtoHandler
