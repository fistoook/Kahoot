import socket
import select
import json
import time
from GameManager import GameManager
from KahootPlayer import Player
from KahootRoom import Room


CLIENT_DISCONNECTED = "CLIENT_DISCONNECTED"
CLIENT_RESPONSE_TIMEOUT = 30
################## Client Handling ###################
class KahootServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.server_address = (host, port)
        self.num_players = 50
        self.timeout = 90 
        self.clients = []
        self.server_socket = socket.socket()
        self.server_socket.bind(self.server_address)
        self.game_control = GameManager()

    def Run(self):
        # Listen for incoming connections
        self.server_socket.listen(self.num_players)

        print(f"Server started on {self.server_address}. Waiting for {self.num_players} players...")

        while len(self.clients) < self.num_players:
            # Use select to wait for incoming connections with a timeout
            readable, _, _ = select.select([self.server_socket], [], [], 1)

            if self.server_socket not in readable:
                continue # Timeout, loop again to check for shutdown signal
            try:
                conn, addr = self.server_socket.accept() # New client connection
            except OSError:
                continue # Socket was closed
            try:
                result = self.treat_client(conn, addr) # Handle client connection and setup
                if result == CLIENT_DISCONNECTED:
                    continue
            except (ConnectionError, OSError):
                conn.close()
                continue

        self.run_game()


    def treat_client(self, conn, addr):
        conn.sendall(b"Welcome to Kahoot! Enter your username: ") # Prompt new client for username

        # Wait for username with a timeout, and handle client disconnection during this phase
        name = None
        deadline = time.time() + CLIENT_RESPONSE_TIMEOUT

        disconnected = False

        while time.time() < deadline:
            r, _, _ = select.select([conn], [], [], 1)
            if conn not in r:
                continue
            try:
                data = conn.recv(1024) # receive username
            except (ConnectionError, OSError):
                data = b""

            if not data: # client disconnected before sending username
                self._drop_client(conn)
                disconnected = True
                break

            name = data.decode().strip() # decode username
            if name:
                break

        if disconnected:
            return CLIENT_DISCONNECTED # skip to next loop iteration to wait for another client

        if not name:
            name = f"{addr[0]}:{addr[1]}" # fallback to IP:port if no username provided

        # Add new player to the list of clients
        self.clients.append(Player(conn, name))
        print(f"Player {len(self.clients)} connected from {addr} as '{name}'")

        # Update lobby status for all clients
        self.broadcast(f"Lobby: {len(self.clients)}/{self.num_players} players connected.\n")

        self.clients[-1].conn.sendall(b"Successfully joined our server!\n") # Acknowledge successful join
        self.clients[-1].conn.sendall(b"Here are all of the ongoing games:\n") # Send list of active rooms to the new client
        self.send_room_list(self.clients[-1].conn)
        self.clients[-1].conn.sendall(b"If you would like to join a game, please enter the command Join <room ID>.\n") # Send list of active rooms to the new client
        self.clients[-1].conn.sendall(b"If you would like to host a game, please enter the command Host <game name>.\n") # Send instructions to host a new game
        self._treat_client_commands(self.clients[-1]) # Start listening for client commands (join/host)

    def _treat_client_commands(self, player):
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
            if text.lower().startswith("host "):
                game_name = text[5:].strip()
                if not game_name:
                    try:
                        player.conn.sendall(b"Game name cannot be empty. Please enter a valid name.\n")
                    except (ConnectionError, OSError):
                        self._drop_client(player.conn)
                    continue
                room_id = str(len(self.game_control.rooms) + 1).zfill(4) # Generate a new room ID
                new_room = Room(room_id, player) # Create a new room with the player as host
                self.game_control.rooms[room_id] = new_room # Add the new room to the game control's list of rooms
                try:
                    player.conn.sendall(f"Game '{game_name}' hosted successfully! Your room ID is {room_id}.\n".encode())
                except (ConnectionError, OSError):
                    self._drop_client(player.conn)
                break
            elif text.lower().startswith("join "):
                room_id = text[5:].strip()
                if room_id not in self.game_control.rooms:
                    try:
                        player.conn.sendall(b"Invalid room ID. Please enter a valid ID from the list of active games.\n")
                    except (ConnectionError, OSError):
                        self._drop_client(player.conn)
                    continue
                room = self.game_control.rooms[room_id]
                room.players.append(player) # Add the player to the room's list of players
                room.scores[player] = 0 # Initialize the player's score in the room
                try:
                    player.conn.sendall(f"Joined game '{room.host_client.username}' successfully! Waiting for host to start the game...\n".encode())
                except (ConnectionError, OSError):
                    self._drop_client(player.conn)
                break
            else:
                try:
                    player.conn.sendall(b"Invalid command. Please enter 'Host <game name>' to host a game or 'Join <room ID>' to join an existing game.\n")
                except (ConnectionError, OSError):
                    self._drop_client(player.conn)


    def send_room_list(self, conn):
        if not self.game_control.rooms:
            try:
                conn.sendall(b"No active games.\n")
            except (ConnectionError, OSError):
                self._drop_client(conn)
            return

        for room_id, room in self.game_control.rooms.items():
            try:
                conn.sendall(f"Room {room_id} - Host: {room.host_client.username}, Players: {len(room.players)}\n".encode())
            except (ConnectionError, OSError):
                self._drop_client(conn)
                return

    def _drop_client(self, client):
            if client in self.clients:
                self.clients.remove(client)
            try:
                client.close()
            except:
                pass

    def broadcast(self, message):
        for client in self.clients:
            try:
                client.conn.sendall(message.encode())
            except:
                self.clients.remove(client)

    def clear_client_screens(self):
        self.broadcast("\033[H\033[2J")

    def run_game(self):
        self.questions = self.game_control._load_questions()
        for i, q_data in enumerate(self.questions):
            if not self.clients:
                print("No players left. Ending game.")
                break

            self.clear_client_screens()

            q_text, o1, o2, o3, o4, correct = q_data
            correct = str(correct).strip()

            prompt = (
                f"Question {i+1}/{self.game_questions_count}:\n"
                f"{q_text}\n"
                f"1) {o1}\n"
                f"2) {o2}\n"
                f"3) {o3}\n"
                f"4) {o4}\n\n"
                f"You have {self.timeout} seconds. Type 1-4 and press Enter:\n"
            )
            self.broadcast(prompt)

            answered_this_round = set()
            answers_this_round = {}
            deadline = time.time() + self.timeout
            while time.time() < deadline and len(answered_this_round) < len(self.clients):
                remaining = deadline - time.time()
                wait_time = 1 if remaining > 1 else max(0, remaining)
                try:
                    readable, _, _ = select.select([client.conn for client in self.clients], [], [], wait_time)
                except OSError:
                    continue

                for s in readable:
                    if s in answered_this_round:
                        continue

                    try:
                        data = s.recv(1024)
                    except (ConnectionError, OSError):
                        self._drop_client(s)
                        continue

                    if not data:
                        self._drop_client(s)
                        continue

                    text = data.decode(errors="ignore").strip()

                    answer = None
                    for ch in text:
                        if ch in "1234":
                            answer = ch
                            break

                    if answer is None:
                        try:
                            s.sendall(b"Invalid answer. Type 1, 2, 3, or 4 and press Enter.\n")
                        except (ConnectionError, OSError):
                            self._drop_client(s)
                        continue

                    answers_this_round[s] = answer
                    if answer == correct:
                        self.scores[s] = self.scores.get(s, 0) + 1
                        try:
                            s.sendall(b" Correct!\n")
                        except (ConnectionError, OSError):
                            self._drop_client(s)
                    else:
                        try:
                            s.sendall(b" Wrong!\n")
                        except (ConnectionError, OSError):
                            self._drop_client(s)
                    answered_this_round.add(s)

            correct_players = 0
            wrong_players = 0
            no_answer_players = 0
            for s in list(self.clients):
                if s in answers_this_round:
                    if answers_this_round[s] == correct:
                        correct_players += 1
                    else:
                        wrong_players += 1
                else:
                    no_answer_players += 1

            summary = f"\n Time! Correct answer was: {correct}\n"
            if correct_players:
                summary += f" Correct: {correct_players} players\n"
            if wrong_players:
                summary += f" Wrong: {wrong_players} players\n"
            if no_answer_players:
                summary += f" No answer: {no_answer_players} players\n"

            self.broadcast(summary)
            self.broadcast("Moving to next question...\n")
            time.sleep(3.5)

        self.show_leaderboard()

    def show_leaderboard(self):
        self.clear_client_screens()
        sorted_results = sorted(self.scores.items(), key=lambda item: item[1], reverse=True)
        leaderboard_msg = "\n--- FINAL LEADERBOARD ---\n"
        rankings = {}
        for sock, score in sorted_results:
            name = self.names.get(sock, "Unknown")

            if score not in rankings:
                rankings[score] = []

            rankings[score].append(name)

        place = 1
        for score in sorted(rankings.keys(), reverse=True):
            players = ", ".join(rankings[score])
            leaderboard_msg += f"{place}. {players} with {score} points\n"
            place += len(rankings[score])

        self.broadcast(leaderboard_msg + "\nThanks for playing!")

        for c in list(self.clients):
            try:
                c.close()
            except:
                pass
        try:
            self.server_socket.close()
        except:
            pass