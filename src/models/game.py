from collections import deque
from typing import Callable

from config.settings import (
    SECONDS_PER_PLAYER,
    SPEECH_LOWER_BOUND,
    SPEECH_UPPER_BOUND,
)

from src.role_info.roles import MAFIA_TEAM

from src.services.timer import TimerManager

from src.models.player import Player
from src.models.state import State


class Game:
    def __init__(self, chat_id: int, game_counter: int):
        self.chat_id = chat_id

        self.players = {}  # user_id -> Player
        self.players_by_number = {}

        self.state = State.LOBBY

        self.day_count = 0
        self.game_number = game_counter
        self.day_starter_num = 1

        self.nominated = []
        self.speech_queue = deque()
        self.defense_queue = deque()
        self.timer_manager = TimerManager()

        self.voting_queue = deque()
        self.current_votes = {}
        self.vote_history = {}

        self.balance_players = []
        self.revote_count = 0

        self.night_actions = {}

        self.expected_night_actors = {}

        self.current_preset = []

        self.mafia_team = MAFIA_TEAM

        self.simulation = False

    def add_player(self, user_id: int, name: str):
        if user_id in self.players:
            return False

        number = len(self.players) + 1
        p = Player(user_id, name, number)

        self.players[user_id] = p
        self.players_by_number[number] = p
        return True

    def filter_players(self, condition: Callable[[Player], bool]):
        return [player for player in self.players.values() if condition(player)]

    def build_daily_queue(self):
        alive = sorted(
            self.filter_players(lambda p: p.is_alive), key=lambda p: p.number
        )

        if not alive:
            return deque()

        queue = deque(alive)
        for i, p in enumerate(alive):
            if p.number >= self.day_starter_num:
                queue.rotate(-i)
                self.day_starter_num = p.number
                break

        return queue

    def fill_empty_slots(self):
        if len(self.players) > len(self.current_preset):
            self.current_preset += ["Мирный житель"] * (
                len(self.players) - len(self.current_preset)
            )

    def calculate_speech_time(self):
        alive_count = len(self.filter_players(lambda p: p.is_alive))
        raw_time = alive_count * SECONDS_PER_PLAYER
        return min(SPEECH_UPPER_BOUND, max(SPEECH_LOWER_BOUND, raw_time))
