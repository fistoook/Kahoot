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
from NetworkHelpers import NetworkHelpers

init(autoreset=True)
CLIENT_DISCONNECTED = "CLIENT_DISCONNECTED"
CLIENT_RESPONSE_TIMEOUT = 60

# Client states for state machine
STATE_AWAITING_USERNAME = "awaiting_username"
STATE_IN_LOBBY = "in_lobby"
STATE_HOSTING = "hosting"
STATE_IN_ROOM = "in_room"
STATE_IN_GAME = "in_game"
STATE_AWAITING_QUESTION_COUNT = "awaiting_question_count"
STATE_AWAITING_THEME = "awaiting_theme"

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
        self.network_helper = NetworkHelpers()
        
        # State machine tracking
        self.client_state = {}  # Maps socket -> state
        self.client_data = {}   # Maps socket -> dict with tracking data
        self.socket_to_player = {}  # Maps socket -> Player object
        
        # Active games tracking for concurrent game support
        self.active_games = {}  # Maps room_id -> game state dict

    def Run(self):
        """Main server loop: Non-blocking concurrent handling of multiple clients."""
        self.server_socket.listen(self.num_players)
        _log_info(f"Server started on {self.server_address}. Accepting connections...")

        # Main event loop
        while True:
            # Monitor server socket + all active client sockets
            readable_sockets = [self.server_socket] + list(self.client_state.keys())
            readable, _, _ = select.select(readable_sockets, [], [], 0.1)  # 100ms timeout

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
        elif state == STATE_AWAITING_QUESTION_COUNT:
            self._handle_question_count(sock, text)
        elif state == STATE_AWAITING_THEME:
            self._handle_theme_selection(sock, text)
        elif state == STATE_IN_ROOM:
            # Player waiting for game to start, ignore input
            pass
        elif state == STATE_IN_GAME:
            # Player in active game, handle answer
            self._handle_game_answer(sock, text)

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

    def _handle_question_count(self, sock, text):
        """Process the number of questions from host."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        room = self.client_data.get(sock, {}).get("room")
        if not room:
            return

        # Validate the input is a positive integer
        if not text.isdigit() or int(text) <= 0:
            sock.sendall(b"Invalid number. Please enter a positive integer: ")
            return

        question_count = int(text)
        _log_info(f"Room {room.room_id} will have {question_count} questions")
        
        # Store question count in room data
        room.question_count = question_count
        
        # Transition to theme selection
        self.client_state[sock] = STATE_AWAITING_THEME
        sock.sendall(b"Select a theme (general, math, cyber, nature):\n")

    def _handle_theme_selection(self, sock, text):
        """Process theme selection from host."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        room = self.client_data.get(sock, {}).get("room")
        if not room:
            return

        # Validate theme selection
        valid_themes = ["general", "math", "cyber", "nature"]
        theme = text.lower().strip()
        
        if theme not in valid_themes:
            sock.sendall(b"Invalid theme. Please choose: general, math, cyber, or nature:\n")
            return

        _log_info(f"Room {room.room_id} selected theme: {theme}")
        
        # Store theme in room data
        room.theme = theme
        room.game_started = True
        
        # Notify all players game is starting
        self.network_helper._broadcast_room(room, f"Game starting with {theme} theme!\n")
        
        # Mark all players (including host) as in-game
        self.client_state[sock] = STATE_IN_GAME
        for p in room.players:
            self.client_state[p.conn] = STATE_IN_GAME
        
        # Start the game with the specified number of questions and theme
        self.game_control.run_room_game(room, room.question_count)
        
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
            _log_info(f"Host initiating game start for room {room.room_id}")
            # Transition to awaiting question count state
            self.client_state[sock] = STATE_AWAITING_QUESTION_COUNT
            sock.sendall(b"How many questions would you like?\n")

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

    def _handle_game_answer(self, sock, text):
        """
        Handle game answers during active game.
        Note: Currently unused as GameManager.run_room_game handles answers
        directly with its own select() loop while blocking.
        """
        pass


if __name__ == "__main__":
    server = KahootServer()
    server.Run()
