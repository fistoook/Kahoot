#!/usr/bin/env python3
"""
Debug runner to start server and simulate client connections.
Run: python run_debug.py
"""
import subprocess
import time
import sys

print("Starting Kahoot server...")
server = subprocess.Popen([sys.executable, "KahootServer.py"], 
                         cwd="c:\\Users\\eyalk\\OneDrive\\Desktop\\Code\\Cyber\\Networking\\Kahoot")

time.sleep(2)

print("\nStarting first client...")
client1 = subprocess.Popen([sys.executable, "clientKahoot.py"],
                          cwd="c:\\Users\\eyalk\\OneDrive\\Desktop\\Code\\Cyber\\Networking\\Kahoot",
                          stdin=subprocess.PIPE, text=True)

time.sleep(1)

# Send username for client 1
print("Sending 'Player1' to client 1...")
try:
    client1.stdin.write("Player1\n")
    client1.stdin.flush()
except:
    pass

time.sleep(1)

print("\nStarting second client...")
client2 = subprocess.Popen([sys.executable, "clientKahoot.py"],
                          cwd="c:\\Users\\eyalk\\OneDrive\\Desktop\\Code\\Cyber\\Networking\\Kahoot",
                          stdin=subprocess.PIPE, text=True)

time.sleep(1)

# Send username for client 2
print("Sending 'Player2' to client 2...")
try:
    client2.stdin.write("Player2\n")
    client2.stdin.flush()
except:
    pass

print("\nWaiting for interaction... (Press Ctrl+C to stop)")
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nCleaning up...")
    client1.terminate()
    client2.terminate()
    server.terminate()
