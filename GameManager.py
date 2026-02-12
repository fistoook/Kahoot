import socket
import random
import csv
import time
import select
from NetworkHelpers import NetworkHelpers
from ConsoleLogger import ConsoleLogger
################## Game Logic ###################
class GameManager:
    def __init__(self):
        self.rooms = {}
        self.game_questions_count = 2
        self.timeout = 20
        self.network_helper = NetworkHelpers()
        self.active_games = {}  # Maps room_id -> game_state dict

    def init_game(self, room, num_questions, theme="general"):
        """Initialize a game state machine for a room (non-blocking)."""
        questions = self._load_questions(num_questions=num_questions, theme=theme)
        
        game_state = {
            'room': room,
            'questions': questions,
            'current_q_index': 0,
            'question_start_time': None,
            'answered_players': set(),
            'answers': {},
            'show_results_until': None,
            'correct_answer': None,
        }
        
        self.active_games[room.room_id] = game_state
        ConsoleLogger.room_event(room.room_id, f"Initialized with {len(questions)} questions")
        return game_state

    def get_current_question(self, room_id):
        """Get the current question to display (returns formatted string)."""
        if room_id not in self.active_games:
            return None
        
        game_state = self.active_games[room_id]
        q_index = game_state['current_q_index']
        questions = game_state['questions']
        
        if q_index >= len(questions):
            return None
        
        q_data = questions[q_index]
        q_text, o1, o2, o3, o4, correct = q_data
        game_state['correct_answer'] = str(correct).strip()
        
        prompt = (
            f"Question {q_index + 1}/{len(questions)}:\n"
            f"{q_text}\n"
            f"1) {o1}\n"
            f"2) {o2}\n"
            f"3) {o3}\n"
            f"4) {o4}\n\n"
            f"You have {self.timeout} seconds. Type 1-4 and press Enter:\n"
        )
        return prompt

    def send_next_question(self, room_id):
        """Send the next question to all players in a room."""
        if room_id not in self.active_games:
            return
        
        game_state = self.active_games[room_id]
        room = game_state['room']
        
        # Clear screens
        self.clear_room_screens(room)
        
        prompt = self.get_current_question(room_id)
        if prompt is None:
            return False  # Game is over
        
        self.network_helper._broadcast_room(room, prompt)
        
        # Reset state for this question
        game_state['question_start_time'] = time.time()
        game_state['answered_players'] = set()
        game_state['answers'] = {}
        game_state['show_results_until'] = None
        
        ConsoleLogger.room_event(room_id, f"Question {game_state['current_q_index'] + 1} sent")
        return True

    def process_answer(self, room_id, player_conn, answer_text):
        """Process an answer from a player (non-blocking)."""
        if room_id not in self.active_games:
            return False
        
        game_state = self.active_games[room_id]
        
        # Check if already answered
        if player_conn in game_state['answered_players']:
            return False
        
        # Check if still accepting answers (not in results phase)
        if game_state['show_results_until'] is not None:
            return False
        
        # Validate answer
        answer = None
        if answer_text in ["1", "2", "3", "4"]:
            answer = answer_text.strip()
        
        if answer is None:
            return False
        
        # Record answer
        game_state['answers'][player_conn] = answer
        game_state['answered_players'].add(player_conn)
        
        # Update score if correct
        room = game_state['room']
        correct_answer = game_state['correct_answer']
        
        # Find player by socket
        for player in room.players:
            if player.conn == player_conn:
                if answer == correct_answer:
                    room.scores[player] = room.scores.get(player, 0) + 1
                    ConsoleLogger.room_event(room_id, f"{player.username} answered correctly")
                break
        
        return True

    def update_game(self, room_id):
        """Update game state - check timeouts and advance questions (non-blocking)."""
        if room_id not in self.active_games:
            return False  # Game doesn't exist
        
        game_state = self.active_games[room_id]
        room = game_state['room']
        
        # If showing results, check if time to move on
        if game_state['show_results_until'] is not None:
            if time.time() >= game_state['show_results_until']:
                # Move to next question
                game_state['current_q_index'] += 1
                if game_state['current_q_index'] >= len(game_state['questions']):
                    return False  # Game is over
                self.send_next_question(room_id)
            return True
        
        # Check if question timeout or all answered
        if game_state['question_start_time'] is not None:
            elapsed = time.time() - game_state['question_start_time']
            all_answered = len(game_state['answered_players']) >= len(room.players)
            
            if elapsed >= self.timeout or all_answered:
                # Show results
                self._show_question_results(room_id)
                return True
        
        return True

    def _show_question_results(self, room_id):
        """Show results for current question."""
        if room_id not in self.active_games:
            return
        
        game_state = self.active_games[room_id]
        room = game_state['room']
        correct_answer = game_state['correct_answer']
        answers = game_state['answers']
        
        # Tally results
        correct_count = 0
        wrong_count = 0
        no_answer_count = 0
        
        for player in room.players:
            if player.conn in answers:
                if answers[player.conn] == correct_answer:
                    correct_count += 1
                else:
                    wrong_count += 1
            else:
                no_answer_count += 1
        
        # Format summary
        summary = f"\nTime's up! Correct answer was: {correct_answer}\n"
        if correct_count:
            summary += f"✓ Correct: {correct_count} players\n"
        if wrong_count:
            summary += f"✗ Wrong: {wrong_count} players\n"
        if no_answer_count:
            summary += f"⏱ No answer: {no_answer_count} players\n"
        summary += "\nMoving to next question...\n"
        
        self.network_helper._broadcast_room(room, summary)
        
        # Schedule next question after 3.5 seconds
        game_state['show_results_until'] = time.time() + 3.5
        
        ConsoleLogger.room_event(room_id, "Results shown")

    def end_game(self, room_id):
        """End a game and show final leaderboard."""
        if room_id not in self.active_games:
            return
        
        game_state = self.active_games[room_id]
        room = game_state['room']
        
        # Clear screens
        self.clear_room_screens(room)
        
        # Show leaderboard
        sorted_results = sorted(room.scores.items(), key=lambda x: x[1], reverse=True)
        
        # Display styled leaderboard on server
        leaderboard_entries = [(i, player.username, score) for i, (player, score) in enumerate(sorted_results, 1)]
        ConsoleLogger.leaderboard("Final Scores", leaderboard_entries)
        
        # Send leaderboard to clients
        msg = "\n" + "="*50 + "\n"
        msg += " "*15 + "FINAL SCORES\n"
        msg += "="*50 + "\n"
        for i, (player, score) in enumerate(sorted_results, 1):
            msg += f"{i:2d}. {player.username:<20s} {score:>5d} pts\n"
        msg += "="*50 + "\nThanks for playing!\n"
        
        self.network_helper._broadcast_room(room, msg)
        
        # Clean up
        del self.active_games[room_id]
        
        ConsoleLogger.room_event(room_id, "Game ended")

    def run_room_game(self, room, num_questions=None):
        """DEPRECATED: Old blocking method. Use init_game + update_game instead."""
        self.theme = room.theme
        """Run the game loop for a specific room with independent scores."""
        if num_questions is None:
            num_questions = self.game_questions_count
        room.questions = self._load_questions(num_questions=num_questions)

        for i, q_data in enumerate(room.questions):
            if not room.players:
                ConsoleLogger.warn("No players left in room. Ending game.")
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

    def _load_questions(self, filename=None, num_questions=None, theme=None):
        if num_questions is None:
            num_questions = self.game_questions_count
        
        # Map theme to CSV filename
        if filename is None:
            if theme is None:
                theme = "general"
            theme_files = {
                "general": "questions/for questions.csv",
                "math": "questions/for math.csv",
                "cyber": "questions/for cybersec.csv",
                "nature": "questions/for nature.csv"
            }
            filename = theme_files.get(theme, "questions/for questions.csv")
        
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