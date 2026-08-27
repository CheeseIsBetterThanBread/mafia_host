from collections import Counter
import random

from config.settings import (
    PLAIN_ASSIGNMENT,
    BALANCE_ASSIGNMENT,
    SIMULATION_ASSIGNMENT,
    CURRENT_ASSIGNMENT,
    BALANCE_CUT_OFF,
    PROBABILITY_THRESHOLD,
    ENVIRONMENT,
    EnvironmentType,
)

from src.role_info.presets import ROOM_PRESETS, SPECIAL_PRESETS

from src.models import Balance, Game

from src.services.database import DATABASE
from src.services.confirmation import confirm
from src.services.logger import LOGGER


class Distributor:
    _max_balance = BALANCE_CUT_OFF
    __precision_threshold = 0.01

    @classmethod
    def assign_roles(cls, game: Game):
        plain_allowed: bool = (CURRENT_ASSIGNMENT & PLAIN_ASSIGNMENT) != 0
        balance_allowed: bool = (CURRENT_ASSIGNMENT & BALANCE_ASSIGNMENT) != 0
        simulation_allowed: bool = (CURRENT_ASSIGNMENT & SIMULATION_ASSIGNMENT) != 0

        game.simulation = simulation_allowed and random.random() < PROBABILITY_THRESHOLD
        cls._select_preset(game)

        if game.simulation:
            cls._assign_roles_simulation(game)
            LOGGER.verbose_debug("Running in simulation mode")
            return

        roles_str = ", ".join(game.current_preset)
        LOGGER.verbose_debug(f"Game is running with roles {roles_str}")

        if not balance_allowed:
            assert plain_allowed
            cls._assign_roles_plain(game)
            return

        cls._assign_roles_balance(game)

    @classmethod
    def _assign_roles_plain(cls, game: Game):
        roles: list[str] = game.current_preset.copy()
        random.shuffle(roles)

        assignments: dict[int, str] = {}
        for i, player in enumerate(game.players.values()):
            player.role = roles[i]
            assignments[player.user_id] = player.role

        cls._update_balances(cls._load_balance(game), assignments)

    @classmethod
    def _assign_roles_balance(cls, game: Game):
        player_ids: list[int] = [player.user_id for player in game.players.values()]
        stats: dict[int, Balance] = cls._load_balance(game)

        assignments: dict[int, str] = {}
        available_players = set(player_ids)

        for role in game.current_preset:
            player = cls._select_player(role, available_players, stats)

            assignments[player] = role
            available_players.remove(player)

        cls._update_balances(stats, assignments)

        for player in game.players.values():
            player.role = assignments[player.user_id]

    @staticmethod
    def _assign_roles_simulation(game: Game):
        for player in game.players.values():
            player.role = "Мирный житель"

    @classmethod
    def _select_player(
        cls, role: str, candidates: set[int], stats: dict[int, Balance]
    ) -> int:
        scores: list[tuple[int, float]] = []

        for player_id in candidates:
            player_stats = stats.get(player_id, Balance())

            score = player_stats.balance.get(role, 0.0)
            scores.append((player_id, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        best_score = scores[0][1]

        eligible_players = [
            player_id
            for player_id, score in scores
            if score >= best_score - cls.__precision_threshold
        ]
        return random.choice(eligible_players)

    @classmethod
    def _update_balances(cls, stats: dict[int, Balance], assignments: dict[int, str]):
        probabilities = cls._calculate_probabilities(list(assignments.values()))

        for player_stats in stats.values():
            for role, probability in probabilities.items():
                current_balance = player_stats.balance.get(role, 0.0)
                current_balance += probability

                player_stats.balance[role] = cls._clamp(current_balance)

        for player_id, role in assignments.items():
            current_balance = stats[player_id].balance.get(role, 0.0)
            current_balance -= 1.0

            stats[player_id].balance[role] = cls._clamp(current_balance)

        DATABASE.update_player_balance(stats)

    @staticmethod
    def _calculate_probabilities(roles: list[str]) -> dict[str, float]:
        role_counter = Counter(roles)
        total_roles = len(roles)

        return {role: count / total_roles for role, count in role_counter.items()}

    @classmethod
    def _clamp(cls, value: float) -> float:
        return max(-cls._max_balance, min(value, cls._max_balance))

    @staticmethod
    def _select_preset(game: Game):
        if ENVIRONMENT == EnvironmentType.TESTING:
            Distributor._choose_preset(game)
            return

        count = len(game.players)
        max_count = max(ROOM_PRESETS.keys())
        game.current_preset = random.choice(ROOM_PRESETS[min(count, max_count)]).copy()

        if game.simulation:
            max_count = max(SPECIAL_PRESETS.keys())
            game.current_preset = SPECIAL_PRESETS[min(count, max_count)].copy()

        game.fill_empty_slots()

    @staticmethod
    def _choose_preset(game: Game):
        assert ENVIRONMENT == EnvironmentType.TESTING
        count = len(game.players)

        if confirm("Use special room presets?", default_answer=False):
            max_count = max(SPECIAL_PRESETS.keys())
            available_count = min(max_count, count)
            LOGGER.regular_debug(f"Looking for room for {available_count} players")

            game.current_preset = SPECIAL_PRESETS[available_count].copy()
            game.fill_empty_slots()
            return

        max_count = max(ROOM_PRESETS.keys())
        available_count = min(max_count, count)
        LOGGER.regular_debug(f"Looking for room for {available_count} players")

        print(ROOM_PRESETS[available_count], sep="\n\n")
        while True:
            print("Choose index of desired preset")
            try:
                index = int(input())
                if index < 0 or index >= len(ROOM_PRESETS[available_count]):
                    print("This index is out of bounds")
                    continue

                game.current_preset = ROOM_PRESETS[available_count][index].copy()
                game.fill_empty_slots()
                return
            except:
                print("Invalid index")

    @staticmethod
    def _load_balance(game: Game) -> dict[int, Balance]:
        player_ids: list[int] = [player.user_id for player in game.players.values()]
        return DATABASE.load_player_balance(player_ids)
