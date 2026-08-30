from src.services.engine import Engine

from config.settings import (
    REMINDER_OFFSET,
    THIEF_TIME,
    NIGHT_TIME,
)

from src.models import (
    Game,
    Meta,
    Player,
    Response,
    State,
)


def _make_valid_response(game: Game, msg: str):
    return Response(game.chat_id, msg, valid=True)


async def _simulate_thief(meta_info: Meta):
    response: Response = _make_valid_response(
        meta_info.game,
        "Вор никого не заклеил",
    )
    meta_info.add_response(response)
    Engine.start_night(meta_info)


async def _simulate_night(meta_info: Meta):
    Engine.finish_night(meta_info)


async def _thief_timeout(meta_info: Meta, current_day: int):
    game: Game = meta_info.game
    if game.state != State.THIEF or game.day_count != current_day:
        return

    response: Response = _make_valid_response(game, "Вор никого не заклеил")
    meta_info.add_response(response)

    game.expected_night_actors.clear()
    alive: list[Player] = game.filter_players(lambda p: p.is_alive)
    thief = next((p for p in alive if p.role == "Вор"), None)
    if thief:
        thief.last_rek = None

    Engine.start_night(meta_info)


async def _night_reminder(meta_info: Meta, current_day: int):
    game: Game = meta_info.game
    if game.state != State.NIGHT or game.day_count != current_day:
        return

    for uid in game.expected_night_actors.keys():
        response = Response(
            uid,
            f"<b>Осталось {REMINDER_OFFSET} секунд!</b> Поторопитесь сделать свой выбор, иначе ваш ход сгорит.",
            parse_mode="HTML",
            valid=True,
        )
        meta_info.add_response(response)

    game.timer_manager.update_timer("night_timeout", meta_info, current_day)
    game.timer_manager.restart_timer("night_timeout")


async def _night_timeout(meta_info: Meta, current_day: int):
    game: Game = meta_info.game
    if game.state != State.NIGHT or game.day_count != current_day:
        return

    response = Response(
        game.chat_id,
        "<b>Время вышло!</b> Ночь затянулась.",
        parse_mode="HTML",
        valid=True,
    )
    meta_info.add_response(response)
    game.expected_night_actors.clear()

    Engine.finish_night(meta_info)


def setup_timers(game: Game):
    game.timer_manager.add_timer("simulate_thief", 0.0, _simulate_thief)
    game.timer_manager.add_timer("simulate_night", 0.0, _simulate_night)
    game.timer_manager.add_timer("thief_timeout", THIEF_TIME, _thief_timeout)
    game.timer_manager.add_timer(
        "night_reminder", NIGHT_TIME - REMINDER_OFFSET, _night_reminder
    )
    game.timer_manager.add_timer(
        "night_timeout", REMINDER_OFFSET, _night_timeout
    )