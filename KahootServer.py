# ============================================================================
# Kahoot Server - Concurrent Multi-Client Handler
# ============================================================================
# Non-blocking event-driven architecture using select() and state machine.
# Allows multiple clients to connect and interact simultaneously.
# ============================================================================

import socket
import select
import time
from ConsoleLogger import ConsoleLogger
from GameManager import GameManager
from NetworkHelpers import NetworkHelpers
from KahootStateMachine import (
    KahootStateMachine,
    STATE_AWAITING_USERNAME,
    STATE_IN_LOBBY,
)


CLIENT_DISCONNECTED = "CLIENT_DISCONNECTED"
CLIENT_RESPONSE_TIMEOUT = 60
WELCOME_MESSAGE = "\n\033[1;35m╔══════════════════════════════════════╗\n║     WELCOME TO KAHOOT!               ║\n║                                      ║\n║   Get ready for an epic quiz!        ║\n╚══════════════════════════════════════╝\033[0m\n\n"

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

        # State machine handler
        self.state_machine = KahootStateMachine(
            self.clients,
            self.client_state,
            self.client_data,
            self.socket_to_player,
            self.game_control,
            self.network_helper,
        )

    def Run(self):
        """Main server loop: Non-blocking concurrent handling of multiple clients."""
        self.server_socket.listen(self.num_players)
        ConsoleLogger.init_server_console(self.server_address)

        # Main event loop
        while True:
            # Monitor server socket + all active client sockets
            readable_sockets = [self.server_socket] + list(self.client_state.keys())
            readable, _, _ = select.select(readable_sockets, [], [], 0.1)  # 100ms timeout

            # Handle new connections
            if self.server_socket in readable:
                try:
                    conn, addr = self.server_socket.accept()
                    # Connection accepted; header will reflect counts
                    
                    # Send welcome message to client only
                    self.network_helper.send_text(conn, WELCOME_MESSAGE)
                    
                    self.client_state[conn] = STATE_AWAITING_USERNAME
                    self.client_data[conn] = {"deadline": time.time() + CLIENT_RESPONSE_TIMEOUT}
                    self.network_helper.send_text(conn, "Enter your username: ")
                except OSError:
                    pass

            # Handle messages from existing clients
            for sock in readable:
                if sock is self.server_socket:
                    continue
                self._handle_client_message(sock)
            
            # Update all active games (non-blocking) - server checks timeouts, GameManager updates state
            self._update_active_games()

            # Update header when counts change
            ConsoleLogger.update_server_header(
                len(self.clients),
                len(self.client_state),
                len(self.game_control.rooms),
            )

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
        self.state_machine.handle_message(sock, text)

    def _drop_client(self, sock):
        """Remove a client and clean up state."""
        player = self.socket_to_player.pop(sock, None)
        if player and player in self.clients:
            self.clients.remove(player)
            ConsoleLogger.disconnected(f"{player.username} disconnected")

        self.client_state.pop(sock, None)
        self.client_data.pop(sock, None)

        try:
            sock.close()
        except:
            pass

    def _update_active_games(self):
        """
        Update all active games each loop iteration.
        GameManager handles all game logic; server just calls update.
        """
        for room_id in list(self.game_control.active_games.keys()):
            game_state = self.game_control.active_games.get(room_id)
            if not game_state:
                continue
            
            # Let GameManager update game state
            is_running = self.game_control.update_game(room_id)
            
            if not is_running:
                # Game finished
                self.game_control.end_game(room_id)
                room = game_state['room']
                # Return players to lobby
                for player in list(room.players):
                    self.client_state[player.conn] = STATE_IN_LOBBY
                # Close room
                self.state_machine.close_room(room)