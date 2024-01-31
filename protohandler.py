import os
import argparse
import time
import requests
import subprocess
import atexit
import sys
from imports.logging_cfg import log
from imports.cli import APIWrapper

"""
To-Do:
- tmux integration and config -> auto setup msf with payload, listener and etc
- custom tmux plugins - floating windows
- input validation
- dynamic handler name creation

- automate update_db with threading 
- more specific instructions for; file, arguments
- inject 'abilities' similar to metasploit 
- dll hyjacking persistance 
- add color and improve the prompt
- disable defender shellcode or command

Done:
- docker image
- change execute-powershell to inject-handler for more clarity 
- chose which metapsploit cmd is run based on the arguments
- fix wipe_db for docker container
- change create_payload to create_handler for clairity 
- fix generate_shellcode for docker container
- method to cross-compile the agent on linux 
- exit after db is wiped 
- fix json conversion error
- fix payload auto suggest for msfvenom --> capital letters seems to be the workaround for now
"""

base_url = f'http://localhost:5000'
def inital_checks():
    original_cwd = os.getcwd()
    parser = argparse.ArgumentParser()
    parser.add_argument("--build_api", action='store_true', help="Builds the API server and tests functionality")
    args = parser.parse_args()
    
    try:
        time.sleep(1)
        connect_url = f'{base_url}/swagger/index.html'
        response = requests.get(connect_url)
        if response.status_code == 200:
            log.success("API is already built. Continuing ...")
            return 
    except:
        pass
    if args.build_api:
        log.info("Building API - please wait ...")
        devnull = os.devnull if os.name != 'nt' else 'nul'
        with open(devnull, 'w') as nullfile:
            sys.stderr = nullfile
        
            dest_path = os.path.join(original_cwd, "APISERVER/TeamServer")
            os.chdir(dest_path)

            build_command = '~/.dotnet/dotnet publish -c Release -r linux-x64 --self-contained true'
            subprocess.run(build_command, shell=True, check=True, stdout=nullfile, stderr=nullfile)

            server_path = os.path.join(dest_path, "bin/Release/net7.0/linux-x64/publish/TeamServer")
            run_server_command = '{} --environment "Development" --urls "http://0.0.0.0:5000" --contentroot {}'.format(server_path, dest_path)
            subprocess.Popen(run_server_command, shell=True)
            
        log.success("API built")
    os.chdir(original_cwd)  # Restore the original working directory

def confirm_connection():
    time.sleep(1)
    connect_url = f'{base_url}/swagger/index.html'

    try:
        response = requests.get(connect_url)
        if response.status_code == 200:
            log.success("API is accessible.")
        else:
            log.error("API is not accessible. Exiting the script.")
    except requests.exceptions.RequestException:
        log.error("API is not accessible. Exiting the script.")
        sys.exit(0)



def shutdown_server():
    try:
        httpd.shutdown()
    except NameError:
        pass    
    atexit.register(shutdown_server)



if __name__ == '__main__':
    inital_checks()
    confirm_connection()
    wrapper = APIWrapper()
    wrapper.main()
