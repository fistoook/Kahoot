# ============================================================================
# Kahoot Server - Concurrent Multi-Client Handler
# ============================================================================
# Non-blocking event-driven architecture using select() and state machine.
# Allows multiple clients to connect and interact simultaneously.
# ============================================================================

import socket
import select
import time
import json
from colorama import Fore, Style, init, Back
from GameManager import GameManager
from KahootPlayer import Player
from KahootRoom import Room


init(autoreset=True)
CLIENT_DISCONNECTED = "CLIENT_DISCONNECTED"
CLIENT_RESPONSE_TIMEOUT = 60

# Client states for state machine
STATE_AWAITING_USERNAME = "awaiting_username"
STATE_IN_LOBBY = "in_lobby"
STATE_HOSTING = "hosting"
STATE_IN_ROOM = "in_room"
STATE_IN_GAME = "in_game"


def _log_info(message):
    """Log an information message in cyan."""
    print(f"{Fore.CYAN}{Style.BRIGHT}[INFO]{Style.RESET_ALL} {message}")


def _log_warn(message):
    """Log a warning message in yellow."""
    print(f"{Fore.YELLOW}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {message}")


# ============================================================================
# Main Server Class - Non-Blocking Event Loop
# ============================================================================
class KahootServer:
    def __init__(self, host='127.0.0.1', port=5555):
        """Initialize Kahoot server with state machine for concurrent client handling."""
        self.server_address = (host, port)
        self.num_players = 50
        self.clients = []  # List of Player objects
        self.server_socket = socket.socket()
        self.server_socket.bind(self.server_address)
        self.game_control = GameManager()
        
        # State machine tracking
        self.client_state = {}  # Maps socket -> state
        self.client_data = {}   # Maps socket -> dict with tracking data
        self.socket_to_player = {}  # Maps socket -> Player object

    def Run(self):
        """Main server loop: Non-blocking concurrent handling of multiple clients."""
        self.server_socket.listen(self.num_players)
        _log_info(f"Server started on {self.server_address}. Accepting connections...")

        # Main event loop
        while True:
            # Monitor server socket + all active client sockets
            readable_sockets = [self.server_socket] + list(self.client_state.keys())
            readable, _, _ = select.select(readable_sockets, [], [], 1)

            # Handle new connections
            if self.server_socket in readable:
                try:
                    conn, addr = self.server_socket.accept()
                    _log_info(f"New connection from {addr}")
                    self.client_state[conn] = STATE_AWAITING_USERNAME
                    self.client_data[conn] = {"deadline": time.time() + CLIENT_RESPONSE_TIMEOUT}
                    conn.sendall(b"Welcome to Kahoot! Enter your username: ")
                except OSError:
                    pass

            # Handle messages from existing clients
            for sock in readable:
                if sock is self.server_socket:
                    continue
                self._handle_client_message(sock)

    def _handle_client_message(self, sock):
        """Process incoming data from a client based on its current state."""
        try:
            data = sock.recv(4096)
        except (ConnectionError, OSError):
            self._drop_client(sock)
            return

        if not data:
            self._drop_client(sock)
            return

        text = data.decode(errors="ignore").strip()
        state = self.client_state.get(sock)

        # Route to appropriate handler based on state
        if state == STATE_AWAITING_USERNAME:
            self._handle_username(sock, text)
        elif state == STATE_IN_LOBBY:
            self._handle_lobby_command(sock, text)
        elif state == STATE_HOSTING:
            self._handle_host_command(sock, text)
        elif state == STATE_IN_ROOM:
            # Player waiting for game to start, ignore input
            pass

    def _handle_username(self, sock, username):
        """Process username submission and add player to lobby."""
        if not username:
            username = "Player"

        # Create Player and add to lobby
        player = Player(sock, username)
        self.clients.append(player)
        self.socket_to_player[sock] = player
        self.client_state[sock] = STATE_IN_LOBBY

        _log_info(f"Player '{username}' joined from {sock.getpeername()}")

        # Send lobby welcome
        sock.sendall(b"Successfully joined our server!\n")
        sock.sendall(b"Here are all of the ongoing games:\n")
        self.send_room_list(sock)
        sock.sendall(b"Type 'Host <game name>' to host or 'Join <room ID>' to join.\n")

    def _handle_lobby_command(self, sock, text):
        """Process Host/Join commands from lobby."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        # Host command
        if text.lower().startswith("host "):
            game_name = text[5:].strip()
            if not game_name:
                sock.sendall(b"Game name cannot be empty. Please try again.\n")
                return

            # Create new room
            room_id = str(len(self.game_control.rooms) + 1).zfill(4)
            room = Room(room_id, player)
            self.game_control.rooms[room_id] = room
            self.client_state[sock] = STATE_HOSTING
            self.client_data[sock]["room"] = room

            _log_info(f"Player '{player.username}' created room {room_id}")
            sock.sendall(f"Game '{game_name}' hosted! Room ID: {room_id}\n".encode())
            sock.sendall(b"Type START to begin, LIST to show players, or CLOSE to cancel.\n")

        # Join command
        elif text.lower().startswith("join "):
            room_id = text[5:].strip()
            if room_id not in self.game_control.rooms:
                sock.sendall(b"Invalid room ID. Try again.\n")
                return

            room = self.game_control.rooms[room_id]
            if room.game_started:
                sock.sendall(b"Game already started. Try another room.\n")
                return

            # Add to room
            room.players.append(player)
            room.scores[player] = 0
            self.client_state[sock] = STATE_IN_ROOM
            self.client_data[sock]["room"] = room

            _log_info(f"Player '{player.username}' joined room {room_id}")
            sock.sendall(f"Joined '{room.host_client.username}' room! Waiting to start...\n".encode())

            # Notify host
            try:
                room.host_client.conn.sendall(f"{player.username} joined!\n".encode())
            except:
                pass

        else:
            sock.sendall(b"Invalid command. Type 'Host <name>' or 'Join <ID>'.\n")

    def _handle_host_command(self, sock, text):
        """Process START, LIST, CLOSE commands from host."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        # Find host's room
        room = self.client_data.get(sock, {}).get("room")
        if not room:
            return

        text_lower = text.lower()

        if text_lower == "start":
            room.game_started = True
            _log_info(f"Game started in room {room.room_id}")
            self._broadcast_room(room, "Game starting now!\n")
            # Mark players as in-game
            for p in room.players:
                self.client_state[p.conn] = STATE_IN_GAME
            self.run_room_game(room)

        elif text_lower == "list":
            players_str = ", ".join([p.username for p in room.players])
            if not players_str:
                players_str = "No players yet"
            sock.sendall(f"Players: {players_str}\n".encode())

        elif text_lower == "close":
            _log_info(f"Room {room.room_id} closed by host")
            self._broadcast_room(room, "Room closed.\n")
            self._close_room(room)
            self.client_state[sock] = STATE_IN_LOBBY

        else:
            sock.sendall(b"Invalid command. Type START, LIST, or CLOSE.\n")

    def send_room_list(self, conn):
        """Send list of active rooms to a client."""
        if not self.game_control.rooms:
            conn.sendall(b"No active games.\n")
            return

        for room_id, room in self.game_control.rooms.items():
            msg = f"Room {room_id} - Host: {room.host_client.username}, Players: {len(room.players)}\n"
            try:
                conn.sendall(msg.encode())
            except:
                pass

    def _broadcast_room(self, room, message):
        """Send message to all players in a room."""
        for player in list(room.players):
            try:
                player.conn.sendall(message.encode())
            except:
                pass

    def _close_room(self, room):
        """Close a room and return players to lobby."""
        if room.room_id not in self.game_control.rooms:
            return

        for player in list(room.players):
            self.client_state[player.conn] = STATE_IN_LOBBY

        del self.game_control.rooms[room.room_id]

    def _drop_client(self, sock):
        """Remove a client and clean up state."""
        player = self.socket_to_player.pop(sock, None)
        if player and player in self.clients:
            self.clients.remove(player)
            _log_info(f"Player '{player.username}' disconnected")

        self.client_state.pop(sock, None)
        self.client_data.pop(sock, None)

        try:
            sock.close()
        except:
            pass

    def broadcast(self, message):
        """Broadcast to all clients in lobby."""
        for client in self.clients:
            try:
                client.conn.sendall(message.encode())
            except:
                pass

    def clear_client_screens(self):
        """Clear screens for all clients."""
        self.broadcast("\033[H\033[2J")

    def run_room_game(self, room):
        """Run trivia game for a specific room (blocking while game runs)."""
        questions = self.game_control._load_questions()
        if isinstance(questions, str):
            try:
                questions = json.loads(questions)
            except:
                questions = []

        for i, q_data in enumerate(questions):
            if not room.players:
                break

            self._clear_room_screens(room)
            q_text, o1, o2, o3, o4, correct = q_data
            correct = str(correct).strip()

            prompt = (
                f"Question {i+1}:\n{q_text}\n"
                f"1) {o1}\n2) {o2}\n3) {o3}\n4) {o4}\n\n"
                f"Answer (1-4): "
            )
            self._broadcast_room(room, prompt)

            # Collect answers
            answered = set()
            answers = {}
            deadline = time.time() + 45  # 45 second timeout per question

            while time.time() < deadline and len(answered) < len(room.players):
                try:
                    readable, _, _ = select.select(
                        [p.conn for p in room.players],
                        [], [],
                        1
                    )
                except:
                    continue

                for sock in readable:
                    if sock in answered:
                        continue

                    try:
                        data = sock.recv(1024)
                    except:
                        continue

                    if not data:
                        continue

                    text = data.decode(errors="ignore").strip()
                    answer = None
                    for ch in text:
                        if ch in "1234":
                            answer = ch
                            break

                    if not answer:
                        try:
                            sock.sendall(b"Invalid. Type 1-4.\n")
                        except:
                            pass
                        continue

                    answers[sock] = answer
                    for p in room.players:
                        if p.conn is sock:
                            if answer == correct:
                                room.scores[p] = room.scores.get(p, 0) + 1
                                try:
                                    sock.sendall(b"Correct!\n")
                                except:
                                    pass
                            else:
                                try:
                                    sock.sendall(b"Wrong!\n")
                                except:
                                    pass
                            answered.add(sock)
                            break

            # Show results
            time.sleep(2)

        # Show leaderboard
        self.show_room_leaderboard(room)

    def _clear_room_screens(self, room):
        """Clear terminal for room players."""
        self._broadcast_room(room, "\033[H\033[2J")

    def show_room_leaderboard(self, room):
        """Display final scores for room."""
        self._clear_room_screens(room)
        sorted_results = sorted(room.scores.items(), key=lambda x: x[1], reverse=True)
        msg = "\n=== FINAL SCORES ===\n"
        for i, (player, score) in enumerate(sorted_results, 1):
            msg += f"{i}. {player.username}: {score} points\n"
        msg += "\nThanks for playing!\n"
        self._broadcast_room(room, msg)
        self._close_room(room)

    def show_leaderboard(self):
        """Display final global leaderboard."""
        self.clear_client_screens()
        # Not implemented for room mode


if __name__ == "__main__":
    server = KahootServer()
    server.Run()
