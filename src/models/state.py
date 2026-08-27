from enum import Enum


class State(Enum):
    LOBBY = "lobby"
    DAY = "day"
    DEFENSE = "defense"
    VOTE = "vote"
    BALANCE = "balance"
    REVOTE = "revote"
    THIEF = "thief"
    NIGHT = "night"
    DONE = "done"
