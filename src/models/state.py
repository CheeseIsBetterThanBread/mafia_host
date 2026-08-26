from enum import Enum


class State(Enum):
    LOBBY = "lobby"
    DAY = "day"
    DEFENSE = "defense"
    VOTING = "voting"
    BALANCE = "balance"
    REVOTE = "revote"
    NIGHT_THIEF = "night_thief"
    NIGHT = "night"
    FINISHED = "finished"
