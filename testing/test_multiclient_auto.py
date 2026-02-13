#!/usr/bin/env python3
"""
Automated multi-client test to verify message routing works correctly.
Tests:
1. Two clients connecting simultaneously
2. Client 1 hosting a game
3. Client 2 joining the game  
4. Starting the game and answering questions
"""
import subprocess
import time
import sys
import threading
import os

def run_client(client_id, inputs):
    """Run a client with automated inputs."""
    print(f"\n{'='*60}")
    print(f"CLIENT {client_id} - Starting")
    print(f"{'='*60}")
    
    process = subprocess.Popen(
        [sys.executable, "clientKahoot.py"],
        cwd="c:\\Users\\eyalk\\OneDrive\\Desktop\\Code\\Cyber\\Networking\\Kahoot",
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    
    # Track output for analysis
    output_lines = []
    
    def send_inputs():
        """Send inputs with delays between them."""
        for delay, input_text in inputs:
            time.sleep(delay)
            try:
                process.stdin.write(input_text + "\n")
                process.stdin.flush()
                print(f"[CLIENT {client_id}] SENT: {repr(input_text)}")
            except Exception as e:
                print(f"[CLIENT {client_id}] ERROR sending: {e}")
    
    def read_output():
        """Read and display output."""
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                output_lines.append(line)
                # Print interesting lines
                if any(keyword in line for keyword in ["[", "Error", "error", "success", "Successfully", "prompt"]):
                    print(f"[CLIENT {client_id}] {line.rstrip()}")
        except:
            pass
    
    # Start input sender thread
    input_thread = threading.Thread(target=send_inputs, daemon=True)
    input_thread.start()
    
    # Read output
    read_output()
    
    # Wait for process to finish
    try:
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        print(f"[CLIENT {client_id}] TIMEOUT - terminating")
        process.terminate()
    
    print(f"[CLIENT {client_id}] Exited with code {process.returncode}")
    return output_lines

def main():
    print("\n" + "="*60)
    print("KAHOOT MULTI-CLIENT DEBUG TEST")
    print("="*60)
    print("Server should be running on 127.0.0.1:5555")
    
    print("\nWaiting 2 seconds for server to be ready...")
    time.sleep(2)
    
    # Test 1: Two clients connecting with usernames
    print("\n" + "="*60)
    print("TEST 1: Client 1 and Client 2 both connect and get usernames")
    print("="*60)
    
    # Client 1 will: Connect -> Username -> "host TestGame" -> "start" -> "2" questions -> "cyber" theme
    client1_inputs = [
        (1.0, "Player1"),           # Username
        (2.0, "host Game1"),        # Host command
        (1.0, "start"),             # Start game (this triggers question count prompt)
        (1.0, "2"),                 # Number of questions  
        (1.0, "cyber"),             # Theme selection
        (20.0, "1"),                # Answer to Q1
        (20.0, "2"),                # Answer to Q2
    ]
    
    # Client 2 will: Connect -> Username -> wait -> "join 0001" -> wait for game -> answer
    client2_inputs = [
        (1.5, "Player2"),           # Username
        (3.0, "join 0001"),         # Join room (wait for room to be created)
        (22.0, "2"),                # Answer to Q1
        (22.0, "4"),                # Answer to Q2
    ]
    
    # Run clients in parallel
    thread1 = threading.Thread(target=run_client, args=(1, client1_inputs), daemon=False)
    thread2 = threading.Thread(target=run_client, args=(2, client2_inputs), daemon=False)
    
    print("\nStarting Client 1...")
    thread1.start()
    
    print("Waiting 1 second before starting Client 2...")
    time.sleep(1)
    
    print("Starting Client 2...")
    thread2.start()
    
    # Wait for both to finish
    thread1.join(timeout=30)
    thread2.join(timeout=30)
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print(f"Both clients {'finished successfully' if not thread1.is_alive() and not thread2.is_alive() else 'had issues'}")
    
    # Check server status
    print("\nChecking server status...")
    time.sleep(1)

if __name__ == "__main__":
    main()
