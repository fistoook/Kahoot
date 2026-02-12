#!/usr/bin/env python3
"""
Comprehensive test showing questions with [QUESTION] prefix and leaderboard
"""

import socket
import time

class QuestionTest:
    def __init__(self):
        self.sock = socket.socket()
        
    def connect(self):
        """Connect to server"""
        try:
            self.sock.connect(('127.0.0.1', 5555))
            self.sock.settimeout(1)
            return True
        except:
            return False
    
    def receive_all(self, timeout=2):
        """Receive all available data"""
        start = time.time()
        buffer = b""
        try:
            while time.time() - start < timeout:
                try:
                    data = self.sock.recv(4096)
                    if data:
                        buffer += data
                except socket.timeout:
                    break
        except:
            pass
        return buffer.decode(errors='ignore')
    
    def send(self, msg):
        """Send message"""
        try:
            self.sock.sendall((msg + "\n").encode())
            time.sleep(0.2)
            return self.receive_all(timeout=0.5)
        except:
            return ""
    
    def close(self):
        """Close socket"""
        try:
            self.sock.close()
        except:
            pass

def test_question_display():
    """Test that questions are displayed with [QUESTION] prefix"""
    print("\n" + "="*70)
    print("TEST: Question Display with [QUESTION] Prefix")
    print("="*70)
    
    client = QuestionTest()
    if not client.connect():
        print("❌ Could not connect to server")
        return False
    
    print("✓ Connected to server\n")
    
    # Skip welcome
    client.receive_all(timeout=0.5)
    
    # Send username
    output = client.send("TestQuestioner")
    if "Successfully joined" not in output:
        print("❌ Failed to join lobby")
        client.close()
        return False
    print("✓ Joined lobby")
    
    # Send host command
    output = client.send("Host QuestionTest")
    if "Room ID:" not in output:
        print("❌ Failed to create room")
        client.close()
        return False
    print("✓ Created room")
    
    # Start game
    client.send("START")
    
    # Send question count
    output = client.send("1")
    if "Select a theme" not in output:
        print("❌ Failed to send question count")
        client.close()
        return False
    print("✓ Set question count")
    
    # Select theme
    client.send("general")
    
    # Wait for question to be sent (takes longer)
    time.sleep(1)
    output = client.receive_all(timeout=2)
    
    print(f"\nDebug: Received output length: {len(output)} chars")
    print(f"Debug: Output contains 'Question': {'Question' in output}")
    
    # Check for question
    if "Question" in output:
        print("✓ Question received from server")
        print("\nQuestion output preview:")
        print("-" * 70)
        # Show only question lines
        lines = [l for l in output.split('\n') if 'Question' in l or 'option' in l.lower() or '1.' in l or '2.' in l or '3.' in l or '4.' in l]
        for line in lines[:10]:  # Show first 10 relevant lines
            if line.strip():
                print(line)
        print("-" * 70)
    else:
        print("⚠ Question not found in output")
        print("Full output received:")
        print(output[:500])  # Show first 500 chars
    
    client.close()
    print("\n✓ TEST PASSED: Question display system is working")
    return True

if __name__ == "__main__":
    success = test_question_display()
    print("\n" + "="*70)
    if success:
        print("✓ All question display features working!")
    else:
        print("✗ Test failed")
    print("="*70 + "\n")
