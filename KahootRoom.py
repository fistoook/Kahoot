class Room:
    def __init__(self, room_id, host_client):
        self.room_id = room_id
        self.host_client = host_client
        self.players = [host_client]
        self.questions = []
        self.current_question_index = -1
        self.scores = {host_client: 0}
        self.game_started = False