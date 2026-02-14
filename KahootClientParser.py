from ConsoleLogger import ConsoleLogger
import time
import re
import os
import sys

LOBBY_PROMPT = "Type 'Host <game name>' to host, 'Join <room ID>' to join, or 'View Rooms' to see available rooms:"

if os.name == "nt":
    import msvcrt
else:
    import select


class KahootClientMessageParser:
    def __init__(self, client=None, input_func=input):
        """Initialize parser state and the input function used for prompts."""
        self.recv_buffer = ""
        self.name_sent = False
        self.input_func = input_func
        self.client = client

    def handle_data(self, data, send_line):
        """Parse incoming bytes and respond to prompts via send_line."""
        text = data.decode(errors="ignore")
        self.recv_buffer += text

        text = self.recv_buffer
        self.recv_buffer = ""
        lowered = text.lower()

        handled = self._handle_prompts(text, send_line)

        if not handled and "Question" in text:
            lines = text.split("\n")
            for line in lines:
                cleaned = self._clean_line(line)
                if cleaned:
                    ConsoleLogger.question(cleaned)
            return

        if not handled:
            print(text, end="", flush=True)

    def _handle_prompts(self, text, send_line):
        """Handle server prompts and return True when input was consumed."""
        raw_lines = text.split("\n")
        lowered_lines = [line.lower().strip() for line in raw_lines]
        accepted = False

        for i, lowered in enumerate(lowered_lines):
            lowered = lowered.strip()
            raw_line = self._clean_line(raw_lines[i]).strip()

            if "welcome to kahoot" in lowered:
                ConsoleLogger.Kahoot()
                continue

            if "successfully joined kahoot!" in lowered:
                ConsoleLogger.clear_console()
                ConsoleLogger.Welcome()
                ConsoleLogger.success(raw_line if raw_line else lowered)
                accepted = True
                time.sleep(2)
                ConsoleLogger.clear_console()
                ConsoleLogger.Menu()
                continue

            if "game" in lowered and "hosted" in lowered:
                ConsoleLogger.clear_console()
                match = re.search(r"room id:\s*(\d{4})", lowered)
                if match:
                    game_id = match.group(1)
                    ConsoleLogger.Game(game_id)
                else:
                    ConsoleLogger.Game("")
                ConsoleLogger.success(raw_line if raw_line else lowered)
                accepted = True
                continue

            if "joined" in lowered and "waiting to start..." in lowered:
                ConsoleLogger.clear_console()
                match = re.search(r"room #\s*(\d{4})", lowered)
                if match:
                    game_id = match.group(1)
                    ConsoleLogger.Game(game_id)
                else:
                    ConsoleLogger.Game("")
                ConsoleLogger.success(raw_line if raw_line else lowered)
                accepted = True
                continue

            if "joined" in lowered:
                for line in raw_lines:
                    cleaned = self._clean_line(line).strip()
                    if cleaned:
                        ConsoleLogger.info(cleaned)
                return True

            if not self.name_sent and "enter your username" in lowered:
                ConsoleLogger.prompt("Enter your username:")
                name = self.input_func().strip()
                if not name:
                    name = "Player"
                send_line(name)
                self.name_sent = True
                return True

            if ("join <room id>" in lowered or "host <game name>" in lowered) and "available rooms" in lowered:
                ConsoleLogger.prompt(raw_line if raw_line else lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "invalid command" in lowered or "invalid room id" in lowered or "game name cannot be empty" in lowered or "invalid host command" in lowered:
                ConsoleLogger.error(raw_line if raw_line else lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "type start" in lowered and "list" in lowered and "close" in lowered:
                ConsoleLogger.prompt(raw_line if raw_line else lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "how many questions would you like?" in lowered:
                ConsoleLogger.prompt(raw_line if raw_line else lowered)
                num_q = self.input_func().strip()
                if num_q.isdigit() and int(num_q) > 0:
                    send_line(num_q)
                    return True

            if "select a theme" in lowered and ("general" in lowered or "math" in lowered or "cyber" in lowered or "nature" in lowered):
                ConsoleLogger.prompt(raw_line if raw_line else lowered)
                theme = self.input_func().strip()
                if theme:
                    send_line(theme)
                return True

            if "invalid theme" in lowered:
                ConsoleLogger.error(raw_line if raw_line else lowered)
                theme = self.input_func().strip()
                if theme:
                    send_line(theme)
                return True

            if ("type 1-4" in lowered or "type 1, 2, 3, or 4" in lowered):
                ConsoleLogger.clear_console()

                timeout_seconds = self._extract_timeout_seconds(text)

                if self.client:
                    self.client.start_countdown(timeout_seconds)
                ConsoleLogger.countdown_timer(timeout_seconds)

                counter, question_text, options = self._extract_question_block(raw_lines)
                if counter:
                    ConsoleLogger.question_counter(counter)
                if question_text:
                    ConsoleLogger.question(question_text)

                if options:
                    print()
                for option_number, option_text in options:
                    ConsoleLogger.option(option_text, option_number)

                answer_prompt = "Type 1-4 and press Enter:"
                answer = self._prompt_for_answer_with_timeout(answer_prompt, timeout_seconds)

                if self.client:
                    self.client.displaying_countdown = False
                    self.client.countdown_end_time = None

                if answer:
                    send_line(answer)
                else:
                    ConsoleLogger.warn("Time is up. No answer submitted.")

                return True

            if "players:" in lowered:
                ConsoleLogger.info(raw_line if raw_line else lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "room closed" in lowered:
                ConsoleLogger.clear_console()
                ConsoleLogger.Menu()
                ConsoleLogger.info(raw_line if raw_line else lowered)
                ConsoleLogger.prompt(LOBBY_PROMPT)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "invalid answer" in lowered:
                ConsoleLogger.error(raw_line if raw_line else lowered)
                answer = self.input_func().strip()
                if answer:
                    send_line(answer)
                return True

            if "available rooms" in lowered:
                ConsoleLogger.clear_console()
                ConsoleLogger.Rooms()
                ConsoleLogger.info(raw_line if raw_line else lowered)

                for j, line in enumerate(raw_lines):
                    cleaned = self._clean_line(line).strip()
                    if cleaned and lowered_lines[j] != lowered:
                        ConsoleLogger.room(cleaned)

                print()
                ConsoleLogger.prompt(LOBBY_PROMPT)
                answer = self.input_func().strip()
                if answer:
                    send_line(answer)
                return True

        return accepted

    def _extract_timeout_seconds(self, text):
        """Extract the server-provided timeout in seconds from the question prompt."""
        match = re.search(r"you have\s+(\d+)\s+seconds?", text, flags=re.IGNORECASE)
        if not match:
            return 20

        try:
            parsed = int(match.group(1))
            return parsed if parsed > 0 else 20
        except ValueError:
            return 20

    def _prompt_for_answer_with_timeout(self, prompt_text, timeout_seconds):
        """Read answer input with timeout in interactive mode; fallback to injected input_func in tests."""
        ConsoleLogger.prompt(prompt_text)

        if timeout_seconds <= 0:
            return None

        if self.input_func is not input:
            answer = self.input_func().strip()
            return answer if answer else None

        if os.name == "nt":
            return self._timed_console_input_windows(timeout_seconds)

        return self._timed_console_input_posix(timeout_seconds)

    def _timed_console_input_windows(self, timeout_seconds):
        """Timed console input for Windows using msvcrt."""
        chars = []
        end_time = time.time() + timeout_seconds

        while time.time() < end_time:
            self._tick_countdown()

            if msvcrt.kbhit():
                ch = msvcrt.getwch()

                if ch in ("\r", "\n"):
                    print()
                    answer = "".join(chars).strip()
                    return answer if answer else None

                if ch == "\x03":
                    raise KeyboardInterrupt

                if ch in ("\b", "\x7f"):
                    if chars:
                        chars.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue

                if ch in ("\x00", "\xe0"):
                    if msvcrt.kbhit():
                        msvcrt.getwch()
                    continue

                chars.append(ch)
                sys.stdout.write(ch)
                sys.stdout.flush()
            else:
                time.sleep(0.05)

        if chars:
            print()
        return None

    def _timed_console_input_posix(self, timeout_seconds):
        """Timed console input for POSIX terminals using select."""
        end_time = time.time() + timeout_seconds
        chars = []

        while time.time() < end_time:
            self._tick_countdown()
            remaining = max(0.0, end_time - time.time())
            wait = min(0.05, remaining)

            ready, _, _ = select.select([sys.stdin], [], [], wait)
            if not ready:
                continue

            ch = sys.stdin.read(1)
            if ch in ("\n", "\r"):
                answer = "".join(chars).strip()
                return answer if answer else None

            chars.append(ch)

        return None

    def _tick_countdown(self):
        """Advance visual countdown while waiting for timed input."""
        if self.client and self.client.displaying_countdown:
            self.client._update_countdown_display()

    def _extract_question_block(self, raw_lines):
        """Extract question counter/text/options from a mixed payload safely."""
        cleaned_lines = [self._clean_line(line).strip() for line in raw_lines]
        cleaned_lines = [line for line in cleaned_lines if line]

        counter = ""
        question_text = ""
        options = []

        for idx, line in enumerate(cleaned_lines):
            if re.match(r"^question\s+\d+/\d+:", line, flags=re.IGNORECASE):
                counter = line
                if idx + 1 < len(cleaned_lines):
                    question_text = cleaned_lines[idx + 1]
                break

        for line in cleaned_lines:
            match = re.match(r"^([1-4])\)\s*(.+)$", line)
            if not match:
                continue

            option_number = int(match.group(1))
            option_text = match.group(2).strip()
            options.append((option_number, option_text))
            if len(options) == 4:
                break

        return counter, question_text, options

    def _clean_line(self, line):
        """Remove ANSI escape sequences and common control characters."""
        cleaned = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", line)
        return cleaned.replace("\r", "")
