import subprocess
import time

def tail(f):
    proc = subprocess.Popen(['tail', '-F', f], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # Get the initial position of the file
    with open(f, 'rb') as file:
        file.seek(0, 2)
        initial_position = file.tell()

    while True:
        line = proc.stdout.readline().decode().strip()
        if not line:
            time.sleep(1)
            continue

        # Check if the file position has changed
        with open(f, 'rb') as file:
            file.seek(initial_position, 0)
            new_lines = file.readlines()

        for new_line in new_lines:
            print(new_line.decode().strip())

        # Update the initial position to the current end of the file
        with open(f, 'rb') as file:
            file.seek(0, 2)
            initial_position = file.tell()

print("Waiting for events ...")
logfile = '.smb_logs.log'
tail(logfile)




# logfile = '.electron-logfile.log'