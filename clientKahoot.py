import socket
import time
from ConsoleLogger import ConsoleLogger
from KahootClientParser import KahootClientMessageParser
from NetworkHelpers import NetworkHelpers

class KahootClient:
    def __init__(self, host='127.0.0.1', port=5555):
        """Initialize connection settings, socket, and helpers."""
        self.server_address = (host, port)
        self.client_socket = socket.socket()
        self.client_socket.settimeout(0.5)  # 0.5 second timeout for non-blocking loop
        self.is_running = False
        # Helpers for network sends and server message parsing.
        self.network_helper = NetworkHelpers()
        self.message_parser = KahootClientMessageParser(self)
        # Countdown timer state.
        self.countdown_end_time = None
        self.displaying_countdown = False
        self.last_countdown_display = 0
        self.countdown_duration = 20

    def connect(self):
        """Connect to the server and mark the client as running."""
        try:
            self.client_socket.connect(self.server_address)
            ConsoleLogger.connected(f"Connected to Kahoot server at {self.server_address[0]}:{self.server_address[1]}")
            self.is_running = True
            return True
        except ConnectionRefusedError:
            ConsoleLogger.error("Could not connect to server. Is it running?")
            return False
        except Exception as e:
            ConsoleLogger.error(f"Unexpected error during connection: {e}")
            return False

    def start(self):
        """Start the receive loop and run until exit."""
        # Main loop: connect once and then receive messages until stopped.
        if not self.is_running:
            if not self.connect():
                return
        try:
            while self.is_running:
                # Display countdown if active.
                if self.displaying_countdown:
                    self._update_countdown_display()
                self._receive_messages()
        except KeyboardInterrupt:
            ConsoleLogger.warn("Player exited the game.")
        finally:
            self.close()

    def _receive_messages(self):
        """Read one server payload and forward it to the parser."""
        # Receive raw bytes from the server (socket timeout is 0.5s).
        try:
            data = self.client_socket.recv(4096)
        except socket.timeout:
            # Timeout is normal; just loop again to display countdown.
            return
        except Exception as e:
            ConsoleLogger.error(f"Socket error: {e}")
            self.is_running = False
            return

        if not data:
            ConsoleLogger.disconnected("Connection closed by server.")
            self.is_running = False
            return
        
        # Provide a safe send callback so the parser can respond to prompts.
        self.message_parser.handle_data(
            data,
            lambda line: self.network_helper.send_line(self.client_socket, line),
        )

    def start_countdown(self, seconds):
        """Start a countdown timer for a question (called by parser)."""
        self.countdown_end_time = time.time() + seconds
        self.displaying_countdown = True
        self.last_countdown_display = 0
        self.countdown_duration = seconds

    def _update_countdown_display(self):
        """Display and update the countdown timer at the top of the screen."""
        if not self.countdown_end_time:
            return
        
        current_time = time.time()
        remaining = max(0, int(self.countdown_end_time - current_time))
        
        # Only update display once per second to avoid spam.
        if current_time - self.last_countdown_display < 1.0 and remaining > 0:
            return
        
        self.last_countdown_display = current_time
        
        # Update countdown at top of screen using ANSI positioning
        ConsoleLogger.update_countdown_timer(remaining)
        
        if remaining == 0:
            self.displaying_countdown = False
            self.countdown_end_time = None

    def _input_thread_worker(self):
        """DEPRECATED: No longer used (threading removed)."""
        pass

    def close(self):
        """Stop the client and close the socket safely."""
        self.is_running = False
        try:
            self.client_socket.close()
        except:
            pass
        ConsoleLogger.disconnected("Client socket closed.")


if __name__ == "__main__":
    client = KahootClient()
    client.start()