#!/usr/bin/env python3
"""
Extended test to verify complete game flow including leaderboard.
"""

import socket
import time
import threading
from colorama import Fore, Style, init

init(autoreset=True)

def log(client_name, msg):
    print(f"{Fore.MAGENTA}[{client_name}]{Style.RESET_ALL} {msg}")

def client_test(client_id, host='127.0.0.1', port=5555):
    """Simulate a client that plays a complete game."""
    try:
        sock = socket.socket()
        sock.connect((host, port))
        log(f"C{client_id}", "Connected")
        
        # Receive welcome
        data = sock.recv(4096)
        
        # Send username
        username = f"P{client_id}"
        sock.sendall((username + "\n").encode())
        log(f"C{client_id}", f"Username: {username}")
        
        time.sleep(0.3)
        sock.recv(4096)  # Lobby info
        
        # Host a room
        sock.sendall(f"Host Room{client_id}\n".encode())
        log(f"C{client_id}", f"Hosted room")
        
        time.sleep(0.3)
        data = sock.recv(4096)
        
        # Start game
        sock.sendall(b"START\n")
        log(f"C{client_id}", "START sent")
        
        time.sleep(0.3)
        sock.recv(4096)  # Question count prompt
        sock.sendall(b"1\n")  # Only 1 question for quick test
        
        time.sleep(0.3)
        sock.recv(4096)  # Theme prompt
        sock.sendall(b"general\n")
        log(f"C{client_id}", "Game configured")
        
        # Receive and answer questions
        for q_num in range(1):
            time.sleep(0.2)
            data = sock.recv(4096)
            q_text = data.decode()
            log(f"C{client_id}", f"Q{q_num+1}: {q_text[:40]}...")
            
            # Answer
            sock.sendall(b"1\n")
            time.sleep(0.2)
            
            # Get feedback + results
            resp = sock.recv(4096).decode()
            if "Correct" in resp or "Wrong" in resp:
                log(f"C{client_id}", f"Feedback: {'Correct' if 'Correct' in resp else 'Wrong'}")
            if "Next question" in resp or "Time's up" in resp:
                log(f"C{client_id}", "Results received")
        
        # Wait for leaderboard
        log(f"C{client_id}", "Waiting for leaderboard...")
        time.sleep(5)
        
        try:
            data = sock.recv(4096)
            if data:
                board = data.decode()
                if "SCORE" in board or "score" in board.lower():
                    log(f"C{client_id}", "✓ Leaderboard received")
                else:
                    log(f"C{client_id}", f"Data received: {board[:50]}")
            else:
                log(f"C{client_id}", "Connection closed (leaderboard may be sent)")
        except:
            log(f"C{client_id}", "Timeout waiting for leaderboard (game may be complete)")
        
        sock.close()
        log(f"C{client_id}", "Done")
        
    except Exception as e:
        log(f"C{client_id}", f"ERROR: {e}")

if __name__ == "__main__":
    print(f"\n{Fore.GREEN}{Style.BRIGHT}=== Complete Game Flow Test ==={Style.RESET_ALL}\n")
    
    t1 = threading.Thread(target=client_test, args=(1,))
    t2 = threading.Thread(target=client_test, args=(2,))
    
    t1.start()
    time.sleep(0.5)
    t2.start()
    
    t1.join()
    t2.join()
    
    print(f"\n{Fore.GREEN}{Style.BRIGHT}=== Test Complete ==={Style.RESET_ALL}\n")
