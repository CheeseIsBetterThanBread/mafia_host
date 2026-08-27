from auth import *
from query import QueryType

from guards.night_action import guard_night_action

from handles.help import handle_help
from handles.open_game import handle_open_game
from handles.night_action import handle_night_action


def process_query(query):
    cmd = QueryType.from_string(query.get("cmd", ""))
    match cmd:
        case QueryType.HELP:
            return Wrap(query) >> handle_help
        case QueryType.OPEN_GAME:
            return (
                Wrap(query)
                >> is_admin_middleware
                >> no_game_middleware
                >> handle_open_game
            )
        case QueryType.NIGHT_ACTION:
            return Wrap(query) >> guard_night_action >> handle_night_action
        case _:
            raise ValueError("Неизвестная команда")
