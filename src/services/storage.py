from src.models.game import Game


class Storage:
    def __init__(self):
        self.games = {}
        self.game_counter = 0

    def get_game(self, chat_id):
        return self.games.get(chat_id)

    def create_game(self, chat_id):
        self.game_counter += 1
        game = Game(chat_id, self.game_counter)
        self.games[chat_id] = game
