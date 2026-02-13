#!/usr/bin/env python3
"""Simple debug test for host message flow"""
import subprocess
import sys

print("="*60)
print("CLIENT DEBUG TEST - Host Message Flow")
print("="*60)

process = subprocess.Popen(
    [sys.executable, "clientKahoot.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    cwd="c:\\Users\\eyalk\\OneDrive\\Desktop\\Code\\Cyber\\Networking\\Kahoot",
    bufsize=1
)

# Send inputs  
inputs = ["Player1", "host TestGame", "start", "1", "cyber"]
for inp in inputs:
    try:
        process.stdin.write(inp + "\n")
        process.stdin.flush()
        print(f"[SENT] {inp}")
    except:
        break
    
    import time
    time.sleep(0.5)

# Wait and capture output
try:
    stdout, _ = process.communicate(timeout=10)
except subprocess.TimeoutExpired:
    process.kill()
    stdout, _ = process.communicate()

print("\n" + "="*60)
print("OUTPUT:")
print("="*60)
print(stdout)
