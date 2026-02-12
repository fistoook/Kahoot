#!/usr/bin/env python3
"""
Automated test script for Kahoot game - tests full game flow
"""

import socket
import time
import threading
import sys

class TestClient:
    def __init__(self, name, client_id):
        self.name = name
        self.client_id = client_id
        self.sock = socket.socket()
        self.messages = []
        self.connected = False
        
    def connect(self):
        """Connect to server."""
        try:
            self.sock.connect(('127.0.0.1', 5555))
            self.connected = True
            print(f"[CLIENT {self.client_id}] Connected to server")
            return True
        except Exception as e:
            print(f"[CLIENT {self.client_id}] Connection failed: {e}")
            return False
    
    def send(self, message):
        """Send a message to server."""
        try:
            self.sock.sendall((message + "\n").encode())
            print(f"[CLIENT {self.client_id}] Sent: {message}")
            time.sleep(0.2)
        except Exception as e:
            print(f"[CLIENT {self.client_id}] Send failed: {e}")
    
    def receive_until(self, pattern, timeout=5):
        """Receive messages until pattern is found."""
        start = time.time()
        buffer = ""
        
        while time.time() - start < timeout:
            try:
                self.sock.settimeout(0.5)
                data = self.sock.recv(4096)
                if not data:
                    break
                buffer += data.decode(errors='ignore')
                
                if pattern.lower() in buffer.lower():
                    print(f"[CLIENT {self.client_id}] Received pattern: {pattern}")
                    return True
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[CLIENT {self.client_id}] Receive error: {e}")
                break
        
        print(f"[CLIENT {self.client_id}] Timeout waiting for: {pattern}")
        return False
    
    def close(self):
        """Close connection."""
        try:
            self.sock.close()
            self.connected = False
            print(f"[CLIENT {self.client_id}] Disconnected")
        except:
            pass


def test_basic_connection():
    """Test 1: Basic connection and username entry."""
    print("\n" + "="*60)
    print("TEST 1: Basic Connection and Username Entry")
    print("="*60)
    
    client = TestClient("TestPlayer1", 1)
    if not client.connect():
        return False
    
    # Wait for username prompt
    if not client.receive_until("Enter your username", timeout=3):
        return False
    
    # Send username
    client.send("TestPlayer1")
    
    # Wait for lobby message
    if not client.receive_until("Successfully joined", timeout=3):
        return False
    
    print("[TEST 1] ✓ PASSED")
    client.close()
    return True


def test_host_creates_room():
    """Test 2: Host creates a room."""
    print("\n" + "="*60)
    print("TEST 2: Host Creates Room")
    print("="*60)
    
    host = TestClient("HostPlayer", 2)
    if not host.connect():
        return False
    
    # Send username
    host.receive_until("Enter your username", timeout=3)
    host.send("HostPlayer")
    
    # Wait for lobby - look for any indicator that we're in lobby
    host.receive_until("Host", timeout=3)
    
    # Host create room
    print("[TEST 2] Hosting game...")
    host.send("Host TestGame")
    
    # Wait for room creation confirmation
    if not host.receive_until("Room ID:", timeout=3):
        return False
    
    print("[TEST 2] ✓ PASSED")
    host.close()
    return True


def test_two_players_full_game():
    """Test 3: Two players - host creates room, guest joins, game plays."""
    print("\n" + "="*60)
    print("TEST 3: Full Game Flow (Host + Guest)")
    print("="*60)
    
    # Create host
    host = TestClient("Host", 3)
    guest = TestClient("Guest", 4)
    
    if not host.connect():
        return False
    if not guest.connect():
        return False
    
    # Both send usernames
    host.receive_until("Enter your username", timeout=3)
    host.send("Host")
    
    guest.receive_until("Enter your username", timeout=3)
    guest.send("Guest")
    
    # Wait for lobby
    host.receive_until("Host", timeout=3)
    guest.receive_until("Guest", timeout=3)
    
    # Host creates room
    print("[TEST 3] Host creating room...")
    host.send("Host GameRoom")
    
    if not host.receive_until("Room ID:", timeout=3):
        print("[TEST 3] Failed: Host didn't get room ID")
        return False
    
    print("[TEST 3] Waiting for guest to receive room list...")
    time.sleep(0.5)
    
    # Guest joins room (room 0002 based on test 2 creating room 0001)
    print("[TEST 3] Guest joining room 0002...")
    guest.send("Join 0002")
    
    if not guest.receive_until("Joined", timeout=3):
        print("[TEST 3] Failed: Guest didn't join")
        return False
    
    # Host starts game
    print("[TEST 3] Host starting game...")
    host.send("START")
    
    # Host should get question count prompt
    if not host.receive_until("How many questions", timeout=3):
        print("[TEST 3] Failed: Host didn't get question count prompt")
        return False
    
    # Host sends question count
    host.send("2")
    
    # Host should get theme prompt
    if not host.receive_until("Select a theme", timeout=3):
        print("[TEST 3] Failed: Host didn't get theme prompt")
        return False
    
    # Host selects theme
    host.send("general")
    
    # Wait for game messages
    print("[TEST 3] Game starting, waiting for questions...")
    time.sleep(0.5)
    
    if not host.receive_until("Question 1", timeout=5):
        print("[TEST 3] Warning: Host didn't get question message")
    
    if not guest.receive_until("Question 1", timeout=5):
        print("[TEST 3] Failed: Guest didn't get question message")
        return False
    
    print("[TEST 3] ✓ PASSED")
    host.close()
    guest.close()
    return True


def main():
    """Run all tests."""
    print("\n\n" + "█"*60)
    print("█ KAHOOT GAME - AUTOMATED TESTING")
    print("█"*60)
    
    tests = [
        ("Basic Connection", test_basic_connection),
        ("Host Creates Room", test_host_creates_room),
        ("Full Game Flow", test_two_players_full_game),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            time.sleep(1)
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
            time.sleep(1)
    
    # Show summary
    print("\n\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} | {test_name}")
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n✗ {total - passed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
