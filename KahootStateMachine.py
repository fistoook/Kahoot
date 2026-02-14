from ConsoleLogger import ConsoleLogger
from KahootRoom import Room
from KahootPlayer import Player

# Client states for state machine
STATE_AWAITING_USERNAME = "awaiting_username"
STATE_IN_LOBBY = "in_lobby"
STATE_HOSTING = "hosting"
STATE_IN_ROOM = "in_room"
STATE_IN_GAME = "in_game"
STATE_AWAITING_QUESTION_COUNT = "awaiting_question_count"
STATE_AWAITING_THEME = "awaiting_theme"


class KahootStateMachine:
    def __init__(self, clients, client_state, client_data, socket_to_player, game_control, network_helper):
        # Shared server state and helper dependencies.
        self.clients = clients
        self.client_state = client_state
        self.client_data = client_data
        self.socket_to_player = socket_to_player
        self.game_control = game_control
        self.network_helper = network_helper

    def handle_message(self, sock, text):
        """Route a message based on the current client state."""
        state = self.client_state.get(sock)

        # State routing based on the client lifecycle.
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
            self._handle_game_answer(sock, text)

    def _handle_username(self, sock, username):
        """Process username submission and add player to lobby."""
        if not username:
            username = "Player"

        # Create player entry and move client to lobby.
        player = Player(sock, username)
        self.clients.append(player)
        self.socket_to_player[sock] = player
        self.client_state[sock] = STATE_IN_LOBBY

        ConsoleLogger.player_action(username, "Joined from " + str(sock.getpeername()))

        self.network_helper.send_line(sock, f"{username}, you have successfully joined Kahoot!")
        self.network_helper.send_line(sock, "Type 'Host <game name>' to host, 'Join <room ID>' to join, or 'View Rooms' to see available rooms:")

    def _handle_lobby_command(self, sock, text):
        """Process Host/Join commands from lobby."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        if text.lower().strip() == "view rooms":
            self.network_helper.send_room_list(sock, self.game_control.rooms)
            return

        if text.lower().startswith("host "):
            game_name = text[5:].strip()
            if not game_name:
                self.network_helper.send_line(sock, "Game name cannot be empty. Please try again.")
                return

            # Create room and mark host state.
            room_id = str(len(self.game_control.rooms) + 1).zfill(4)
            room = Room(room_id, player)
            self.game_control.rooms[room_id] = room
            self.client_state[sock] = STATE_HOSTING
            self.client_data[sock]["room"] = room

            ConsoleLogger.room_event(room_id, f"Created by {player.username}")
            self.network_helper.send_line(sock, f"Game '{game_name}' hosted! Room ID: {room_id}")
            self.network_helper.send_line(sock, "Type START to begin, LIST to show players, or CLOSE to cancel.")

        elif text.lower().startswith("join "):
            room_id = text[5:].strip()
            if room_id not in self.game_control.rooms:
                self.network_helper.send_line(sock, "Invalid room ID. Try again.")
                return

            room = self.game_control.rooms[room_id]
            if room.game_started:
                self.network_helper.send_line(sock, "Game already started. Try another room.")
                return

            # Add player to room and update state.
            room.players.append(player)
            room.scores[player] = 0
            self.client_state[sock] = STATE_IN_ROOM
            self.client_data[sock]["room"] = room

            ConsoleLogger.room_event(room_id, f"{player.username} joined")
            self.network_helper.send_line(sock, f"Joined {room.host_client.username}'s room #{room_id}! Waiting to start...")
            self.network_helper.send_line(room.host_client.conn, f"{player.username} joined!")

        else:
            self.network_helper.send_line(sock, "Invalid command. Type 'Host <name>', 'Join <ID>', or 'View Rooms':")

    def _handle_question_count(self, sock, text):
        """Process the number of questions from host."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        room = self.client_data.get(sock, {}).get("room")
        if not room:
            return

        if not text.isdigit() or int(text) <= 0:
            self.network_helper.send_line(sock, "Invalid number. Please enter a positive integer: ")
            return

        # Persist question count and advance flow to theme selection.
        question_count = int(text)
        ConsoleLogger.room_event(room.room_id, f"Set to {question_count} questions")

        room.question_count = question_count
        self.client_state[sock] = STATE_AWAITING_THEME
        self.network_helper.send_line(sock, "Select a theme (general, math, cyber, nature):")

    def _handle_theme_selection(self, sock, text):
        """Process theme selection from host."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        room = self.client_data.get(sock, {}).get("room")
        if not room:
            return

        valid_themes = ["general", "math", "cyber", "nature"]
        theme = text.lower().strip()

        if theme not in valid_themes:
            self.network_helper.send_line(sock, "Invalid theme. Please choose: general, math, cyber, or nature:")
            return

        # Start game for all players in the room.
        ConsoleLogger.room_event(room.room_id, f"Theme selected: {theme}")

        room.theme = theme
        room.game_started = True

        self.network_helper.broadcast_room(room, f"Game starting with {theme} theme!\n")

        self.client_state[sock] = STATE_IN_GAME
        for p in room.players:
            self.client_state[p.conn] = STATE_IN_GAME

        self.game_control.init_game(room, room.question_count, theme)
        self.game_control.send_next_question(room.room_id)

    def _handle_host_command(self, sock, text):
        """Process START, LIST, CLOSE commands from host."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        room = self.client_data.get(sock, {}).get("room")
        if not room:
            return

        text_lower = text.lower()

        if text_lower == "start":
            ConsoleLogger.room_event(room.room_id, "Host initiated game start")
            self.client_state[sock] = STATE_AWAITING_QUESTION_COUNT
            self.network_helper.send_line(sock, "How many questions would you like?")

        elif text_lower == "list":
            players_str = ", ".join([p.username for p in room.players])
            if not players_str:
                players_str = "No players yet"
            self.network_helper.send_line(sock, f"Players: {players_str}")

        elif text_lower == "close":
            ConsoleLogger.room_event(room.room_id, "Closed by host")
            self.network_helper.broadcast_room(room, "Room closed.\n")
            self.close_room(room)
            self.client_state[sock] = STATE_IN_LOBBY

        else:
            self.network_helper.send_line(sock, "Invalid command. Type START, LIST, or CLOSE.")

    def _handle_game_answer(self, sock, text):
        """Handle game answers from players."""
        player = self.socket_to_player.get(sock)
        if not player:
            return

        room = self.client_data.get(sock, {}).get("room")
        if not room or room.room_id not in self.game_control.active_games:
            return

        answer_valid = self.game_control.process_answer(room.room_id, sock, text)

        if answer_valid:
            # Compare submitted answer to the current correct answer.
            game_state = self.game_control.active_games[room.room_id]
            correct_answer = game_state['correct_answer']
            if text.strip() == correct_answer:
                self.network_helper.send_line(sock, "Correct!")
            else:
                self.network_helper.send_line(sock, "Wrong!")
        else:
            self.network_helper.send_line(sock, "Invalid answer. Type 1, 2, 3, or 4 and press Enter.")

    def close_room(self, room):
        """Close a room and return players to lobby."""
        if room.room_id not in self.game_control.rooms:
            return

        # Reset all players in the room back to lobby.
        for player in list(room.players):
            self.client_state[player.conn] = STATE_IN_LOBBY

        del self.game_control.rooms[room.room_id]
