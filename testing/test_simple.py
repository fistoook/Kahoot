#!/usr/bin/env python3
"""Simple test to debug message flow between client and server."""
import subprocess
import time
import sys

print("="*60)
print("SIMPLE CLIENT TEST - Debug message flow")
print("="*60)

# Start one client with interactive input
print("\nStarting client...")
print("When prompted, enter:")
print("  1. Username: TestPlayer")
print("  2. Command: host TestGame")
print("  3. Questions: 1")
print("  4. Theme: general")
print("\n" + "="*60 +"\n")

process = subprocess.Popen(
    [sys.executable, "clientKahoot.py"],
    cwd="c:\\Users\\eyalk\\OneDrive\\Desktop\\Code\\Cyber\\Networking\\Kahoot",
)

try:
    process.wait(timeout=30)
except subprocess.TimeoutExpired:
    print("\nClient timeout - terminating")
    process.terminate()
    process.wait()
