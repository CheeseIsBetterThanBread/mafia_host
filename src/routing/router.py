from auth import *
from query import QueryType

from guards.join_game import guard_join_game
from guards.commit_nominate import guard_commit_nominate
from guards.commit_vote import guard_commit_vote
from guards.commit_balance import guard_commit_balance
from guards.mafia_chat import guard_mafia_chat
from guards.night_action import guard_night_action

from handles.help import handle_help
from handles.admin_help import handle_admin_help
from handles.status import handle_status
from handles.description import handle_description
from handles.roles import handle_roles
from handles.speech import handle_speech
from handles.end_speech import handle_end_speech
from handles.join_game import handle_join_game
from handles.nominate import handle_nominate
from handles.commit_nominate import handle_commit_nominate
from handles.vote import handle_vote
from handles.commit_vote import handle_commit_vote
from handles.balance import handle_balance
from handles.commit_balance import handle_commit_balance
from handles.open_game import handle_open_game
from handles.run_game import handle_run_game
from handles.terminate_game import handle_terminate_game
from handles.start_night import handle_start_night
from handles.skip_night import handle_skip_night
from handles.mafia_chat import handle_mafia_chat
from handles.night_action import handle_night_action


def process_query(query):
    cmd = QueryType.from_string(query.get("cmd", ""))
    match cmd:
        case QueryType.HELP:
            return Wrap(query) >> handle_help
        case QueryType.ADMIN_HELP:
            return Wrap(query) >> admin_middleware >> handle_admin_help
        case QueryType.STATUS:
            return Wrap(query) >> active_game_middleware >> handle_status
        case QueryType.DESCRIPTION:
            return Wrap(query) >> active_game_middleware >> handle_description
        case QueryType.ROLES:
            return Wrap(query) >> active_game_middleware >> handle_roles
        case QueryType.SPEECH:
            return (
                Wrap(query)
                >> active_game_middleware
                >> in_game_middleware
                >> alive_middleware
                >> turn_ready_middleware
                >> handle_speech
            )
        case QueryType.END_SPEECH:
            return (
                Wrap(query)
                >> active_game_middleware
                >> in_game_middleware
                >> alive_middleware
                >> turn_ready_middleware
                >> handle_end_speech
            )
        case QueryType.JOIN_GAME:
            return Wrap(query) >> guard_join_game >> handle_join_game
        case QueryType.NOMINATE:
            return (
                Wrap(query)
                >> active_game_middleware
                >> in_game_middleware
                >> alive_middleware
                >> turn_ready_middleware
                >> valid_target_middleware
                >> handle_nominate
            )
        case QueryType.COMMIT_NOMINATE:
            return Wrap(query) >> guard_commit_nominate >> handle_commit_nominate
        case QueryType.VOTE:
            return (
                Wrap(query)
                >> active_game_middleware
                >> in_game_middleware
                >> alive_middleware
                >> turn_ready_middleware
                >> valid_target_middleware
                >> handle_vote
            )
        case QueryType.COMMIT_VOTE:
            return Wrap(query) >> guard_commit_vote >> handle_commit_vote
        case QueryType.BALANCE:
            return (
                Wrap(query)
                >> active_game_middleware
                >> in_game_middleware
                >> alive_middleware
                >> turn_ready_middleware
                >> valid_target_middleware
                >> handle_balance
            )
        case QueryType.COMMIT_BALANCE:
            return Wrap(query) >> guard_commit_balance >> handle_commit_balance
        case QueryType.OPEN_GAME:
            return (
                Wrap(query)
                >> admin_middleware
                >> no_game_middleware
                >> handle_open_game
            )
        case QueryType.RUN_GAME:
            return (
                Wrap(query)
                >> admin_middleware
                >> ready_to_start_middleware
                >> handle_run_game
            )
        case QueryType.TERMINATE_GAME:
            return (
                Wrap(query)
                >> admin_middleware
                >> active_game_middleware
                >> in_game_middleware
                >> handle_terminate_game
            )
        case QueryType.START_NIGHT:
            return (
                Wrap(query)
                >> admin_middleware
                >> active_game_middleware
                >> right_phase_middleware
                >> in_game_middleware
                >> handle_start_night
            )
        case QueryType.SKIP_NIGHT:
            return (
                Wrap(query)
                >> admin_middleware
                >> active_game_middleware
                >> right_phase_middleware
                >> in_game_middleware
                >> handle_skip_night
            )
        case QueryType.MAFIA_CHAT:
            return Wrap(query) >> guard_mafia_chat >> handle_mafia_chat
        case QueryType.NIGHT_ACTION:
            return Wrap(query) >> guard_night_action >> handle_night_action
        case _:
            raise ValueError("Неизвестная команда")
