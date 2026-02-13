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

    def show_room_leaderboard(self, room):
        """Send the final leaderboard to all players in a room."""
        self.clear_room_screens(room)
        sorted_results = sorted(room.scores.items(), key=lambda item: item[1], reverse=True)
        leaderboard_msg = "\n--- FINAL LEADERBOARD ---\n"
        rankings = {}
        for player, score in sorted_results:
            name = player.username
            if score not in rankings:
                rankings[score] = []
            rankings[score].append(name)

        place = 1
        for score in sorted(rankings.keys(), reverse=True):
            players = ", ".join(rankings[score])
            leaderboard_msg += f"{place}. {players} with {score} points\n"
            place += len(rankings[score])

        self.broadcast_room(room, leaderboard_msg + "\nThanks for playing!\n")

    def send_room_list(self, conn, rooms):
        """Send list of active rooms to a client."""
        lines = []
        if not rooms:
            lines.append("No active games. Try hosting one with 'Host <game name>'!")
        else:
            for room_id, room in rooms.items():
                lines.append(
                    f"Room {room_id} - Host: {room.host_client.username} - Players: {len(room.players)}"
                )
        payload = "AVAILABLE ROOMS:\n" + "\n".join(lines)
        self.send_text(conn, payload)

    def broadcast_lobby_room_list(self, client_state, rooms, lobby_state):
        """Broadcast updated room list to all lobby clients."""
        for sock, state in list(client_state.items()):
            if state == lobby_state:
                self.send_room_list(sock, rooms)
