from enum import Enum


class QueryType(str, Enum):
    HELP = "help"
    OPEN_GAME = "open_game"
    NIGHT_ACTION = "night_action"

    @classmethod
    def from_string(cls, value: str):
        try:
            return cls(value)
        except ValueError:
            return None
