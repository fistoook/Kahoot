#!/usr/bin/env python3
"""Test single client with debug logging"""
import subprocess
import sys

inputs_to_send = ["Player1", "host Game1", "start", "2", "cyber"]

print("="*60)
print("SINGLE CLIENT TEST - With Debug Logging")
print("="*60)
print("\nSending inputs:")
for inp in inputs_to_send:
    print(f"  {inp}")
print("\n" + "="*60 + "\n")

process = subprocess.Popen(
    [sys.executable, "clientKahoot.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd="c:\\Users\\eyalk\\OneDrive\\Desktop\\Code\\Cyber\\Networking\\Kahoot",
    bufsize=1
)

# Send inputs
for input_text in inputs_to_send:
    try:
        process.stdin.write(input_text + "\n")
        process.stdin.flush()
        print(f"[TEST] Sent: {input_text}")
    except Exception as e:
        print(f"[TEST] Error sending {input_text}: {e}")
        break
    
    import time
    time.sleep(0.5)

# Wait and capture output
try:
    stdout, stderr = process.communicate(timeout=10)
except subprocess.TimeoutExpired:
    print("\n[TEST] Timeout - killing process")
    process.kill()
    stdout, stderr = process.communicate()

print("\n=== STDOUT ===")
print(stdout.split('\n')[:30])  # First 30 lines

print("\n=== STDERR (Debug logs) ===")
for line in stderr.split('\n'):
    if "[" in line:
        print(line)
