"""
Manual test for countdown timer.
Run this to test the countdown feature interactively.

Instructions:
1. Run this script
2. When prompted, enter: Player1
3. Type: host TestGame
4. Type: start
5. Type: 1 (for number of questions)
6. Type: cyber (for theme)
7. Watch the countdown timer update at the top of the screen!
8. Answer the question by typing 1, 2, 3, or 4
"""

import subprocess
import sys
import time

print("=" * 70)
print("MANUAL COUNTDOWN TIMER TEST".center(70))
print("=" * 70)
print()
print("This test will start the server and client.")
print("Follow the prompts to host a game and see the countdown in action!")
print()
print("Expected behavior:")
print("  1. Screen clears when question appears")
print("  2. Countdown timer shows at the TOP of the screen")
print("  3. Timer updates every second (20, 19, 18...)")
print("  4. Question appears BELOW the timer")
print()
print("=" * 70)
input("Press ENTER to start the test...")
print()

# Start server
print("Starting server...")
server = subprocess.Popen(
    [sys.executable, "KahootServer.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)
time.sleep(1.5)

print("Server started! Now starting client...")
print()
print("=" * 70)
print()

# Start client interactively
try:
    subprocess.run([sys.executable, "clientKahoot.py"])
except KeyboardInterrupt:
    print("\nTest interrupted by user.")
finally:
    print("\nCleaning up...")
    server.kill()
    server.wait()
    print("Server stopped. Test complete.")
