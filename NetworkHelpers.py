class NetworkHelpers:
    def __init__(self):
        pass

    def _broadcast_room(self, room, message):
        """Send message to all players in a room."""
        for player in list(room.players):
            try:
                player.conn.sendall(message.encode())
            except:
                pass

    def send_line(self, conn, line):
        """Send a single line of text to a connection."""
        try:
            conn.sendall((line + "\n").encode())
        except:
            pass
