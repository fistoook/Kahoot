"""
Test to verify countdown timer updates in real-time.
This test waits longer to see the countdown tick down.
"""
import socket
import time
import sys
import threading

sys.path.insert(0, r'c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot')

def test_countdown_updates():
    """Test that countdown updates every second."""
    import subprocess
    
    print("=" * 70)
    print("COUNTDOWN UPDATE TEST")
    print("=" * 70)
    print("\nThis test will:")
    print("  1. Start a game")
    print("  2. Show a question with countdown")
    print("  3. Wait 5 seconds to watch countdown update")
    print("  4. Then auto-answer")
    print("\n" + "=" * 70 + "\n")
    
    # Start server
    print("[Starting server...]")
    server = subprocess.Popen(
        [sys.executable, "KahootServer.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=r'c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot'
    )
    time.sleep(2)
    
    try:
        from KahootClient import KahootClient
        from KahootClientParser import KahootClientMessageParser
        
        # Track when we reach the question
        reached_question = [False]
        wait_time = [5]  # Wait 5 seconds during question
        
        # Create inputs that will wait at the question
        inputs_given = [0]
        
        def slow_mock_input():
            """Mock input that waits when at question."""
            inputs = ["Player1", "host TestGame", "start", "1", "cyber"]
            
            if inputs_given[0] < len(inputs):
                value = inputs[inputs_given[0]]
                inputs_given[0] += 1
                print(f"[INPUT] {value}")
                time.sleep(0.2)
                return value
            
            # At the question - wait to see countdown
            if not reached_question[0]:
                reached_question[0] = True
                print("\n" + "=" * 70)
                print("COUNTDOWN IS NOW RUNNING!")
                print(f"Waiting {wait_time[0]} seconds to observe countdown updates...")
                print("=" * 70)
                
                for i in range(wait_time[0]):
                    time.sleep(1)
                    print(f"[Observing: {i+1}/{wait_time[0]} seconds]", flush=True)
                
                print("\n[Now sending answer '1' to complete test]")
                return "1"
            
            return ""
        
        # Create and connect client
        client = KahootClient()
        client.message_parser = KahootClientMessageParser(client, slow_mock_input)
        
        print("[Connecting to server...]")
        if not client.connect():
            print("❌ Failed to connect")
            return
        
        print("[Running client...]")
        print()
        
        # Run client
        def run():
            try:
                client.start()
            except EOFError:
                pass  # Expected when inputs run out
            except Exception as e:
                print(f"\n[Client stopped: {type(e).__name__}]")
        
        client_thread = threading.Thread(target=run, daemon=True)
        client_thread.start()
        client_thread.join(timeout=20)
        
        print("\n" + "=" * 70)
        print("TEST COMPLETE")
        print("=" * 70)
        print("\n✓ Check above output for:")
        print("  - '⏱  TIME REMAINING: 20 seconds' (initial display)")
        print("  - Countdown updates every second (if visible)")
        print("  - Question displayed below countdown")
        
    finally:
        print("\n[Cleanup...]")
        server.kill()
        try:
            server.wait(timeout=1)
        except:
            pass
        print("[Done]")

if __name__ == "__main__":
    test_countdown_updates()
