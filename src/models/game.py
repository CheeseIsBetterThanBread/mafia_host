from collections import deque
from typing import Callable, Deque

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
        self.chat_id: int = chat_id

        self.players: dict[int, Player] = {}  # user_id -> Player
        self.players_by_number: dict[int, Player] = {}

        self.state: State = State.LOBBY

        self.day_count: int = 0
        self.game_number: int = game_counter
        self.day_starter_num: int = 1

        self.order_queue: Deque[Player] = deque()
        self.timer_manager: TimerManager = TimerManager()

        self.nominated: list[int] = []

        self.current_votes: dict[str | int, int] = {}  # choice -> votes for this choice
        self.vote_history = {}  # player -> choice

        self.balance_players: list[int] = []
        self.vote_count: int = 0  # no more than 2 are allowed per day

        self.night_actions = {}
        self.expected_night_actors = {}

        self.current_preset: list[str] = []

        self.mafia_team: list[str] = MAFIA_TEAM

        self.simulation: bool = False

    def add_player(self, user_id: int, name: str):
        if user_id in self.players:
            return False

        number = len(self.players) + 1
        p = Player(user_id, name, number)

        self.players[user_id] = p
        self.players_by_number[number] = p
        return True

    def filter_players(self, condition: Callable[[Player], bool]) -> list[Player]:
        return [player for player in self.players.values() if condition(player)]

    def build_daily_queue(self):
        alive = sorted(
            self.filter_players(lambda p: p.is_alive), key=lambda p: p.number
        )
        assert alive

        queue = deque(alive)
        for i, p in enumerate(alive):
            if p.number >= self.day_starter_num:
                queue.rotate(-i)
                self.day_starter_num = p.number
                break

        self.order_queue = queue

    def build_defense_queue(self):
        self.order_queue = deque([self.players_by_number[n] for n in self.nominated])
        assert self.order_queue

    def fill_empty_slots(self):
        if len(self.players) > len(self.current_preset):
            self.current_preset += ["Мирный житель"] * (
                len(self.players) - len(self.current_preset)
            )

    def pop_speaker(self) -> Player:
        return self.order_queue.popleft()

    def calculate_speech_time(self) -> int:
        alive_count = len(self.filter_players(lambda p: p.is_alive))
        raw_time = alive_count * SECONDS_PER_PLAYER
        return min(SPEECH_UPPER_BOUND, max(SPEECH_LOWER_BOUND, raw_time))
