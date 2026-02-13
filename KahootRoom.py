import csv
import random
import time
import select
from ConsoleLogger import ConsoleLogger
from NetworkHelpers import NetworkHelpers
class Room:
    def __init__(self, room_id, host_client, network_helper=None):
        """Initialize room state, players, and a network helper."""
        # Core room metadata and tracking state.
        self.room_id = room_id
        self.host_client = host_client
        self.players = [host_client]
        self.questions = []
        self.current_question_index = -1
        self.scores = {host_client: 0}
        self.game_started = False
        # Network helper to broadcast prompts and results.
        self.network_helper = network_helper or NetworkHelpers()
        # Loader for CSV-based question banks.
        self.question_loader = QuestionCSVLoader()

    def run_room_game(self, num_questions=None, timeout=20, default_count=2):
        num_questions = self._prepare_questions(num_questions, default_count)

        for i, q_data in enumerate(self.questions):
            if not self.players:
                ConsoleLogger.warn("No players left in room. Ending game.")
                break

            self.network_helper.clear_room_screens(self)

            prompt, correct = self._build_question_prompt(i, q_data, num_questions, timeout)
            self.network_helper.broadcast_room(self, prompt)

            # Collect answers until timeout or all players respond.
            answers_this_round = self._collect_answers(timeout, correct)
            summary = self._build_round_summary(answers_this_round, correct)
            self._broadcast_round_summary(summary)

        # Final leaderboard at the end of the game.
        self.network_helper.show_room_leaderboard(self)

    def _prepare_questions(self, num_questions, default_count):
        """Load question list and return the effective question count."""
        if num_questions is None:
            num_questions = default_count
        self.questions = self.load_questions(
            num_questions=num_questions,
            theme=getattr(self, "theme", None),
            default_count=default_count,
        )
        return num_questions

    def _build_question_prompt(self, index, q_data, num_questions, timeout):
        """Build the question prompt and return (prompt, correct_answer)."""
        q_text, o1, o2, o3, o4, correct = q_data
        correct = str(correct).strip()

        prompt = (
            f"Question {index+1}/{num_questions}:\n"
            f"{q_text}\n"
            f"1) {o1}\n"
            f"2) {o2}\n"
            f"3) {o3}\n"
            f"4) {o4}\n\n"
            f"You have {timeout} seconds. Type 1-4 and press Enter:\n"
        )
        return prompt, correct

    def _collect_answers(self, timeout, correct_answer):
        """Collect answers for a question and return socket->answer map."""
        answered_this_round = set()
        answers_this_round = {}
        deadline = time.time() + timeout
        conn_to_player = {p.conn: p for p in self.players}

        while time.time() < deadline and len(answered_this_round) < len(self.players):
            remaining = deadline - time.time()
            wait_time = 1 if remaining > 1 else max(0, remaining)
            try:
                readable, _, _ = select.select(list(conn_to_player.keys()), [], [], wait_time)
            except OSError:
                continue

            for s in readable:
                if s in answered_this_round:
                    continue

                try:
                    data = s.recv(1024)
                except (ConnectionError, OSError):
                    self._drop_player_connection(s)
                    continue

                if not data:
                    self._drop_player_connection(s)
                    continue

                text = data.decode(errors="ignore").strip()

                answer = None
                if text == "1" or text == "2" or text == "3" or text == "4":
                    answer = text.strip()

                if answer is None:
                    self.network_helper.send_line(s, "Invalid answer. Type 1, 2, 3, or 4 and press Enter.")
                    continue

                answers_this_round[s] = answer
                player = conn_to_player.get(s)
                if player is not None and answer == correct_answer:
                    self.scores[player] = self.scores.get(player, 0) + 1
                    self.network_helper.send_line(s, "Correct!")
                else:
                    self.network_helper.send_line(s, "Wrong!")
                answered_this_round.add(s)

        return answers_this_round

    def _build_round_summary(self, answers_this_round, correct_answer):
        """Create a summary string for the current question results."""
        correct_players = 0
        wrong_players = 0
        no_answer_players = 0
        for p in list(self.players):
            if p.conn in answers_this_round:
                if answers_this_round[p.conn] == correct_answer:
                    correct_players += 1
                else:
                    wrong_players += 1
            else:
                no_answer_players += 1

        summary = f"\n Time! Correct answer was: {correct_answer}\n"
        if correct_players:
            summary += f" Correct: {correct_players} players\n"
        if wrong_players:
            summary += f" Wrong: {wrong_players} players\n"
        if no_answer_players:
            summary += f" No answer: {no_answer_players} players\n"

        return summary

    def _broadcast_round_summary(self, summary):
        """Broadcast summary and wait before the next question."""
        self.network_helper.broadcast_room(self, summary)
        self.network_helper.broadcast_room(self, "Moving to next question...\n")
        time.sleep(3.5)

    def _drop_player_connection(self, conn):
        """Remove a disconnected player and close the socket."""
        # Remove player and score entries tied to this connection.
        for player in list(self.players):
            if player.conn == conn:
                self.players.remove(player)
                self.scores.pop(player, None)
                break
        try:
            conn.close()
        except:
            pass

    def load_questions(self, filename=None, num_questions=None, theme=None, default_count=2):
        """Load question rows from CSV, optionally filtered by theme."""
        # Resolve requested count and CSV path.
        if num_questions is None:
            num_questions = default_count
        return self.question_loader.load_questions(
            filename=filename,
            num_questions=num_questions,
            theme=theme,
        )

class QuestionCSVLoader:
    def __init__(self, default_file="questions/for questions.csv"):
        """Initialize loader with a default CSV fallback path."""
        self.default_file = default_file

    def load_questions(self, filename=None, num_questions=2, theme=None):
        """Load question rows from CSV and return a random sample."""
        if filename is None:
            if theme is None:
                theme = "general"
            theme_files = {
                "general": "questions/for questions.csv",
                "math": "questions/for math.csv",
                "cyber": "questions/for cybersec.csv",
                "nature": "questions/for nature.csv"
            }
            filename = theme_files.get(theme, self.default_file)

        try:
            return self._read_questions(filename, num_questions)
        except FileNotFoundError:
            return self._read_questions(self.default_file, num_questions)

    def _read_questions(self, filename, num_questions):
        with open(filename, 'r', encoding='utf-8', newline='') as file:
            reader = csv.reader(file)
            all_questions = []
            for row in reader:
                if len(row) != 6:
                    continue
                all_questions.append([cell.strip() for cell in row])

        return random.sample(all_questions, min(len(all_questions), num_questions))

