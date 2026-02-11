import socket
import select
import json
import time
from GameManager import GameManager

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

    def _drop_client(self, client):
        if client in self.clients:
            self.clients.remove(client)
        try:
            client.close()
        except:
            pass

    def Run(self):
        self.server_socket.listen(self.num_players)

        print(f"Server started on {self.server_address}. Waiting for {self.num_players} players...")

        while len(self.clients) < self.num_players:
            readable, _, _ = select.select([self.server_socket], [], [], 1)
            if self.server_socket not in readable:
                continue
            try:
                conn, addr = self.server_socket.accept()
            except OSError:
                continue
            try:
                conn.sendall(b"Welcome! Enter your name and press Enter: ")
            except (ConnectionError, OSError):
                conn.close()
                continue

            name = None
            deadline = time.time() + 15

            disconnected = False

            while time.time() < deadline:
                r, _, _ = select.select([conn], [], [], 1)
                if conn not in r:
                    continue
                try:
                    data = conn.recv(1024)
                except (ConnectionError, OSError):
                    data = b""

                if not data:
                    self._drop_client(conn)
                    disconnected = True
                    break

                name = data.decode(errors="ignore").strip()
                if name:
                    break
            if disconnected:
                continue
            if not name:
                name = f"{addr[0]}:{addr[1]}"
            self.clients.append(conn)
            self.scores[conn] = 0
            self.names[conn] = name
            print(f"Player {len(self.clients)} connected from {addr} as '{name}'")
            self.broadcast(f"Lobby: {len(self.clients)}/{self.num_players} players connected.\n")
            try:
                conn.sendall(b"Joined! Waiting for other players...\n")
            except (ConnectionError, OSError):
                self._drop_client(conn)

        self.broadcast("All players connected! The game is starting now.\n")
        self.run_game()

    def broadcast(self, message):
        for client in self.clients:
            try:
                client.send(message.encode())
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
                    readable, _, _ = select.select(self.clients, [], [], wait_time)
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