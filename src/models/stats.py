from dataclasses import dataclass
from typing import Optional, Dict

from src.role_info.roles import ROLE_DESCRIPTIONS


@dataclass
class Balance:
    def __init__(self, balance: Optional[Dict[str, float]] = None):
        self.balance: dict[str, float] = {
            role: 0.0 for role in ROLE_DESCRIPTIONS.keys()
        }
        if balance:
            self.balance.update(balance)

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> "Balance":
        return cls(data)

    def to_dict(self):
        return self.balance


@dataclass
class WinRate:
    wins: int = 0
    total_games: int = 0

    @property
    def win_rate(self) -> float:
        return self.wins / self.total_games if self.total_games > 0 else 0.0

    @property
    def win_rate_percent(self) -> float:
        return self.win_rate * 100
