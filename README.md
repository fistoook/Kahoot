# 🎯 Kahoot Clone - Multiplayer Trivia Game

A real-time multiplayer trivia game built with Python sockets, featuring concurrent room support and themed questions.

## ✨ Features

- **Multi-room Support** - Multiple games run simultaneously without blocking
- **Themed Questions** - Choose from General, Math, Cyber Security, or Nature
- **Real-time Gameplay** - Instant answer validation and live leaderboards
- **Concurrent Architecture** - Event-driven non-blocking server handles multiple rooms
- **Colorful UI** - Terminal-based interface with ANSI colors

## 🚀 Quick Start

### Server
```bash
python KahootServer.py
```

### Client
```bash
python clientKahoot.py
```

## 🎮 How to Play

1. **Join Server** - Connect and choose a username
2. **Create/Join Room** - Host with `Host <game name>` or join with `Join <room ID>`
3. **Configure Game** - Select number of questions and theme (general/math/cyber/nature)
4. **Answer Questions** - Type 1-4 within the time limit
5. **View Results** - See scores after each question and final leaderboard

## 🏗️ Architecture

- **KahootServer.py** - Event-driven server with concurrent room management
- **clientKahoot.py** - Prompt-based client interface
- **GameManager.py** - Question loading and game logic
- **NetworkHelpers.py** - Network utility functions
- **questions/** - CSV files with themed trivia questions

## 📝 Question Format

CSV files with 6 columns: `question,option1,option2,option3,option4,correct_answer`

## 🔧 Requirements

- Python 3.7+
- colorama (`pip install colorama`)

---

*Built with Python sockets and select() for non-blocking I/O*
