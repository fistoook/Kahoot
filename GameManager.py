import socket
import random
import csv
import json

################## Game Logic ###################
class GameManager:
    def __init__(self):
        self.rooms = {}
    
    def run(self):
        print(f"Game Control Server started on {self.server_address}.")
        while True:
            try:
                data = self.main_server_socket.recv(1024)
                if not data:
                    print("Main server disconnected.")
                    break
                command = data.decode().strip()
                print(f"Received command from main server: {command}")
                self.parse_command(command)
            except (ConnectionError, OSError):
                print("Connection error with main server.")
                break
        self.shutdown()

    def parse_command(self, command):
        print(f"Parsing command: {command}")
        
        if command == "START":
            self.start_game()

    def start_game(self):
        print("Game started. Ready to send questions to main server.")
        self.questions = self._load_questions()
        

    def _load_questions(self, filename='for questions.csv'):
        with open(filename, 'r', encoding='utf-8', newline='') as file:
            reader = csv.reader(file)
            all_questions = []
            for row in reader:
                if len(row) != 6:
                    continue
                all_questions.append([cell.strip() for cell in row])

        return json.dumps(random.sample(all_questions,
        min(len(all_questions), self.game_questions_count)))