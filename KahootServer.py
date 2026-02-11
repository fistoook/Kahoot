# ============================================================================
# Kahoot Server - NETWORKING
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
CLIENT_RESPONSE_TIMEOUT = 60  # Timeout for waiting on client responses (username, commands)

# Print functions with color
def _log_info(message):
    """Log an information message in cyan."""
    print(f"{Fore.CYAN}{Style.BRIGHT}[INFO]{Style.RESET_ALL} {message}")

def _log_warn(message):
    """Log a warning message in yellow."""
    print(f"{Fore.YELLOW}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {message}")


# ============================================================================
# Main Server Class
# ============================================================================
class KahootServer:
    def __init__(self, host='127.0.0.1', port=5555):
        """Initialize the Kahoot server with listening socket and game manager."""
        self.server_address = (host, port)
        self.num_players = 50  # Max players for global game
        self.clients = []  # List of Player objects in lobby or global game
        self.server_socket = socket.socket()
        self.server_socket.bind(self.server_address)
        self.game_control = GameManager()  # Loads and manages questions

    def Run(self):
        """Main server loop: accept connections, handle them."""
        # Listen for incoming connections
        self.server_socket.listen(self.num_players)

        _log_info(f"Server started on {self.server_address}. Waiting for players...")

        # Accept connections until max players reached (this can be modified for continuous play)
        while len(self.clients) < self.num_players:
            # Use select to timeout every 1 second to remain responsive
            readable, _, _ = select.select([self.server_socket], [], [], 1)

            if self.server_socket not in readable:
                continue  # Timeout, loop again
            try:
                conn, addr = self.server_socket.accept()  # Accept new client connection
            except OSError:
                continue  # Socket was closed
            try:
                result = self.treat_client(conn, addr)  # Handle login and route to host/join
                if result == CLIENT_DISCONNECTED:
                    continue
            except (ConnectionError, OSError):
                conn.close()
                continue
        
        return # Exit after handling clients (modify for continuous play or room-only mode)


    def treat_client(self, conn, addr):
        """Receive username from new client, add to lobby, show rooms, and wait for host/join command."""
        conn.sendall(b"Welcome to Kahoot! Enter your username: ")  # Prompt for username

        # Wait for username with a timeout; disconnect if no response
        name = None
        deadline = time.time() + CLIENT_RESPONSE_TIMEOUT
        disconnected = False

        while time.time() < deadline:
            r, _, _ = select.select([conn], [], [], 1)
            if conn not in r:
                continue
            try:
                data = conn.recv(1024)  # Receive username
            except (ConnectionError, OSError):
                data = b""

            if not data:  # Client disconnected before sending username
                self._drop_client(conn)
                disconnected = True
                break

            name = data.decode().strip()  # Decode and strip username
            if name:
                break

        if disconnected:
            return CLIENT_DISCONNECTED  # Skip to next iteration

        if not name:
            name = f"{addr[0]}:{addr[1]}"  # Fallback to IP:port if blank

        # Create Player object and add to lobby
        self.clients.append(Player(conn, name))
        _log_info(f"Player {len(self.clients)} connected from {addr} as '{name}'")

        # Broadcast new player to all lobby members
        self.broadcast(f"Lobby: {len(self.clients)}/{self.num_players} players connected.\n")

        # Send welcome message and available rooms
        self.clients[-1].conn.sendall(b"Here are all of the ongoing games:\n")
        self.send_room_list(self.clients[-1].conn)
        self.clients[-1].conn.sendall(b"If you would like to join a game, please enter the command Join <room ID>.\n")
        self.clients[-1].conn.sendall(b"If you would like to host a game, please enter the command Host <game name>.\n")
        
        # Wait for host/join command or connection loss
        self._treat_client_commands(self.clients[-1])

    def _treat_client_commands(self, player):
        """Wait for 'Host <name>' or 'Join <room_id>' command from a player in the lobby."""
        response = None
        deadline = time.time() + CLIENT_RESPONSE_TIMEOUT
        disconnected = False

        while time.time() < deadline:
            try:
                data = player.conn.recv(1024)
            except (ConnectionError, OSError):
                self._drop_client(player.conn)
                return

            if not data:
                self._drop_client(player.conn)
                return

            text = data.decode().strip()
            
            # Host command: "Host <game_name>"
            if text.lower().startswith("host "):
                game_name = text[5:].strip()
                while not game_name:
                    try:
                        player.conn.sendall(b"Game name cannot be empty. Please enter a valid name.\n")
                    except (ConnectionError, OSError):
                        self._drop_client(player.conn)
                        return
                    try:
                        data = player.conn.recv(1024)
                    except (ConnectionError, OSError):
                        self._drop_client(player.conn)
                        return
                    if not data:
                        self._drop_client(player.conn)
                        return
                    game_name = data.decode().strip()
                
                # Create new room with this player as host
                room_id = str(len(self.game_control.rooms) + 1).zfill(4)
                new_room = Room(room_id, player)
                self.game_control.rooms[room_id] = new_room
                
                try:
                    player.conn.sendall(f"Game '{game_name}' hosted successfully! Your room ID is {room_id}.\n".encode())
                    player.conn.sendall(b"Type START to begin, LIST to show players, or CLOSE to cancel the room.\n")
                except (ConnectionError, OSError):
                    self._drop_client(player.conn)
                
                # Enter host control loop (waits for START/LIST/CLOSE)
                self._wait_for_host_start(new_room)
                break
            
            # Join command: "Join <room_id>"
            elif text.lower().startswith("join "):
                room_id = text[5:].strip()
                if room_id not in self.game_control.rooms:
                    try:
                        player.conn.sendall(b"Invalid room ID. Please enter a valid ID from the list of active games.\n")
                    except (ConnectionError, OSError):
                        self._drop_client(player.conn)
                    continue
                
                room = self.game_control.rooms[room_id]
                
                # Prevent joining if game already started
                if room.game_started:
                    try:
                        player.conn.sendall(b"This game has already started. Please join a different room.\n")
                    except (ConnectionError, OSError):
                        self._drop_client(player.conn)
                    continue
                
                # Add player to room
                room.players.append(player)
                room.scores[player] = 0
                
                try:
                    player.conn.sendall(f"Joined game '{room.host_client.username}' successfully! Waiting for host to start the game...\n".encode())
                except (ConnectionError, OSError):
                    self._drop_client(player.conn)
                
                # Notify host of new joining player
                try:
                    room.host_client.conn.sendall(f"{player.username} joined your room.\n".encode())
                except (ConnectionError, OSError):
                    self._drop_client(room.host_client.conn)
                break
            
            # Invalid command
            else:
                try:
                    player.conn.sendall(b"Invalid command. Please enter 'Host <game name>' to host a game or 'Join <room ID>' to join an existing game.\n")
                except (ConnectionError, OSError):
                    self._drop_client(player.conn)


    def send_room_list(self, conn):
        """Send list of active rooms to the client."""
        if not self.game_control.rooms:
            try:
                conn.sendall(b"No active games.\n")
            except (ConnectionError, OSError):
                self._drop_client(conn)
            return

        # List each room with host name and player count
        for room_id, room in self.game_control.rooms.items():
            try:
                conn.sendall(f"Room {room_id} - Host: {room.host_client.username}, Players: {len(room.players)}\n".encode())
            except (ConnectionError, OSError):
                self._drop_client(conn)
                return

    def _wait_for_host_start(self, room):
        """Wait for host to issue START, LIST, or CLOSE command."""
        host_conn = room.host_client.conn
        while True:
            try:
                readable, _, _ = select.select([host_conn], [], [], 1)
            except OSError:
                continue

            if host_conn not in readable:
                continue

            try:
                data = host_conn.recv(1024)
            except (ConnectionError, OSError):
                self._close_room(room)
                return

            if not data:
                self._close_room(room)
                return

            text = data.decode(errors="ignore").strip().lower()
            
            # Host starts the game
            if text == "start":
                room.game_started = True
                self._broadcast_room(room, "Game is starting now!\n")
                self.game_control.run_room_game(room)  # Run the room-specific game loop
                return
            
            # Host lists current players
            if text == "list":
                self._send_room_player_list(host_conn, room)
                continue
            
            # Host closes the room
            if text == "close":
                self._broadcast_room(room, "Room closed by host.\n")
                self._close_room(room)
                return

            # Invalid host command
            try:
                host_conn.sendall(b"Invalid host command. Type START, LIST, or CLOSE.\n")
            except (ConnectionError, OSError):
                self._close_room(room)
                return

    def _send_room_player_list(self, conn, room):
        """Send host a list of all players currently in the room."""
        players = ", ".join([p.username for p in room.players])
        if not players:
            players = "No players yet"
        try:
            conn.sendall(f"Players in room {room.room_id}: {players}\n".encode())
        except (ConnectionError, OSError):
            self._drop_client(conn)

    def _broadcast_room(self, room, message):
        """Send message to all players in a room."""
        for player in list(room.players):
            try:
                player.conn.sendall(message.encode())
            except (ConnectionError, OSError):
                self._drop_client(player.conn)

    def _clear_room_screens(self, room):
        """Clear terminal screens for all players in a room using ANSI codes."""
        self._broadcast_room(room, "\033[H\033[2J")

    def _close_room(self, room):
        """Delete room from active rooms and clean up."""
        if room.room_id in self.game_control.rooms:
            del self.game_control.rooms[room.room_id]

    def _drop_client(self, client):
        """Remove a client (Player object or raw socket) from the lobby."""
        target = None
        if client in self.clients:
            target = client
        else:
            # Search for Player object containing this socket
            for player in list(self.clients):
                if getattr(player, "conn", None) is client:
                    target = player
                    break
        if target is not None:
            self.clients.remove(target)
        try:
            if hasattr(client, "close"):
                client.close()
        except:
            pass

    def broadcast(self, message):
        """Send message to all clients in the global lobby."""
        for client in self.clients:
            try:
                client.conn.sendall(message.encode())
            except:
                self.clients.remove(client)

    def clear_client_screens(self):
        """Clear screens for all clients in global game using ANSI codes."""
        self.broadcast("\033[H\033[2J")