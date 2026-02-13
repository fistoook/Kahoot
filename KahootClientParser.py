from ConsoleLogger import ConsoleLogger

class KahootClientMessageParser:
    def __init__(self, client=None, input_func=input):
        """Initialize parser state and the input function used for prompts."""
        # Buffer for partial server messages and prompt state.
        self.recv_buffer = ""
        self.name_sent = False
        self.input_func = input_func
        self.client = client  # Reference to client for countdown control

    def handle_data(self, data, send_line):
        """Parse incoming bytes and respond to prompts via send_line."""
        # Decode bytes and append to buffer in case of partial messages.
        text = data.decode(errors="ignore")
        self.recv_buffer += text

        text = self.recv_buffer
        self.recv_buffer = ""
        lowered = text.lower()

        # handling for the initial welcome message, banner print.
        if "enter your username" in lowered and "welcome to kahoot" in lowered:
            prompt_index = lowered.find("enter your username")
            banner = text[:prompt_index].rstrip()
            if banner:
                print(banner, end="\n", flush=True)

        handled = self._handle_prompts(text, send_line)

        if not handled and "Question" in text:
            # Print formatted question block when present.
            lines = text.split("\n")
            for line in lines:
                if line.strip():
                    from ConsoleLogger import ConsoleLogger
                    ConsoleLogger.question(line.strip())
            return

        if not handled:
            # Default to raw output when no prompt was handled.
            print(text, end="", flush=True)

    def _handle_prompts(self, text, send_line):
        """Handle server prompts and return True when input was consumed."""
        # Iterate line-by-line to match prompts and collect responses.
        lines = text.lower().split("\n")
        accepted = False
        for i, lowered in enumerate(lines):
            lowered = lowered.strip()
            
            # DISPLAY-ONLY messages (don't return, continue processing)
            if "successfully joined our server!" in lowered:
                ConsoleLogger.success(lowered)
                accepted = True
                continue

            if "game" in lowered and "hosted" in lowered:
                ConsoleLogger.success(lowered)
                accepted = True
                continue
            
            if "joined" in lowered:
                for line in lines:
                    if line.strip():
                        ConsoleLogger.info(line.strip())
                return True

            # PROMPTS that require input (return after handling)
            if not self.name_sent and "enter your username" in lowered:
                ConsoleLogger.prompt("Enter your username:")
                name = self.input_func().strip()
                if not name:
                    name = "Player"
                send_line(name)
                self.name_sent = True
                return True

            # Lobby prompt: Match only when full prompt is present
            if ("join <room id>" in lowered or "host <game name>" in lowered) and "available rooms" in lowered:
                ConsoleLogger.prompt(lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "invalid command" in lowered or "invalid room id" in lowered or "game name cannot be empty" in lowered or "invalid host command" in lowered:
                ConsoleLogger.error(lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "type start" in lowered and "list" in lowered and "close" in lowered:
                ConsoleLogger.prompt(lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "how many questions would you like?" in lowered:
                ConsoleLogger.prompt(lowered)
                num_q = self.input_func().strip()
                if num_q.isdigit() and int(num_q) > 0:
                    send_line(num_q)
                    return True

            if "select a theme" in lowered and ("general" in lowered or "math" in lowered or "cyber" in lowered or "nature" in lowered):
                ConsoleLogger.prompt(lowered)
                theme = self.input_func().strip()
                if theme:
                    send_line(theme)
                return True

            if "invalid theme" in lowered:
                ConsoleLogger.error(lowered)
                theme = self.input_func().strip()
                if theme:
                    send_line(theme)
                return True

            # Question prompt: Only match if full prompt is present (includes answer options)
            if ("type 1-4" in lowered or "type 1, 2, 3, or 4" in lowered) and len(lines) >= 6:
                # Clear screen and display countdown at top
                print("\x1b[H\x1b[2J", end="", flush=True)  # Clear screen
                
                # Start countdown timer (20 seconds)
                if self.client:
                    self.client.start_countdown(20)
                    ConsoleLogger.countdown_timer(20)  # Initial display
                else:
                    ConsoleLogger.countdown_timer(20)
                
                # Display question content below countdown
                print()  # Blank line for spacing
                ConsoleLogger.question_counter(lines[0].strip())
                ConsoleLogger.question(lines[1].strip())
                for j in range(2, 6):
                    ConsoleLogger.option(lines[j].strip(), j-1)
                ConsoleLogger.prompt(lowered)
                
                # Get answer from user
                answer = self.input_func().strip()
                
                # Stop countdown when answer is submitted
                if self.client:
                    self.client.displaying_countdown = False
                    self.client.countdown_end_time = None
                
                if answer:
                    send_line(answer)
                return True

            if "players:" in lowered:
                ConsoleLogger.info(lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "room closed" in lowered:
                ConsoleLogger.info(lowered)
                command = self.input_func().strip()
                if command:
                    send_line(command)
                return True

            if "Invalid answer" in lowered:
                ConsoleLogger.error(lowered)
                answer = self.input_func().strip()
                if answer:
                    send_line(answer)
                return True

            if "available rooms" in lowered:
                ConsoleLogger.info(lowered)
                lines_copy = lines.copy()
                try:
                    lines_copy.remove(lowered)
                except ValueError:
                    pass
                for line in lines_copy:
                    if line.strip():
                        ConsoleLogger.room(line.strip())
                ConsoleLogger.prompt("Type 'Host <game name>' to host, 'Join <room ID>' to join, or 'View Rooms' to see available rooms:")
                answer = self.input_func().strip()
                if answer:
                    send_line(answer)
                return True
        
        return accepted