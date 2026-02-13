"""
Automated countdown test with simulated client input.
"""
import socket
import time
import sys
import threading
from io import StringIO

# Add current directory to path for imports
sys.path.insert(0, r'c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot')

def run_server():
    """Run server in a thread."""
    import subprocess
    server = subprocess.Popen(
        [sys.executable, "KahootServer.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=r'c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot'
    )
    return server

def test_with_mock_input():
    """Test countdown with mocked input."""
    print("=" * 70)
    print("AUTOMATED COUNTDOWN TEST")
    print("=" * 70)
    
    # Start server
    print("\n[1] Starting server...")
    server = run_server()
    time.sleep(2)
    
    try:
        print("[2] Starting client with mocked inputs...")
        
        # Import client components
        from clientKahoot import KahootClient
        from KahootClientParser import KahootClientMessageParser
        
        # Create mock input function
        inputs = ["Player1", "host TestGame", "start", "1", "cyber", "1"]
        input_index = [0]  # Use list to make it mutable in closure
        
        def mock_input():
            """Mock input function that returns predefined values."""
            if input_index[0] < len(inputs):
                value = inputs[input_index[0]]
                print(f"[AUTO INPUT] {value}")
                input_index[0] += 1
                time.sleep(0.3)  # Small delay to simulate user typing
                return value
            return ""
        
        # Create client with mocked input
        client = KahootClient()
        client.message_parser = KahootClientMessageParser(client, mock_input)
        
        print("[3] Connecting to server...")
        if not client.connect():
            print("❌ Failed to connect to server")
            return
        
        print("[4] Running client (will auto-answer)...")
        print("\n" + "=" * 70)
        print("WATCH FOR COUNTDOWN TIMER AT TOP OF SCREEN!")
        print("=" * 70 + "\n")
        
        # Run client in a thread with timeout
        def run_client():
            try:
                client.start()
            except Exception as e:
                print(f"\n[Client stopped: {e}]")
        
        client_thread = threading.Thread(target=run_client, daemon=True)
        client_thread.start()
        
        # Wait for test to complete (question + answer)
        client_thread.join(timeout=15)
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print("\n✓ If you saw:")
        print("  - Screen clear when question appeared")
        print("  - Countdown timer at the TOP")
        print("  - Timer updating every second")
        print("  - Question below the timer")
        print("\nThen the countdown feature is working correctly!")
        
    finally:
        print("\n[Cleanup] Stopping server...")
        server.kill()
        try:
            server.wait(timeout=2)
        except:
            pass
        print("[Cleanup] Done")

if __name__ == "__main__":
    test_with_mock_input()
