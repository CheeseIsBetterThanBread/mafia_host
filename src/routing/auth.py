from typing import Optional

from src.connection.event import Response

from src.routing.query import QueryType

from src.models import (
    Game,
    Left,
    Meta,
    Player,
    Query,
    Result,
    Right,
    State,
)

from src.role_info.presets import ROOM_PRESETS

from src.services.storage import STORAGE
from src.services.setup import setup_timers


def _make_invalid_response(query: Query, msg: str) -> Result:
    response = Response(query.chat_id, msg, valid=False)
    return Left(response)


def Wrap(query: Query) -> Result:
    meta_info: Meta = Meta(query)
    return Right(meta_info)


def admin_middleware(meta_info: Meta) -> Result:
    query: Query = meta_info.query
    if query.user_id not in query.admin_ids:
        return _make_invalid_response(query, "Доступно только администраторам")

    return Right(meta_info)


def active_game_middleware(meta_info: Meta) -> Result:
    query: Query = meta_info.query

    game: Optional[Game] = STORAGE.get_game(query.chat_id)
    if not game or game.state in [State.LOBBY, State.DONE]:
        return _make_invalid_response(query, "Игра ещё не началась")

    setup_timers(game)
    meta_info.game = game
    return Right(meta_info)


def no_game_middleware(meta_info: Meta) -> Result:
    query: Query = meta_info.query

    game: Optional[Game] = STORAGE.get_game(query.chat_id)
    if game and game.state != State.DONE:
        return _make_invalid_response(query, "В этом чате уже есть игра")

    return Right(meta_info)


def ready_to_start_middleware(meta_info: Meta) -> Result:
    query: Query = meta_info.query

    game: Optional[Game] = STORAGE.get_game(query.chat_id)
    if not game or game.state != State.LOBBY:
        return _make_invalid_response(query, "Игра не готова к запуску")

    if len(game.players) < min(ROOM_PRESETS.keys()):
        return _make_invalid_response(query, "Недостаточное количество участников")

    meta_info.game = game
    return Right(meta_info)


def right_phase_middleware(meta_info: Meta) -> Result:
    query: Query = meta_info.query
    game: Game = meta_info.game
    assert game is not None

    if query.cmd not in [QueryType.START_NIGHT, QueryType.SKIP_NIGHT]:
        raise ValueError("Настройте обработчик под новый тип запросов")

    if query.cmd == QueryType.START_NIGHT and game.state in [
        State.NIGHT,
        State.THIEF,
    ]:
        return _make_invalid_response(query, "Ночь уже началась")

    if query.cmd == QueryType.SKIP_NIGHT and game.state not in [
        State.NIGHT,
        State.THIEF,
    ]:
        return _make_invalid_response(query, "Сейчас не ночь")

    return Right(meta_info)


def in_game_middleware(meta_info: Meta) -> Result:
    query: Query = meta_info.query
    game: Game = meta_info.game
    assert game is not None

    if query.user_id not in game.players.keys():
        return _make_invalid_response(query, "Вы не в игре")

    return Right(meta_info)


def alive_middleware(meta_info: Meta) -> Result:
    query: Query = meta_info.query
    game: Game = meta_info.game
    assert game is not None

    player: Player = game.players.get(query.user_id)
    if not player.is_alive:
        return _make_invalid_response(query, "Доступно только живым")

    return Right(meta_info)
