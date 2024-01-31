# What is this Tool?
ProtoHandler is a C2 Framework that can be used to facilitate protocol handler poisoning, and other forms of persistence. Protocol handler poisoning attacks occur when an attacker manipulates the behavior of a protocol handler by registering a malicious or unexpected handler for a particular URI scheme. This allows the attacker to execute arbitrary commands or scripts on the victim's system when the manipulated URI is clicked.

# How is the Exploit triggered? 
The exploit can be triggered through vulnerable Electron applications or through Web browsers. 

# Prerequisites

Windows 10/11 vm with RTP [real-time-protection] turned off (the victim)

prebuilt devloperVMs here: https://developer.microsoft.com/en-us/windows/downloads/virtual-machines/
or build your own

# Install docker

Install docker as per your distro intructions, make sure to add your user to the docker group.

## Run docker container
```bash
docker build -t c2:latest .
docker run --rm -it --net host --hostname c2 -v $PWD:/shared --name c2 c2:latest
```


# Getting started 
Once the docker container is running, a few setup steps are required. 

- start a listener:
```
listeners
start_listener
# Enter the listener name (this can be anything)
# Enter the listing port (this will be an http listener so port 8080 is a good option)

```
- Compile the agent: 
```
compile_agent
  - enter the callback IP (your host IP) 
  - Enter the listener port (same as above step)
```

The agent will be compiled and can now be served using the httpserver or smbserver methods
It is now up to you to get the Agent.exe onto the target machine - good luck.
Once an agent checks in, use the "Agents" menu to interact with it.  


## Shellcode inject Demo


https://github.com/rouxn-bsi/assessment-toolset/assets/85493503/07e36a8b-53ae-4c14-8a0f-74df58514178



## Other features
several tabs will be opened during runtime they are as follows:

- ProtoHandler-cli: Main menu, handles all interactions with the agent
- ProtoHandler-event_viewer: Captures SMB server events as well as when agents checkin 
- ProtoHandler-msf: Only opens if the generate_shellcode mode is invoked - will auto starts the listener for you. 

### Key bindings and plugins
Mostly tmux default keybindings with a few additions:

Prefix == ctrl+b
  
  - prefix + tab == Displays all the msfvenom shellcode generation options, select one from the popup and it will automatically pasted for you.
  - prefix + h == Displays help floating window, use the arrow keys to navigate through the help, ctrl+arrows will scroll the right pane. press esc or enter to quit
  - prefix + v == paste buffer 
  - prefix + R == Reloads tmux config 

Plugins:
  
  - TPM (Plugin manager) 
  - Yank (Select text then input 'y' to copy)
  - dracula (Theme)
  - zoom (Hold right click then 'z' to zoom a pane to fullscreen, do it again to unzoom)
  - mouse support (click tabs to open them)

# Credits and inspiration
- https://github.com/cobbr/SharpSploit
- https://github.com/Gr1mmie/AtlasC2
- https://github.com/byt3bl33d3r/OffensiveNim
- @tobias.diehl for discovering the handler poisoning attacks
