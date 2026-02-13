import sys
from colorama import Fore, Style, init

init(autoreset=True)

class ConsoleLogger:
    """Centralized logger with styled console output."""

    _status_initialized = False
    _last_counts = (-1, -1)
    _server_console_enabled = False
    _server_addr = ""
    _message_row = 7
    _player_row = 7
    _room_row = 7
    _col_width = 44
    _last_header_counts = (-1, -1, -1)
    _max_rows = 28

    @staticmethod
    def info(message):
        """Log an information message in cyan."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.CYAN}{Style.BRIGHT}[INFO]{Style.RESET_ALL} {message}")

    @staticmethod
    def warn(message):
        """Log a warning message in yellow."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.YELLOW}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {message}")

    @staticmethod
    def error(message):
        """Log an error message in red."""
        if ConsoleLogger._server_console_enabled:
            ConsoleLogger._write_table_row(f"ERROR: {message}", "")
            return
        print(f"{Fore.RED}{Style.BRIGHT}[ERROR]{Style.RESET_ALL} {message}")

    @staticmethod
    def success(message):
        """Log a success message in bold green."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.GREEN}{Style.BRIGHT}[SUCCESS]{Style.RESET_ALL} {message}")

    @staticmethod
    def connected(message):
        """Log successful connection in bold green."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.GREEN}{Style.BRIGHT}[CONNECTED]{Style.RESET_ALL} {message}")

    @staticmethod
    def disconnected(message):
        """Log disconnection in bold red."""
        if ConsoleLogger._server_console_enabled:
            ConsoleLogger._write_table_row(f"Disconnected: {message}", "")
            return
        print(f"{Fore.RED}{Style.BRIGHT}[DISCONNECTED]{Style.RESET_ALL} {message}")

    @staticmethod
    def prompt(message):
        """Log a prompt message with magenta highlight."""
        print(f"{Fore.MAGENTA}{Style.BRIGHT}[PROMPT]{Style.RESET_ALL} {message}", end=" ", flush=True)

    @staticmethod
    def debug(message):
        """Log a debug message in gray."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.LIGHTBLACK_EX}{Style.BRIGHT}[DEBUG]{Style.RESET_ALL} {message}")

    @staticmethod
    def game_event(message):
        """Log a game event in bright white."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.WHITE}{Style.BRIGHT}[GAME]{Style.RESET_ALL} {message}")

    @staticmethod
    def room(message):
        """Log a room event in bright blue."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}[ROOM]{Style.RESET_ALL} {message}")

    @staticmethod
    def server_event(message):
        """Log a server event in bright white."""
        if ConsoleLogger._server_console_enabled:
            ConsoleLogger._write_table_row(message, "")
            return
        print(f"{Fore.WHITE}{Style.BRIGHT}[SERVER]{Style.RESET_ALL} {message}")

    @staticmethod
    def player_action(player_name, action):
        """Log a player action with player name."""
        message = f"{player_name}: {action}"
        if ConsoleLogger._server_console_enabled:
            ConsoleLogger._write_table_row(message, "")
            return
        print(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}[PLAYER]{Style.RESET_ALL} {message}")

    @staticmethod
    def room_event(room_id, message):
        """Log a room-specific event."""
        entry = f"Room {room_id}: {message}"
        if ConsoleLogger._server_console_enabled:
            ConsoleLogger._write_table_row("", entry)
            return
        print(f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}[ROOM {room_id}]{Style.RESET_ALL} {message}")

    @staticmethod
    def joined():
        """Log a player joining."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.GREEN}{Style.BRIGHT}[JOINED]{Style.RESET_ALL}")

    @staticmethod
    def separator(char="=", length=60):
        """Print a separator line."""
        print(f"{Fore.LIGHTBLACK_EX}{char * length}{Style.RESET_ALL}")

    @staticmethod
    def title(text):
        """Print a styled title."""
        print(f"\n{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{text.upper()}{Style.RESET_ALL}\n")

    @staticmethod
    def ongoing(message):
        """Log an ongoing process message."""
        if ConsoleLogger._server_console_enabled:
            return
        print(f"{Fore.YELLOW}{Style.BRIGHT}[ONGOING]{Style.RESET_ALL} {message}", end=" ", flush=True)


    @staticmethod
    def welcome():
        """Display a big bold purple welcome message."""
        if ConsoleLogger._server_console_enabled:
            return
        welcome_text = f"""
{Fore.MAGENTA}{Style.BRIGHT}
========================================
|     WELCOME TO KAHOOT!              |
|                                      |
|   Get ready for an epic quiz!        |
========================================
{Style.RESET_ALL}
        """
        print(welcome_text)
    @staticmethod
    def question(question_text):
        """Display a question with blue [QUESTION] prefix."""
        print(f"{Fore.BLUE}{Style.BRIGHT}[QUESTION]{Style.RESET_ALL} {question_text}")

    @staticmethod
    def option(option_text, option_number):
        """Display a question option with green [OPTION N] prefix."""
        print(f"{Fore.GREEN}{Style.BRIGHT}[OPTION {option_number}]{Style.RESET_ALL} {option_text}")

    @staticmethod
    def question_counter(counter):
        """Display a question counter in cyan."""
        print(f"{Fore.CYAN}{Style.BRIGHT}[Count {counter}]{Style.RESET_ALL}")
    
    @staticmethod
    def countdown_timer(seconds_remaining):
        """Display a countdown timer at the current cursor position (for initial display)."""
        if seconds_remaining > 0:
            print(f"{Fore.YELLOW}{Style.BRIGHT}⏱  TIME REMAINING: {seconds_remaining:2d} seconds{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}{Style.BRIGHT}⏱  TIME'S UP!{Style.RESET_ALL}")
    
    @staticmethod
    def update_countdown_timer(seconds_remaining):
        """Update countdown timer in place using ANSI escape codes."""
        # Save cursor, move to line 1, clear line, print timer, restore cursor
        if seconds_remaining > 0:
            timer_text = f"{Fore.YELLOW}{Style.BRIGHT}⏱  TIME REMAINING: {seconds_remaining:2d} seconds{Style.RESET_ALL}"
        else:
            timer_text = f"{Fore.RED}{Style.BRIGHT}⏱  TIME'S UP!{Style.RESET_ALL}                    "
        
        # ANSI: Save cursor (\x1b[s), move to line 1 (\x1b[1;1H), clear line (\x1b[2K), print, restore cursor (\x1b[u)
        print(f"\x1b[s\x1b[1;1H\x1b[2K{timer_text}\x1b[u", end="", flush=True)
    
    @staticmethod
    def rooms_panel(room_lines):
        """Display a styled rooms panel in the client console (ASCII-safe)."""
        # Create border with ASCII characters for Windows console compatibility
        top_border = f"{Fore.CYAN}{Style.BRIGHT}+{'-'*70}+{Style.RESET_ALL}"
        mid_border = f"{Fore.CYAN}+{'-'*70}+{Style.RESET_ALL}"
        bottom_border = f"{Fore.CYAN}+{'-'*70}+{Style.RESET_ALL}"
        
        print("\n" + top_border)
        title = f"{Fore.CYAN}{Style.BRIGHT}|{'AVAILABLE ROOMS':^70}|{Style.RESET_ALL}"
        print(title)
        print(mid_border)
        
        if not room_lines:
            empty_msg = f"{Fore.LIGHTBLACK_EX}No rooms available - Host a game to get started!{Style.RESET_ALL}"
            print(f"{Fore.CYAN}|{Style.RESET_ALL} {empty_msg:68} {Fore.CYAN}|{Style.RESET_ALL}")
        else:
            for i, line in enumerate(room_lines, 1):
                # Add numbering and styling
                styled_line = f"{Fore.YELLOW}{i}.{Style.RESET_ALL} {Fore.WHITE}{line}{Style.RESET_ALL}"
                # Pad to fit in box (accounting for ANSI codes)
                padding = 68 - len(line) - 3  # 3 for "N. "
                print(f"{Fore.CYAN}|{Style.RESET_ALL} {styled_line}{' ' * padding} {Fore.CYAN}|{Style.RESET_ALL}")
        
        print(bottom_border + "\n")


    @staticmethod
    def leaderboard(title, entries):
        """Display a styled leaderboard with title and ranked entries.
        
        Args:
            title: Title of the leaderboard (e.g., "FINAL SCORES")
            entries: List of tuples (place_number, player_name, score)
        """
        if ConsoleLogger._server_console_enabled:
            ConsoleLogger._write_table_row("", f"{title} posted ({len(entries)} players)")
            return
        border = f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}"
        title_text = f"{Fore.CYAN}{Style.BRIGHT}{title.upper():^50}{Style.RESET_ALL}"
        
        print(f"\n{border}")
        print(title_text)
        print(border)
        
        for place, player, score in entries:
            # Create medal emoji based on placement
            if place == 1:
                medal = "🥇"
            elif place == 2:
                medal = "🥈"
            elif place == 3:
                medal = "🥉"
            else:
                medal = "  "
            
            # Color code by placement
            if place == 1:
                color = Fore.YELLOW + Style.BRIGHT
            elif place == 2:
                color = Fore.WHITE + Style.BRIGHT
            elif place == 3:
                color = Fore.LIGHTBLACK_EX + Style.BRIGHT
            else:
                color = Fore.WHITE
            
            line = f"{medal} {color}{place:2d}. {player:<20s} {score:>5d} pts{Style.RESET_ALL}"
            print(line)
        
        print(border + "\n")

    @staticmethod
    def init_status_bar():
        """Initialize the status bar at the top of the console."""
        if ConsoleLogger._status_initialized:
            return

        ConsoleLogger._status_initialized = True
        sys.stdout.write("\033[2J\033[H")
        ConsoleLogger._last_counts = (-1, -1)
        ConsoleLogger._render_status_bar(0, 0, force=True)

    @staticmethod
    def update_status_bar(players_count, rooms_count):
        """Refresh the status bar when counts change."""
        ConsoleLogger._render_status_bar(players_count, rooms_count, force=False)

    @staticmethod
    def _render_status_bar(players_count, rooms_count, force=False):
        """Render the status bar using ANSI cursor save/restore."""
        if not force and (players_count, rooms_count) == ConsoleLogger._last_counts:
            return

        ConsoleLogger._last_counts = (players_count, rooms_count)
        status_line = (
            f"\033[1;36m[PLAYERS]\033[0m {players_count:<3}   "
            f"\033[1;35m[ROOMS]\033[0m {rooms_count:<3}"
        )
        separator = "\033[90m" + "-" * 40 + "\033[0m"

        sys.stdout.write("\033[s\033[H")
        sys.stdout.write("\033[2K")
        sys.stdout.write(status_line + "\n")
        sys.stdout.write("\033[2K")
        sys.stdout.write(separator + "\n")
        sys.stdout.write("\033[u")
        sys.stdout.flush()

    @staticmethod
    def init_server_console(server_address):
        """Initialize the server console layout and header."""
        if ConsoleLogger._server_console_enabled:
            return

        ConsoleLogger._server_console_enabled = True
        ConsoleLogger._server_addr = f"{server_address[0]}:{server_address[1]}"
        ConsoleLogger._message_row = 7
        ConsoleLogger._player_row = 7
        ConsoleLogger._room_row = 7
        ConsoleLogger._last_header_counts = (-1, -1, -1)
        sys.stdout.write("\033[2J\033[H")
        ConsoleLogger._render_server_header(0, 0, 0)
        sys.stdout.flush()

    @staticmethod
    def update_server_header(players_count, connections_count, rooms_count):
        """Update the server header with current counts."""
        if not ConsoleLogger._server_console_enabled:
            return

        if (players_count, connections_count, rooms_count) == ConsoleLogger._last_header_counts:
            return

        ConsoleLogger._render_server_header(players_count, connections_count, rooms_count)

    @staticmethod
    def _render_server_header(players_count, connections_count, rooms_count):
        """Render the fixed server header and table titles."""
        ConsoleLogger._last_header_counts = (players_count, connections_count, rooms_count)
        title = f"LISTENING ON {ConsoleLogger._server_addr}"
        counts = (
            f"{Fore.CYAN}{Style.BRIGHT}PLAYERS{Style.RESET_ALL}: {players_count:<3}  "
            f"{Fore.MAGENTA}{Style.BRIGHT}CONNECTIONS{Style.RESET_ALL}: {connections_count:<3}  "
            f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}ROOMS{Style.RESET_ALL}: {rooms_count:<3}"
        )
        bar = "=" * (ConsoleLogger._col_width * 2 + 3)
        divider = "-" * (ConsoleLogger._col_width * 2 + 3)
        left_header = f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}{'PLAYER ACTIONS':^{ConsoleLogger._col_width}}{Style.RESET_ALL}"
        right_header = f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}{'ROOM ACTIONS':^{ConsoleLogger._col_width}}{Style.RESET_ALL}"

        sys.stdout.write("\033[s\033[H")
        sys.stdout.write("\033[2K")
        sys.stdout.write(f"{Fore.YELLOW}{Style.BRIGHT}{title}{Style.RESET_ALL}\n")
        sys.stdout.write("\033[2K")
        sys.stdout.write(bar + "\n")
        sys.stdout.write("\033[2K")
        sys.stdout.write(counts + "\n")
        sys.stdout.write("\033[2K")
        sys.stdout.write(divider + "\n")
        sys.stdout.write("\033[2K")
        sys.stdout.write(f"{left_header}|{right_header}\n")
        sys.stdout.write("\033[2K")
        sys.stdout.write(divider + "\n")
        sys.stdout.write("\033[u")

    @staticmethod
    def _write_table_row(left_text, right_text):
        """Write a single row to the server message table."""
        if not ConsoleLogger._server_console_enabled:
            return

        if ConsoleLogger._player_row > ConsoleLogger._max_rows or ConsoleLogger._room_row > ConsoleLogger._max_rows:
            sys.stdout.write("\033[2J\033[H")
            ConsoleLogger._message_row = 7
            ConsoleLogger._player_row = 7
            ConsoleLogger._room_row = 7
            counts = ConsoleLogger._last_header_counts
            if counts == (-1, -1, -1):
                counts = (0, 0, 0)
            ConsoleLogger._render_server_header(*counts)

        if left_text:
            left = left_text[:ConsoleLogger._col_width].ljust(ConsoleLogger._col_width)
            sys.stdout.write("\033[s")
            sys.stdout.write(f"\033[{ConsoleLogger._player_row};1H")
            sys.stdout.write(left)
            sys.stdout.write(f"\033[{ConsoleLogger._player_row};{ConsoleLogger._col_width + 1}H|")
            sys.stdout.write("\033[u")
            sys.stdout.flush()
            ConsoleLogger._player_row += 1

        if right_text:
            right = right_text[:ConsoleLogger._col_width].ljust(ConsoleLogger._col_width)
            sys.stdout.write("\033[s")
            sys.stdout.write(f"\033[{ConsoleLogger._room_row};{ConsoleLogger._col_width + 2}H")
            sys.stdout.write(right)
            sys.stdout.write(f"\033[{ConsoleLogger._room_row};{ConsoleLogger._col_width + 1}H|")
            sys.stdout.write("\033[u")
            sys.stdout.flush()
            ConsoleLogger._room_row += 1