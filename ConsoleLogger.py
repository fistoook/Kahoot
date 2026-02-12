"""
Centralized styled console logging for the Kahoot application.
Provides consistent, colored logging throughout all modules.
"""

from colorama import Fore, Style, init

init(autoreset=True)


class ConsoleLogger:
    """Centralized logger with styled console output."""

    @staticmethod
    def info(message):
        """Log an information message in cyan."""
        print(f"{Fore.CYAN}{Style.BRIGHT}[INFO]{Style.RESET_ALL} {message}")

    @staticmethod
    def warn(message):
        """Log a warning message in yellow."""
        print(f"{Fore.YELLOW}{Style.BRIGHT}[WARN]{Style.RESET_ALL} {message}")

    @staticmethod
    def error(message):
        """Log an error message in red."""
        print(f"{Fore.RED}{Style.BRIGHT}[ERROR]{Style.RESET_ALL} {message}")

    @staticmethod
    def success(message):
        """Log a success message in bold green."""
        print(f"{Fore.GREEN}{Style.BRIGHT}[SUCCESS]{Style.RESET_ALL} {message}")

    @staticmethod
    def connected(message):
        """Log successful connection in bold green."""
        print(f"{Fore.GREEN}{Style.BRIGHT}[CONNECTED]{Style.RESET_ALL} {message}")

    @staticmethod
    def disconnected(message):
        """Log disconnection in bold red."""
        print(f"{Fore.RED}{Style.BRIGHT}[DISCONNECTED]{Style.RESET_ALL} {message}")

    @staticmethod
    def prompt(message):
        """Log a prompt message with magenta highlight."""
        print(f"{Fore.MAGENTA}{Style.BRIGHT}[PROMPT]{Style.RESET_ALL} {message}", end=" ", flush=True)

    @staticmethod
    def debug(message):
        """Log a debug message in gray."""
        print(f"{Fore.LIGHTBLACK_EX}{Style.BRIGHT}[DEBUG]{Style.RESET_ALL} {message}")

    @staticmethod
    def game_event(message):
        """Log a game event in bright white."""
        print(f"{Fore.WHITE}{Style.BRIGHT}[GAME]{Style.RESET_ALL} {message}")

    @staticmethod
    def server_event(message):
        """Log a server event in bright white."""
        print(f"{Fore.WHITE}{Style.BRIGHT}[SERVER]{Style.RESET_ALL} {message}")

    @staticmethod
    def player_action(player_name, action):
        """Log a player action with player name."""
        print(f"{Fore.LIGHTGREEN_EX}{Style.BRIGHT}[PLAYER]{Style.RESET_ALL} {player_name}: {action}")

    @staticmethod
    def room_event(room_id, message):
        """Log a room-specific event."""
        print(f"{Fore.LIGHTBLUE_EX}{Style.BRIGHT}[ROOM {room_id}]{Style.RESET_ALL} {message}")

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
        print(f"{Fore.YELLOW}{Style.BRIGHT}[ONGOING]{Style.RESET_ALL} {message}", end=" ", flush=True)


    @staticmethod
    def welcome():
        """Display a big bold purple welcome message."""
        welcome_text = f"""
{Fore.MAGENTA}{Style.BRIGHT}
╔══════════════════════════════════════╗
║     WELCOME TO KAHOOT!               ║
║                                      ║
║   Get ready for an epic quiz!        ║
╚══════════════════════════════════════╝
{Style.RESET_ALL}
        """
        print(welcome_text)
    @staticmethod
    def question(question_text):
        """Display a question with blue [QUESTION] prefix."""
        print(f"{Fore.BLUE}{Style.BRIGHT}[QUESTION]{Style.RESET_ALL} {question_text}")

    @staticmethod
    def leaderboard(title, entries):
        """Display a styled leaderboard with title and ranked entries.
        
        Args:
            title: Title of the leaderboard (e.g., "FINAL SCORES")
            entries: List of tuples (place_number, player_name, score)
        """
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