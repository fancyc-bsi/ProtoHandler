import threading
import re
import requests
import sqlite3
from tabulate import tabulate
import dateutil.parser
import datetime
from dateutil import tz
import time
from imports.logging_cfg import log

class MonitorDB:
    def __init__(self):
        self.deleted_agent_ids = set()     
        self.conn = sqlite3.connect('agents.db', check_same_thread=False)
        self.c = self.conn.cursor()
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT,
                hostname TEXT,
                username TEXT,
                processName TEXT,
                processId INTEGER,
                integrity TEXT,
                architecture TEXT,
                lastSeen TEXT
            )
        ''')

        # Create a new table for tasks
        self.c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT,
            command TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        self.base_url = f'http://localhost:5000'
        log.info("Waiting for API to be online...")
        while True:
            try:
                response = requests.get(f"{self.base_url}/swagger/index.html")
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass 
            time.sleep(2)

        log.success("Connection to backend confirmed")
        log.info("Waiting for incoming connections...")
        self.update_thread = threading.Thread(target=self.update_db)
        self.update_thread.start()

        # Start the monitor_db_changes thread
        self.monitor_thread = threading.Thread(target=self.monitor_db_changes)
        self.monitor_thread.start()

    def update_db(self):
        while True:
            response = requests.get(f"{self.base_url}/agents")
            result = response.json()
            if result:
                agents_data = [
                    (
                        agent['metadata']['id'], agent['metadata']['hostname'], agent['metadata']['username'],
                        agent['metadata']['processName'], agent['metadata']['processId'], agent['metadata']['integrity'],
                        agent['metadata']['architecture'], agent['lastSeen'] or datetime.datetime.now().isoformat()
                    )
                    for agent in result
                ]
                with self.conn:
                    for agent_data in agents_data:
                        agent_id = agent_data[0]
                        self.c.execute("SELECT agent_id FROM agents WHERE agent_id=?", (agent_id,))
                        existing_agent = self.c.fetchone()
                        if existing_agent:
                            # Update existing agent
                            self.c.execute(
                                "UPDATE agents SET hostname=?, username=?, processName=?, processId=?, integrity=?, architecture=?, lastSeen=? WHERE agent_id=?",
                                agent_data[1:] + (agent_id,)
                            )
                        else:
                            # Insert new agent
                            self.c.execute(
                                "INSERT INTO agents (agent_id, hostname, username, processName, processId, integrity, architecture, lastSeen) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                agent_data
                            )

            time.sleep(10)


    def monitor_db_changes(self):
        # Initialize previous agent IDs as an empty set
        previous_agent_ids = set()

        # Initialize previous lastSeen time as None
        previous_last_seen = None

        # Continuously monitor the database for changes
        while True:
            # Fetch the current lastSeen time from the endpoint
            response = requests.get(f"{self.base_url}/agents")
            result = response.json()
            if result:
                current_last_seen = result[0].get('lastSeen')

                # Compare the current and previous lastSeen values
                if current_last_seen and previous_last_seen:
                    current_time = dateutil.parser.isoparse(current_last_seen)
                    previous_time = dateutil.parser.isoparse(previous_last_seen)
                    time_diff = current_time - previous_time

                    # If the time difference exceeds 3 minutes, delete the agent from the database
                    if time_diff.total_seconds() > 180:
                        agent_id = result[0]['metadata']['id']
                        self.delete_agent(agent_id)
                        self.deleted_agent_ids.add(agent_id)
                        log.info(f"Inactive agent deleted: {agent_id}")

                # Update the previous lastSeen value
                previous_last_seen = current_last_seen

            # Fetch the current agent IDs and last seen times from the database using a new cursor
            c = self.conn.cursor()
            c.execute("SELECT agent_id, lastSeen FROM agents")
            agent_last_seen = {row[0]: row[1] for row in c.fetchall()}
            c.close()

            # Check if agent IDs in the database have changed
            if set(agent_last_seen.keys()) != previous_agent_ids:
                headers = ['Agent ID', 'Hostname', 'Username', 'Process Name', 'Process ID', 'Integrity', 'Architecture', 'Last Seen']
                log.success("Agent checked in:")
                self.c.execute("SELECT * FROM agents WHERE agent_id IN ({})".format(",".join(["?"] * len(agent_last_seen))), list(agent_last_seen.keys()))
                current_values = self.c.fetchall()
                print(tabulate(current_values, headers=headers, tablefmt='psql'))

            # Delete inactive agents from the database
            current_time = datetime.datetime.now()
            for agent_id, last_seen in agent_last_seen.items():
                if self.is_inactive(current_time, last_seen):
                    if agent_id not in self.deleted_agent_ids:
                        self.delete_agent(agent_id)
                        self.deleted_agent_ids.add(agent_id)
                        log.info(f"Inactive agent deleted: {agent_id}")

            # Update the previous agent IDs with the current agent IDs
            previous_agent_ids = set(agent_last_seen.keys())

            # Sleep for a certain period before checking again
            time.sleep(2)




    def is_inactive(self, current_time, last_seen):
        # Determine if the agent is inactive based on the last seen time
        # Adjust the time threshold as needed (e.g., timedelta(minutes=30))
        threshold = datetime.timedelta(minutes=2)
        last_seen_time = dateutil.parser.isoparse(last_seen)
        current_time = current_time.replace(tzinfo=last_seen_time.tzinfo)
        return current_time - last_seen_time > threshold

    def delete_agent(self, agent_id):
        # Delete the agent from the database
        self.c.execute("DELETE FROM agents WHERE agent_id=?", (agent_id,))
        self.conn.commit()
        log.info(f"Inactive agent deleted: {agent_id}")

        # Remove the agent_id from the deleted_agent_ids set
        if agent_id in self.deleted_agent_ids:
            self.deleted_agent_ids.remove(agent_id)



if __name__ == "__main__":
    try:
        invoke = MonitorDB()
    except KeyboardInterrupt as ki:
        invoke.update_thread.join()
        invoke.monitor_thread.join()
        sys.exit(0)
