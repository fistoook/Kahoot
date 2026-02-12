import socket
from ConsoleLogger import ConsoleLogger

class KahootClient:
    def __init__(self, host='127.0.0.1', port=5555):
        self.server_address = (host, port)
        self.client_socket = socket.socket()
        self.is_running = False
        self.name_sent = False
        self.recv_buffer = ""

    def connect(self):
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
        if not self.is_running:
            if not self.connect():
                return
        try:
            while self.is_running:
                self._receive_messages()
        except KeyboardInterrupt:
            ConsoleLogger.warn("Player exited the game.")
        finally:
            self.close()

    def _receive_messages(self):
        try:
            data = self.client_socket.recv(4096)
        except Exception:
            self.is_running = False
            return

        if not data:
            ConsoleLogger.disconnected("Connection closed by server.")
            self.is_running = False
            return

        text = data.decode(errors="ignore")
        self.recv_buffer += text

        text = self.recv_buffer
        self.recv_buffer = ""
        lowered = text.lower()

         
        if "enter your username" in lowered and "welcome to kahoot" in lowered:
            prompt_index = lowered.find("enter your username")
            banner = text[:prompt_index].rstrip()
            if banner:
                print(banner, end="\n", flush=True)

        handled = self._handle_prompts(text)
        
        # Check if it's a question message
        if not handled and "Question" in text:
            # Extract and display question using ConsoleLogger
            lines = text.split('\n')
            for line in lines:
                if line.strip():
                    ConsoleLogger.question(line.strip())
            return
        
        # Only print non-prompt messages
        if not handled:
            print(text, end="", flush=True)

    def _handle_prompts(self, text):
        """Handle server prompts and return True if a prompt was handled."""
        lines = text.lower().split('\n')
        for lowered in lines:
            lowered = lowered.strip()
            if not self.name_sent and "enter your username" in lowered:
                ConsoleLogger.prompt("Enter your username:")
                name = input().strip()
                if not name:
                    name = "Player"
                self._send_line(name)
                self.name_sent = True
                return True

            if "successfully" in lowered:
                ConsoleLogger.success(lowered)
                return True
            
            if "join <room id>" in lowered or "host <game name>" in lowered:
                ConsoleLogger.prompt(lowered)
                command = input().strip()
                if command:
                    self._send_line(command)
                return True

            if "invalid command" in lowered or "invalid room id" in lowered or "game name cannot be empty" in lowered or "invalid host command" in lowered:
                ConsoleLogger.prompt(lowered)
                command = input().strip()
                if command:
                    self._send_line(command)
                return True

            if "type start" in lowered and "list" in lowered and "close" in lowered:
                ConsoleLogger.prompt(lowered)
                command = input().strip()
                if command:
                    self._send_line(command)
                return True

            if "how many questions would you like?" in lowered:
                ConsoleLogger.prompt(lowered)
                num_q = input().strip()
                if num_q.isdigit() and int(num_q) > 0:
                    self._send_line(num_q)
                    return True
            
            if "select a theme" in lowered and ("general" in lowered or "math" in lowered or "cyber" in lowered or "nature" in lowered):
                ConsoleLogger.prompt(lowered)
                theme = input().strip()
                if theme:
                    self._send_line(theme)
                return True
            
            if "invalid theme" in lowered:
                ConsoleLogger.prompt(lowered)
                theme = input().strip()
                if theme:
                    self._send_line(theme)
                return True
                
            if "type 1-4" in lowered or "type 1, 2, 3, or 4" in lowered:
                ConsoleLogger.question_counter(lines[0].strip())
                ConsoleLogger.question(lines[1].strip())
                for i in range(2, 6):
                    ConsoleLogger.option(lines[i].strip(), i)
                ConsoleLogger.prompt(lowered)
                answer = input().strip()
                if answer:
                    self._send_line(answer)
                return True
            
            if "players:" in lowered:
                ConsoleLogger.info(lowered)
                command = input().strip()
                if command:
                    self._send_line(command)
                return True
            
            if "room closed" in lowered:
                ConsoleLogger.info(lowered)
                command = input().strip()
                if command:
                    self._send_line(command)
                return True

            if "Invalid answer" in lowered:
                ConsoleLogger.error(lowered)
                answer = input().strip()
                if answer:
                    self._send_line(answer)
                return True
            
            if "game" in lowered and "hosted" in lowered:
                ConsoleLogger.success(lowered)

            if "available rooms" in lowered:
                ConsoleLogger.info(lowered)
                ConsoleLogger.prompt("Type 'Host <game name>' to host, 'Join <room ID>' to join, or 'View Rooms' to see available rooms:")
                answer = input().strip()
                if answer:
                    self._send_line(answer)
                return True

        return False

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
        ConsoleLogger.disconnected("Client socket closed.")


if __name__ == "__main__":
    client = KahootClient()
    client.start()
