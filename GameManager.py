import time
from NetworkHelpers import NetworkHelpers
from ConsoleLogger import ConsoleLogger
class GameManager:
    def __init__(self):
        # Tracks rooms and active game state across the server.
        self.rooms = {}
        self.game_questions_count = 2
        self.timeout = 20
        self.network_helper = NetworkHelpers()
        self.active_games = {}  # Maps room_id -> game_state dict

    def init_game(self, room, num_questions, theme="general"):
        """Initialize a game state machine for a room (non-blocking)."""
        # Build a new game_state entry for the room.
        questions = room.load_questions(num_questions=num_questions, theme=theme, default_count=self.game_questions_count)
        
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
        # Return None when the room is missing or out of questions.
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
        # Push the next question to every player and reset round state.
        if room_id not in self.active_games:
            return
        
        game_state = self.active_games[room_id]
        room = game_state['room']
        
        # Clear screens
        self.network_helper.clear_room_screens(room)
        
        prompt = self.get_current_question(room_id)
        if prompt is None:
            return False  # Game is over
        
        self.network_helper.broadcast_room(room, prompt)
        
        # Reset state for this question
        game_state['question_start_time'] = time.time()
        game_state['answered_players'] = set()
        game_state['answers'] = {}
        game_state['show_results_until'] = None
        
        ConsoleLogger.room_event(room_id, f"Question {game_state['current_q_index'] + 1} sent")
        return True

    def process_answer(self, room_id, player_conn, answer_text):
        """Process an answer from a player (non-blocking)."""
        # Validate and record a single player's answer.
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
        # Advance question state based on timeouts and responses.
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
        # Tally and broadcast results for the current question.
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
        
        self.network_helper.broadcast_room(room, summary)
        
        # Schedule next question after 3.5 seconds
        game_state['show_results_until'] = time.time() + 3.5
        
        ConsoleLogger.room_event(room_id, "Results shown")

    def end_game(self, room_id):
        """End a game and show final leaderboard."""
        # Send final scores, then remove the game from active state.
        if room_id not in self.active_games:
            return
        
        game_state = self.active_games[room_id]
        room = game_state['room']
        
        # Clear screens
        self.network_helper.clear_room_screens(room)
        
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
        
        self.network_helper.broadcast_room(room, msg)
        
        # Clean up
        del self.active_games[room_id]
        
        ConsoleLogger.room_event(room_id, "Game ended")

    def update_active_games(self):
        """Update all active games and return rooms that finished."""
        # Iterate through all active games and collect finished rooms.
        finished_rooms = []
        for room_id in list(self.active_games.keys()):
            game_state = self.active_games.get(room_id)
            if not game_state:
                continue

            is_running = self.update_game(room_id)
            if not is_running:
                self.end_game(room_id)
                finished_rooms.append(game_state['room'])

        return finished_rooms