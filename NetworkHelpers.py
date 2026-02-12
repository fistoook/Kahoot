class NetworkHelpers:
    def __init__(self):
        pass

    def send_bytes(self, conn, data):
        """Send raw bytes to a connection."""
        try:
            conn.sendall(data)
        except:
            pass

    def send_text(self, conn, text):
        """Send a text payload as-is (no extra newline)."""
        self.send_bytes(conn, text.encode())

    def broadcast_clients(self, clients, message):
        """Broadcast to all clients in lobby."""
        for client in list(clients):
            try:
                client.conn.sendall(message.encode())
            except:
                pass

    def clear_client_screens(self, clients):
        """Clear screens for all clients."""
        self.broadcast_clients(clients, "\033[H\033[2J")

    def _broadcast_room(self, room, message):
        """Send message to all players in a room."""
        self.broadcast_room(room, message)

    def broadcast_room(self, room, message):
        """Send message to all players in a room."""
        for player in list(room.players):
            try:
                player.conn.sendall(message.encode())
            except:
                pass

    def clear_room_screens(self, room):
        """Clear screens for all players in a room."""
        self.broadcast_room(room, "\033[H\033[2J")

    def send_line(self, conn, line):
        """Send a single line of text to a connection."""
        try:
            conn.sendall((line + "\n").encode())
        except:
            pass
