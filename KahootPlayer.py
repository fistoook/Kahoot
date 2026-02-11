class Player:
    def __init__(self, conn, username):
        self.conn = conn
        self.username = username
        self.score = 0