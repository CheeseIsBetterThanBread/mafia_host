from pathlib import Path
from typing import Union
import os
import sqlite3

from config.settings import DB_PATH

from src.models import (
    Balance,
    Game,
    Player,
    WinRate,
    get_room_id,
)

from src.role_info.teams import ROLE_TO_TEAM, Team

from src.services.logger import LOGGER

FROM_ROLES = dict[str, WinRate]


class Database:
    def __init__(self, db_path: Union[str, Path]):
        if isinstance(db_path, str):
            self._db_path = db_path
        if isinstance(db_path, Path):
            self._db_path = str(db_path)

        self._ensure_db_directory()
        self._init_db()

    def _ensure_db_directory(self):
        db_dir = os.path.dirname(self._db_path)
        if db_dir:
            LOGGER.verbose_debug(f"Creating database directory {db_dir}")
            Path(db_dir).mkdir(parents=True, exist_ok=True)

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS balance (
                    player_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    balance REAL NOT NULL DEFAULT 0,

                    PRIMARY KEY (
                        player_id,
                        role
                    )
                )
                """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS win_rate (
                    player_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    room_id INTEGER NOT NULL,
                    wins INTEGER NOT NULL,
                    total_games INTEGER NOT NULL,

                    PRIMARY KEY (
                        player_id,
                        role,
                        room_id
                    )
                )
            """)

            conn.commit()
            LOGGER.verbose_debug(f"Created balance and win rate databases")

    def load_player_balance(self, player_ids: list[int]) -> dict[int, Balance]:
        result: dict[int, Balance] = {}
        for player_id in player_ids:
            result[player_id] = self._load_player_balance_by_id(player_id)

        return result

    def update_player_balance(self, stats: dict[int, Balance]) -> None:
        for player_id, player_stats in stats.items():
            self._update_player_balance_by_id(player_id, player_stats)

    def delete_player_stats(self, player_id: int) -> None:
        LOGGER.verbose_debug(f"Deleting stats for player with id {player_id}")
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE
                FROM balance
                WHERE player_id = ?
                """,
                (player_id,),
            )

            cursor.execute(
                """
                DELETE
                FROM win_rate
                WHERE player_id = ?
                """,
                (player_id,),
            )

            conn.commit()

    def _load_player_balance_by_id(self, player_id: int) -> Balance:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT
                    role,
                    balance
                FROM balance
                WHERE player_id = ?
                """,
                (player_id,),
            )

            rows = cursor.fetchall()

        if not rows:
            LOGGER.verbose_debug(f"Did not find player with id {player_id}")
            return Balance()

        role_balance = {role: balance for role, balance in rows}

        return Balance.from_dict(role_balance)

    def _update_player_balance_by_id(self, player_id: int, stats: Balance) -> None:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            for role, balance in stats.balance.items():
                cursor.execute(
                    """
                    INSERT OR REPLACE
                    INTO balance (
                        player_id,
                        role,
                        balance
                    )
                    VALUES (?, ?, ?)
                    """,
                    (player_id, role, balance),
                )

            conn.commit()

    def load_player_win_rate(self, player_ids: list[int]) -> dict[int, FROM_ROLES]:
        result: dict[int, FROM_ROLES] = {}
        for player_id in player_ids:
            result[player_id] = self._load_player_win_rate_by_id(player_id)

        return result

    def update_win_rate(self, game: Game, winner: Team) -> None:
        room_id: int = get_room_id(game.current_preset)
        for player in game.players.values():
            self._update_win_rate_by_player(player, room_id, winner)

    def load_room_win_rate(self, room_id: int) -> dict[Team, float]:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    role,
                    SUM(wins) as total_wins,
                    SUM(total_games) as total_games
                FROM win_rate
                WHERE room_id = ?
                GROUP BY role
                HAVING SUM(total_games) >= 1
            """,
                (room_id,),
            )

            team_stats: dict[Team, dict] = {}

            for role, wins, games in cursor.fetchall():
                team = ROLE_TO_TEAM[role]
                if role == "Двуликий":
                    team = Team.MAFIA

                if team not in team_stats.keys():
                    team_stats[team] = {"wins": 0, "games": 0}

                team_stats[team]["wins"] += wins
                team_stats[team]["games"] += games

            result = {}
            for team, stats in team_stats.items():
                if stats["games"] > 0:
                    result[team] = stats["wins"] / stats["games"]
                else:
                    result[team] = 0.0

            return result

    def load_role_win_rate(self) -> FROM_ROLES:
        stats: FROM_ROLES = {}
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT 
                    role,
                    SUM(wins) as total_wins,
                    SUM(total_games) as total_games
                FROM win_rate
                GROUP BY role
                HAVING SUM(total_games) >= 1
            """)

            for role, wins, total_games in cursor.fetchall():
                stats[role] = WinRate(wins, total_games)

        return stats

    def _load_player_win_rate_by_id(self, player_id: int) -> FROM_ROLES:
        stats: FROM_ROLES = {}

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT 
                    role,
                    SUM(wins) as total_wins,
                    SUM(total_games) as total_games
                FROM win_rate
                WHERE player_id = ?
                GROUP BY role
                HAVING SUM(total_games) >= 1
            """,
                (player_id,),
            )

            for role, wins, total_games in cursor.fetchall():
                stats[role] = WinRate(wins, total_games)

        return stats

    def _update_win_rate_by_player(
        self, player: Player, room_id: int, winner: Team
    ) -> None:
        win_delta = 1 if self._is_player_winner(player, winner) else 0

        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO win_rate (player_id, role, room_id, wins, total_games)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(player_id, role, room_id) DO UPDATE SET
                    wins = wins + ?,
                    total_games = total_games + 1
            """,
                (player.user_id, player.role, room_id, win_delta, 1, win_delta),
            )

            conn.commit()

    @staticmethod
    def _is_player_winner(player: Player, winner: Team) -> bool:
        if player.role == "Двуликий":
            return winner == Team.MAFIA and player.found_mafia

        return winner == ROLE_TO_TEAM[player.role]


DATABASE = Database(DB_PATH)
