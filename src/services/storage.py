from typing import Optional

from src.models import Game


class Storage:
    def __init__(self):
        self.games = {}
        self.game_counter = 0

    def get_game(self, chat_id) -> Optional[Game]:
        return self.games.get(chat_id)

    def create_game(self, chat_id):
        self.game_counter += 1
        self.games[chat_id] = Game(chat_id, self.game_counter)


STORAGE = Storage()
