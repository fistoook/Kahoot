#!/usr/bin/env python3
"""
Test script to verify concurrent room functionality.
Runs two clients that create and start games simultaneously.
"""

import socket
import time
import threading
from colorama import Fore, Style, init

init(autoreset=True)

def log(client_name, msg):
    print(f"{Fore.MAGENTA}[{client_name}]{Style.RESET_ALL} {msg}")

def client_test(client_id, host='127.0.0.1', port=5555):
    """Simulate a client that creates a room and starts a game."""
    try:
        # Connect
        sock = socket.socket()
        sock.connect((host, port))
        log(f"Client{client_id}", "Connected to server")
        
        # Receive welcome
        data = sock.recv(4096)
        log(f"Client{client_id}", f"Received: {data.decode().strip()}")
        
        # Send username
        username = f"Player{client_id}"
        sock.sendall((username + "\n").encode())
        log(f"Client{client_id}", f"Sent username: {username}")
        time.sleep(0.5)
        
        # Receive lobby list
        data = sock.recv(4096)
        log(f"Client{client_id}", f"Received lobby info")
        
        # Host a room
        game_name = f"Room{client_id}"
        sock.sendall(f"Host {game_name}\n".encode())
        log(f"Client{client_id}", f"Created room: {game_name}")
        time.sleep(0.5)
        
        # Receive room confirmation
        data = sock.recv(4096)
        room_info = data.decode().strip()
        log(f"Client{client_id}", f"Room created: {room_info[:50]}")
        
        # Extract room ID from response (should be "Room ID: XXXX")
        lines = room_info.split('\n')
        room_id = None
        for line in lines:
            if "Room ID:" in line:
                room_id = line.split("Room ID:")[-1].strip()
                break
        log(f"Client{client_id}", f"Room ID: {room_id}")
        
        # Start the game
        sock.sendall(b"START\n")
        log(f"Client{client_id}", "Sent START command")
        time.sleep(0.5)
        
        # Should get question count prompt
        data = sock.recv(4096)
        log(f"Client{client_id}", f"Received: {data.decode().strip()[:60]}")
        
        # Send number of questions
        sock.sendall(b"2\n")
        log(f"Client{client_id}", "Sent question count: 2")
        time.sleep(0.5)
        
        # Should get theme selection prompt
        data = sock.recv(4096)
        log(f"Client{client_id}", f"Received: {data.decode().strip()[:60]}")
        
        # Send theme
        sock.sendall(b"general\n")
        log(f"Client{client_id}", "Sent theme: general")
        time.sleep(0.5)
        
        # Should get first question
        data = sock.recv(4096)
        q_data = data.decode().strip()
        log(f"Client{client_id}", f"Received first question ({len(q_data)} bytes)")
        
        # Wait to see game progress
        time.sleep(3)
        
        # Try to answer
        sock.sendall(b"1\n")
        log(f"Client{client_id}", "Answered question: 1")
        
        # Receive feedback
        data = sock.recv(4096)
        log(f"Client{client_id}", f"Received feedback: {data.decode().strip()}")
        
        # Keep connection open for a few seconds to see results
        time.sleep(5)
        
        sock.close()
        log(f"Client{client_id}", "Disconnected")
        
    except Exception as e:
        log(f"Client{client_id}", f"ERROR: {e}")

if __name__ == "__main__":
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== Testing Concurrent Rooms ==={Style.RESET_ALL}\n")
    
    # Start two clients simultaneously
    log("TEST", "Starting Client 1...")
    t1 = threading.Thread(target=client_test, args=(1,))
    t1.start()
    
    time.sleep(1)  # Stagger slightly to see sequential operations
    
    log("TEST", "Starting Client 2...")
    t2 = threading.Thread(target=client_test, args=(2,))
    t2.start()
    
    # Wait for both to complete
    t1.join()
    t2.join()
    
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== Test Complete ==={Style.RESET_ALL}\n")
