from enum import Enum


class QueryType(str, Enum):
    HELP = "help"
    ADMIN_HELP = "admin_help"
    STATUS = "status"
    DESCRIPTION = "description"
    ROLES = "roles"
    SPEECH = "speech"
    END_SPEECH = "end_speech"
    JOIN_GAME = "join_game"
    NOMINATE = "nominate"
    COMMIT_NOMINATE = "commit_nominate"
    VOTE = "vote"
    COMMIT_VOTE = "commit_vote"
    BALANCE = "balance"
    COMMIT_BALANCE = "commit_balance"
    OPEN_GAME = "open_game"
    RUN_GAME = "run_game"
    TERMINATE_GAME = "terminate_game"
    START_NIGHT = "start_night"
    SKIP_NIGHT = "skip_night"
    MAFIA_CHAT = "mafia_chat"
    NIGHT_ACTION = "night_action"

    @classmethod
    def from_string(cls, value: str):
        try:
            return cls(value)
        except ValueError:
            return None
