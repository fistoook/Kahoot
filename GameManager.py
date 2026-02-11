import socket
import random
import csv
import json
from colorama import Fore, Style, init, Back
def _log_warn(message):
    """Log a warning message in yellow."""
    print(f"{Fore.YELLOW}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {message}")
################## Game Logic ###################
class GameManager:
    def __init__(self):
        self.rooms = {}
        

    

    def run_room_game(self, room):
        """Run the game loop for a specific room with independent scores."""
        questions = self.game_control._load_questions()
        if isinstance(questions, str):
            try:
                questions = json.loads(questions)
            except json.JSONDecodeError:
                questions = []

        for i, q_data in enumerate(questions):
            if not room.players:
                _log_warn("No players left in room. Ending game.")
                break

            self._clear_room_screens(room)

            # Parse question data
            q_text, o1, o2, o3, o4, correct = q_data
            correct = str(correct).strip()

            # Format and broadcast question to room
            prompt = (
                f"Question {i+1}/{self.game_questions_count}:\n"
                f"{q_text}\n"
                f"1) {o1}\n"
                f"2) {o2}\n"
                f"3) {o3}\n"
                f"4) {o4}\n\n"
                f"You have {self.timeout} seconds. Type 1-4 and press Enter:\n"
            )
            self._broadcast_room(room, prompt)

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

                    # Record answer and update room score if correct
                    answers_this_round[s] = answer
                    player = conn_to_player.get(s)
                    if player is not None and answer == correct:
                        room.scores[player] = room.scores.get(player, 0) + 1
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

            self._broadcast_room(room, summary)
            self._broadcast_room(room, "Moving to next question...\n")
            time.sleep(3.5)  # Pause before next question

        # Display room-specific leaderboard when game ends
        self.show_room_leaderboard(room)

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
        self._clear_room_screens(room)
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

        self._broadcast_room(room, leaderboard_msg + "\nThanks for playing!\n")