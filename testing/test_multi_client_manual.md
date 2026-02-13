# Multi-Client Testing Guide

## What Was Fixed

The issue was that the client parser was matching **partial prompts** when TCP messages arrived in chunks. When the server sends a long prompt message that arrives split across multiple `recv()` calls, the parser would match the incomplete prompt and wait for user input prematurely.

### Root Cause Examples

**Problem 1: Lobby Request Prompt**
- Server sends: `"Type 'Host <game name>' to host, 'Join <room ID>' to join, or 'View Rooms' to see available rooms:"`
- If this arrives as chunks:
  - First chunk: `"Type 'Host <game name>' to host, 'Join <room ID>'"`
  - OLD parser code would match "join <room id>" and call `input()` immediately
  - This made client 2 wait for input even though the full prompt hadn't arrived yet

**Problem 2: Question Prompt**
- Server sends: Multi-line question with counter, question text, 4 options, and answer prompt
- OLD parser code would match "type 1-4" on the prompt line without checking if all options had arrived

### Fixes Applied

1. **Line 63 in KahootClientParser.py**: Changed lobby request matching from:
   ```python
   if "join <room id>" in lowered or "host <game name>" in lowered:
   ```
   to:
   ```python
   if ("join <room id>" in lowered or "host <game name>" in lowered) and "available rooms" in lowered:
   ```
   This ensures the full prompt line is present before triggering input.

2. **Line 107 in KahootClientParser.py**: Changed question matching from:
   ```python
   if "type 1-4" in lowered or "type 1, 2, 3, or 4" in lowered:
   ```
   to:
   ```python
   if ("type 1-4" in lowered or "type 1, 2, 3, or 4" in lowered) and len(lines) >= 6:
   ```
   This ensures all 6+ lines of the question (counter, question, 4 options, prompt) are present.

## Testing Instructions

### Terminal 1 - Start the Server
```bash
cd "c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot"
python KahootServer.py
```
You should see:
```
LISTENING ON 127.0.0.1:5555
```

### Terminal 2 - Start Client 1
```bash
cd "c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot"
python clientKahoot.py
```
When prompted for username, type: `Player1`

You should see the lobby prompt.

### Terminal 3 - Start Client 2 Immediately
While Client 1 is stil running, in a new terminal:
```bash
cd "c:\Users\eyalk\OneDrive\Desktop\Code\Cyber\Networking\Kahoot"
python clientKahoot.py
```
When prompted for username, type: `Player2`

## What to Verify

✅ **Both clients should:**
- Connect without errors
- Receive welcome message
- Prompt for username without hanging
- Receive full lobby message
- Respond to commands properly

❌ **Issues that would indicate a problem:**
- Client hangs waiting for input
- Partial prompts displayed
- "Messages not going through" - garbled output
- Second client disconnects or timeouts

## Testing Interaction Flow (Optional)

After both clients are in the lobby:

In Client 1 terminal, type: `host TestGame`
- Client 1 should see "Game 'TestGame' hosted! Room ID: 0001"

In Client 2 terminal, type: `join 0001`  
- Client 2 should be added to the room
- Client 1 should see "Player2 joined"

In Client 1 terminal, type: `start`
- Game should begin and both clients should receive the first question
- Countdown timer should display: `⏱ Time remaining: XXs`

In either client, type `1`, `2`, `3`, or `4` for answer
- Response should be submitted to server
