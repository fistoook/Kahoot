import socket
import random
import csv
from colorama import Fore, Style, init, Back
import time
import select
from NetworkHelpers import NetworkHelpers
init(autoreset=True)

_log_warn = lambda msg: print(f"{Fore.YELLOW}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {msg}")
################## Game Logic ###################
class GameManager:
    def __init__(self):
        self.rooms = {}
        self.game_questions_count = 2
        self.timeout = 20
        self.network_helper = NetworkHelpers()
        self.theme = "general"

    def run_room_game(self, room, num_questions=None):
        self.theme = room.theme
        """Run the game loop for a specific room with independent scores."""
        if num_questions is None:
            num_questions = self.game_questions_count
        room.questions = self._load_questions(num_questions=num_questions)

        for i, q_data in enumerate(room.questions):
            if not room.players:
                _log_warn("No players left in room. Ending game.")
                break

            self.clear_room_screens(room)

            # Parse question data
            q_text, o1, o2, o3, o4, correct = q_data
            correct = str(correct).strip()

            # Format and broadcast question to room
            prompt = (
                f"Question {i+1}/{num_questions}:\n"
                f"{q_text}\n"
                f"1) {o1}\n"
                f"2) {o2}\n"
                f"3) {o3}\n"
                f"4) {o4}\n\n"
                f"You have {self.timeout} seconds. Type 1-4 and press Enter:\n"
            )
            self.network_helper._broadcast_room(room, prompt)

            # Collect answers from room players
            answered_this_round = set()
            answers_this_round = {}  # Maps socket -> answer
            deadline = time.time() + self.timeout
            conn_to_player = {p.conn: p for p in room.players}  # Mapping for socket to Player

            while time.time() < deadline and len(answered_this_round) < len(room.players):
                remaining = deadline - time.time()
                wait_time = 1 if remaining > 1 else max(0, remaining)
                try:
                    readable, _, _ = select.select(list(conn_to_player.keys()), [], [], wait_time)
                except OSError:
                    continue

                for s in readable:
                    if s in answered_this_round:
                        continue  # Already answered this round

                    try:
                        data = s.recv(1024)
                    except (ConnectionError, OSError):
                        self._drop_client(s)
                        continue

                    if not data:  # Connection closed
                        self._drop_client(s)
                        continue

                    text = data.decode(errors="ignore").strip()

                    # Extract first digit 1-4 from response
                    answer = None
                    if text == "1" or text == "2" or text == "3" or text == "4":
                        answer = text.strip()
                        

                    if answer is None:
                        try:
                            self.network_helper.send_line(s, "Invalid answer. Type 1, 2, 3, or 4 and press Enter.")
                        except (ConnectionError, OSError):
                            self._drop_client(s)
                        continue

                    # Record answer and update room score if correct
                    answers_this_round[s] = answer
                    player = conn_to_player.get(s)
                    if player is not None and answer == correct:
                        room.scores[player] = room.scores.get(player, 0) + 1
                        try:
                            self.network_helper.send_line(s, " Correct!")
                        except (ConnectionError, OSError):
                            self._drop_client(s)
                    else:
                        try:
                            self.network_helper.send_line(s, " Wrong!")
                        except (ConnectionError, OSError):
                            self._drop_client(s)
                    answered_this_round.add(s)

            # Tally results for the room
            correct_players = 0
            wrong_players = 0
            no_answer_players = 0
            for p in list(room.players):
                if p.conn in answers_this_round:
                    if answers_this_round[p.conn] == correct:
                        correct_players += 1
                    else:
                        wrong_players += 1
                else:
                    no_answer_players += 1

            # Format and broadcast round summary
            summary = f"\n Time! Correct answer was: {correct}\n"
            if correct_players:
                summary += f" Correct: {correct_players} players\n"
            if wrong_players:
                summary += f" Wrong: {wrong_players} players\n"
            if no_answer_players:
                summary += f" No answer: {no_answer_players} players\n"

            self.network_helper._broadcast_room(room, summary)
            self.network_helper._broadcast_room(room, "Moving to next question...\n")
            time.sleep(3.5)  # Pause before next question

        # Display room-specific leaderboard when game ends
        self.show_room_leaderboard(room)

    def clear_room_screens(self, room):
        for p in room.players:
            try:
                self.network_helper.send_line(p.conn, "\033[2J\033[H")  # Clear screen ANSI code
            except (ConnectionError, OSError):
                self._drop_client(p.conn)

    def _load_questions(self, filename=None, num_questions=None):
        print(self.theme)
        if num_questions is None:
            num_questions = self.game_questions_count
        
        # Map theme to CSV filename
        if filename is None:
            theme_files = {
                "general": "questions/for questions.csv",
                "math": "questions/for math.csv",
                "cyber": "questions/for cybersec.csv",
                "nature": "questions/for nature.csv"
            }
            filename = theme_files.get(self.theme, "questions/for questions.csv")
        
        try:
            with open(filename, 'r', encoding='utf-8', newline='') as file:
                reader = csv.reader(file)
                all_questions = []
                for row in reader:
                    if len(row) != 6:
                        continue
                    all_questions.append([cell.strip() for cell in row])

            return random.sample(all_questions, min(len(all_questions), num_questions))
        except FileNotFoundError:
            # Fallback to default questions if theme file doesn't exist
            with open('questions/for questions.csv', 'r', encoding='utf-8', newline='') as file:
                reader = csv.reader(file)
                all_questions = []
                for row in reader:
                    if len(row) != 6:
                        continue
                    all_questions.append([cell.strip() for cell in row])

            return random.sample(all_questions, min(len(all_questions), num_questions))

    def show_leaderboard(self):
        """Display the global game leaderboard and close the server."""
        self.clear_client_screens()
        sorted_results = sorted(self.scores.items(), key=lambda item: item[1], reverse=True)
        leaderboard_msg = "\n--- FINAL LEADERBOARD ---\n"
        rankings = {}  # Group players by score
        for sock, score in sorted_results:
            name = self.names.get(sock, "Unknown")

            if score not in rankings:
                rankings[score] = []

            rankings[score].append(name)

        # Format leaderboard with ranking
        place = 1
        for score in sorted(rankings.keys(), reverse=True):
            players = ", ".join(rankings[score])
            leaderboard_msg += f"{place}. {players} with {score} points\n"
            place += len(rankings[score])

        self.broadcast(leaderboard_msg + "\nThanks for playing!")

        # Close all client connections
        for c in list(self.clients):
            try:
                c.conn.close()
            except:
                pass
        try:
            self.server_socket.close()
        except:
            pass

    def show_room_leaderboard(self, room):
        """Display the leaderboard for a specific room and clean up."""
        self.clear_room_screens(room)
        sorted_results = sorted(room.scores.items(), key=lambda item: item[1], reverse=True)
        leaderboard_msg = "\n--- FINAL LEADERBOARD ---\n"
        rankings = {}  # Group players by score
        for player, score in sorted_results:
            name = player.username

            if score not in rankings:
                rankings[score] = []

            rankings[score].append(name)

        # Format leaderboard with ranking
        place = 1
        for score in sorted(rankings.keys(), reverse=True):
            players = ", ".join(rankings[score])
            leaderboard_msg += f"{place}. {players} with {score} points\n"
            place += len(rankings[score])

        self.network_helper._broadcast_room(room, leaderboard_msg + "\nThanks for playing!\n")