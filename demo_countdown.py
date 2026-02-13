"""
=== COUNTDOWN TIMER DEMO ===

This script demonstrates the countdown timer feature.

INSTRUCTIONS:
1. Run this script in a terminal/console window
2. Follow the prompts:
   - Enter username: Player1
   - Type: host TestGame
   - Type: start
   - Type: 1
   - Type: cyber
3. Watch the countdown timer at the TOP of the screen update every second!
4. Answer the question (type 1, 2, 3, or 4)

EXPECTED BEHAVIOR:
- Screen clears when question appears
- Countdown timer appears at the very top: ⏱ TIME REMAINING: 20 seconds
- Timer updates in place every second (20 → 19 → 18 → ...)
- Question and options display below the timer
- You can input your answer while timer runs

Press Ctrl+C to exit at any time.
"""

import subprocess
import sys
import time

print(__doc__)
print("=" * 70)
input("\nPress ENTER to start the demo...")
print("\nStarting server in background...")

# Start server
server = subprocess.Popen(
    [sys.executable, "KahootServer.py"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    cwd=r'c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot'
)

time.sleep(1.5)
print("Server ready!")
print("\nStarting client (interactive mode)...\n")
print("=" * 70)
print()

try:
    # Run client interactively
    subprocess.run(
        [sys.executable, "clientKahoot.py"],
        cwd=r'c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot'
    )
except KeyboardInterrupt:
    print("\n\nDemo interrupted.")
finally:
    print("\nStopping server...")
    server.kill()
    server.wait()
    print("Demo complete!")
