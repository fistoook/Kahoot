import socket
import sys
from colorama import Fore, Style, init


init(autoreset=True)

def _log_info(message):
    print(f"{Fore.CYAN}{Style.BRIGHT}[INFO]{Style.RESET_ALL} {message}")

def _log_warn(message):
    print(f"{Fore.YELLOW}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {message}")

def _log_error(message):
    print(f"{Fore.RED}{Style.BRIGHT}[ERROR]{Style.RESET_ALL} {message}")

class KahootClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.server_address = (host, port)
        self.client_socket = socket.socket()
        self.is_running = False
        self.name_sent = False

    def connect(self):
        try:
            self.client_socket.connect(self.server_address)
            _log_info(f"Connected to Kahoot server at {self.server_address[0]}:{self.server_address[1]}")
            self.is_running = True
            return True
        except ConnectionRefusedError:
            _log_error("Could not connect to server. Is it running?")
            return False
        except Exception as e:
            _log_error(f"Unexpected error during connection: {e}")
            return False

    def start(self):
        if not self.is_running:
            if not self.connect():
                return
        try:
            while self.is_running:
                self._receive_messages()
        except KeyboardInterrupt:
            _log_warn("Player exited the game.")
        finally:
            self.close()

    def _receive_messages(self):
        try:
            data = self.client_socket.recv(4096)
        except Exception:
            self.is_running = False
            return

        if not data:
            _log_warn("Connection closed by server.")
            self.is_running = False
            return

        text = data.decode(errors="ignore")
        print(text, end="", flush=True)

        self._handle_prompts(text)

    def _handle_prompts(self, text):
        lowered = text.lower()

        if not self.name_sent and "enter your username" in lowered:
            name = input().strip()
            if not name:
                name = "Player"
            self._send_line(name)
            self.name_sent = True
            return

        if "join <room id>" in lowered or "host <game name>" in lowered:
            command = input().strip()
            if command:
                self._send_line(command)
            return

        if "invalid command" in lowered or "invalid room id" in lowered or "game name cannot be empty" in lowered:
            command = input().strip()
            if command:
                self._send_line(command)
            return

        if "type 1-4" in lowered or "type 1, 2, 3, or 4" in lowered:
            answer = input().strip()
            if answer:
                self._send_line(answer)

    def _send_line(self, line):
        if not self.is_running:
            return
        try:
            self.client_socket.sendall((line + "\n").encode())
        except Exception:
            self.is_running = False

    def close(self):
        self.is_running = False
        try:
            self.client_socket.close()
        except:
            pass
        _log_info("Client socket closed.")


if __name__ == "__main__":
    client = KahootClient()
    client.start()