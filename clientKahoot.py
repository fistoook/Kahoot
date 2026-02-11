import socket
import sys
import threading

class KahootClient:
    def __init__(self, host='0.0.0.0', port=5555):
        self.server_address = (host, port)
        self.client_socket = socket.socket()
        self.is_running = False

    def connect(self):
        try:
            self.client_socket.connect(self.server_address)
            print(f"[*] Connected to Kahoot server at {self.server_address[0]}:{self.server_address[1]}")
            self.is_running = True
            return True
        except ConnectionRefusedError:
            print("[!] Error: Could not connect to server. Is it running?")
            return False
        except Exception as e:
            print(f"[!] Unexpected error during connection: {e}")
            return False

    def start(self):
        if not self.is_running:
            if not self.connect():
                return

        receiver = threading.Thread(target=self._receive_loop, daemon=True)
        receiver.start()

        try:
            while self.is_running:
                message = sys.stdin.readline()
                if message and self.is_running:
                    self.client_socket.sendall(message.encode())
        except KeyboardInterrupt:
            print("\n[*] Player exited the game.")
        finally:
            self.close()

    def _receive_loop(self):
        while self.is_running:
            try:
                data = self.client_socket.recv(4096)
                if not data:
                    print("\n[!] Connection closed by server.")
                    self.is_running = False
                    break
                print(data.decode(errors="ignore"), end="", flush=True)
            except Exception:
                self.is_running = False
                break

    def close(self):
        self.is_running = False
        try:
            self.client_socket.close()
        except:
            pass
        print("[*] Client socket closed.")


if __name__ == "__main__":
    client = KahootClient()
    client.start()