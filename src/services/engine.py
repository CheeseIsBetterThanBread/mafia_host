from asyncio import sleep
import random

from config.settings import (
    THIEF_TIME,
    THIEF_LOWER,
    THIEF_UPPER,
    NIGHT_TIME,
    NIGHT_LOWER,
    NIGHT_UPPER,
    NIGHT_CALLBACK_TEMPLATE,
    NULL_OPTION,
    REMINDER_OFFSET,
)

from src.connection.event import ResponseWithOptions

from src.routing.query import QueryType

from src.models import (
    Game,
    Meta,
    Player,
    Response,
    State,
)

from src.role_info.teams import Team
from src.role_info.role_actions import NightAction
from src.role_info.role_actions import ROLE_NIGHT_ACTIONS

from src.services.database import DATABASE
from src.services.logger import LOGGER
from src.services.unreachable import Unreachable


class Engine:
    @staticmethod
    def setup_timers(meta_info: Meta):
        game: Game = meta_info.game
        game.timer_manager.add_timer("simulate_thief", 0.0, Engine._simulate_thief)
        game.timer_manager.add_timer("simulate_night", 0.0, Engine._simulate_night)
        game.timer_manager.add_timer("thief_timeout", THIEF_TIME, Engine._thief_timeout)
        game.timer_manager.add_timer(
            "night_reminder", NIGHT_TIME - REMINDER_OFFSET, Engine._night_reminder
        )
        game.timer_manager.add_timer(
            "night_timeout", REMINDER_OFFSET, Engine._night_timeout
        )

    @staticmethod
    def _make_valid_response(game: Game, msg: str):
        return Response(game.chat_id, msg, valid=True)

    @staticmethod
    def _check_for_victory(meta_info: Meta) -> bool:
        game: Game = meta_info.game
        if game.simulation:
            return False

        alive: list[Player] = game.filter_players(lambda p: p.is_alive)
        if not alive:
            LOGGER.verbose_debug("Everyone died: mafia wins")
            DATABASE.update_win_rate(game, Team.MAFIA)
            response: Response = Engine._make_valid_response(
                game, "Все умерли - победа мафии"
            )
            meta_info.add_response(response)
            game.state = State.DONE
            return True

        mafia = sum(
            1
            for p in alive
            if p.role in game.mafia_team or (p.role == "Двуликий" and p.found_mafia)
        )
        maniac = sum(1 for p in alive if p.role.startswith("Маньяк"))
        town = len(alive) - mafia - maniac

        if len(alive) <= 2 and maniac > 0:
            LOGGER.verbose_debug("Maniac is left with the victim: maniac wins")
            DATABASE.update_win_rate(game, Team.MANIAC)
            response: Response = Engine._make_valid_response(
                game,
                "Маньяк остался один на один с жертвой - победа маньяка",
            )
            meta_info.add_response(response)
            game.state = State.DONE
            return True

        if mafia == 0 and maniac == 0:
            LOGGER.verbose_debug("Only citizens are left: citizens win")
            DATABASE.update_win_rate(game, Team.CITIZEN)
            response: Response = Engine._make_valid_response(
                game,
                "Вся мафия и маньяки уничтожены - победа мирного города",
            )
            meta_info.add_response(response)
            game.state = State.DONE
            return True

        if mafia >= town and maniac == 0:
            LOGGER.verbose_debug("Mafia dominates table: mafia wins")
            DATABASE.update_win_rate(game, Team.MAFIA)
            response: Response = Engine._make_valid_response(
                game,
                "Мафий за столом не меньше, чем мирных - победа мафии",
            )
            meta_info.add_response(response)
            game.state = State.DONE
            return True

        return False

    @staticmethod
    def _generate_night_moves(meta_info: Meta):
        game: Game = meta_info.game
        alive_players = game.filter_players(lambda p: p.is_alive)

        for player in alive_players:
            if player.user_id in game.night_actions:
                continue

            if player.is_glued:
                continue

            if player.role == "Ниндзя":
                target = random.choice(alive_players)
                game.night_actions.setdefault(player.user_id, {})[
                    NightAction.SHURIKEN
                ] = target.number

                LOGGER.verbose_debug(
                    f"Ninja skipped night move: send to {target.user_id}"
                )

                response = Response(
                    player.user_id,
                    f"Вы проспали ход! Бот случайно бросил сюрикен в игрока #{target.number}",
                    valid=True,
                )
                meta_info.add_response(response)
                continue

            if player.role == "Тула":
                LOGGER.verbose_debug("Tula skipped night move")

                valid_targets = [
                    t for t in alive_players if t.number != player.last_healed
                ]
                if valid_targets:
                    target = random.choice(valid_targets)
                    game.night_actions.setdefault(player.user_id, {})[
                        NightAction.TULA
                    ] = target.number

                    response = Response(
                        player.user_id,
                        f"Вы проспали ход! Бот случайно отправил вас к игроку #{target.number}",
                        valid=True,
                    )
                    meta_info.add_response(response)
                else:
                    player.last_healed = None

                continue

            if player.role in ["Маньяк без бинтов", "Маньяк с бинтами"]:
                if player.role == "Маньяк с бинтами":
                    player.last_man_heal = False

                target = random.choice(alive_players)
                game.night_actions.setdefault(player.user_id, {})[
                    NightAction.MANIAC_KILL
                ] = target.number

                LOGGER.verbose_debug(
                    f"Maniac skipped night move: send to {target.user_id}"
                )

                response = Response(
                    player.user_id,
                    f"Вы проспали ход! Бот случайно отправил вас убивать игрока #{target.number}",
                    valid=True,
                )
                meta_info.add_response(response)
                continue

            if player.role == "Двуликий" and getattr(player, "found_mafia", False):
                target = random.choice(alive_players)
                game.night_actions.setdefault(player.user_id, {})[
                    NightAction.TWO_FACE_KILL
                ] = target.number

                LOGGER.verbose_debug(
                    f"Two face skipped night move: send to {target.user_id}"
                )

                response = Response(
                    player.user_id,
                    f"Вы проспали ход! Бот случайно отправил вас убивать игрока #{target.number}.",
                    valid=True,
                )
                meta_info.add_response(response)
                continue

            if player.role == "Доктор":
                LOGGER.verbose_debug("Doctor skipped night move")
                player.last_healed = None

            if player.role == "Адвокат":
                LOGGER.verbose_debug("Lawyer skipped night move")
                player.last_alibi = None

    @staticmethod
    def start_day(meta_info: Meta):
        game: Game = meta_info.game
        if game.state not in [State.LOBBY, State.NIGHT]:
            raise RuntimeError(f"Unknown phase change in start_day: {game.state}")

        game.state = State.DAY
        game.day_count += 1
        game.vote_count = 0

        alive_players: list[Player] = game.filter_players(lambda p: p.is_alive)

        for player in game.players.values():
            player.has_nominated = False

        if game.day_count > 1:
            alive_nums = sorted([p.number for p in alive_players])
            assert alive_nums

            next_starter = alive_nums[0]
            for num in alive_nums:
                if num > game.day_starter_num:
                    next_starter = num
                    break
            game.day_starter_num = next_starter

        game.nominated = []
        game.build_daily_queue()

        first: Player = game.order_queue[0]
        response: Response = Engine._make_valid_response(
            game,
            f"Наступает день {game.day_count}.\n"
            f"Первым говорит игрок #{first.number}. Напишите /speech.",
        )
        meta_info.add_response(response)

    @staticmethod
    def next_speaker(meta_info: Meta):
        game: Game = meta_info.game
        if game.state not in [State.DAY, State.DEFENSE]:
            raise RuntimeError(f"Unknown phase change in next_speaker: {game.state}")

        game.pop_speaker()

        while game.order_queue and game.order_queue[0].is_glued:
            glued: Player = game.pop_speaker()
            response: Response = Engine._make_valid_response(
                game,
                f"Игрок #{glued.number} заклеен вором и пропускает свою речь",
            )
            meta_info.add_response(response)

        if game.order_queue:
            current: Player = game.order_queue[0]
            response: Response = Engine._make_valid_response(
                game,
                f"Очередь игрока #{current.number}. Напишите /speech",
            )
            meta_info.add_response(response)
            return

        response: Response = Engine._make_valid_response(
            game,
            "Речи завершены, переходим к следующему этапу",
        )
        meta_info.add_response(response)

        if game.state == State.DAY:
            Engine.start_defense(meta_info)
            return

        if game.state == State.DEFENSE:
            Engine.start_vote(meta_info)
            return

        Unreachable()

    @staticmethod
    def start_defense(meta_info: Meta):
        game: Game = meta_info.game
        if game.state != State.DAY:
            raise RuntimeError(f"Unknown phase change in start_defense: {game.state}")

        if not game.nominated:
            response: Response = Engine._make_valid_response(
                game,
                "Никто не выставлен, город засыпает",
            )
            meta_info.add_response(response)

            Engine.start_thief(meta_info)
            return

        game.state = State.DEFENSE
        game.build_defense_queue()

        first: Player = game.order_queue[0]
        response: Response = Engine._make_valid_response(
            game,
            f"На голосование выставлены игроки с номерами {game.nominated}\n"
            f"Переходим к оправдательным речам, начинает игрок #{first.number}. Напишите /speech",
        )
        meta_info.add_response(response)

    @staticmethod
    def start_vote(meta_info: Meta):
        game: Game = meta_info.game
        if game.state != State.DEFENSE or not game.nominated:
            raise RuntimeError(f"Unknown phase change in start_vote: {game.state}")

        if len(game.nominated) > 1:
            game.state = State.VOTE
            game.vote_count += 1
            game.current_votes = {num: 0 for num in game.nominated}
            game.vote_history = {}
            game.build_daily_queue()

            first: Player = game.order_queue[0]
            response: Response = Engine._make_valid_response(
                game,
                f"Начинаем голосование, выставлены {game.nominated}\n"
                f"Первым голосует игрок #{first.number}. Напишите /vote",
            )
            meta_info.add_response(response)
            return

        killed: int = game.nominated[0]
        response: Response = Engine._make_valid_response(
            game,
            f"На голосование выставлен только игрок #{killed}, срабатывает автокик",
        )
        meta_info.add_response(response)

        Engine._eliminate(meta_info, killed)

    @staticmethod
    def finish_vote(meta_info: Meta):
        game: Game = meta_info.game
        if game.state not in [State.VOTE, State.REVOTE]:
            raise RuntimeError(f"Unknown phase change in finish_vote: {game.state}")

        critical_vote = max(game.current_votes.values())
        leaders = [n for n, v in game.current_votes.items() if v == critical_vote]

        if len(leaders) == 1:
            Engine._eliminate(meta_info, leaders[0])
            return

        if game.vote_count < 2:
            Engine.start_balance(meta_info, leaders)
            return

        response: Response = Engine._make_valid_response(
            game,
            "Голоса снова разделились, автоматическое оправдание. Город засыпает...",
        )
        meta_info.add_response(response)
        Engine.start_thief(meta_info)

    @staticmethod
    def _eliminate(meta_info: Meta, killed: int):
        game: Game = meta_info.game
        player: Player = game.players_by_number[killed]

        if player.has_alibi:
            response: Response = Engine._make_valid_response(
                game, f"Игрок #{killed} должен был покинуть стол, но у него алиби"
            )
            meta_info.add_response(response)
        else:
            player.is_alive = False
            response: Response = Engine._make_valid_response(
                game, f"Игрок #{killed} покидает стол"
            )
            meta_info.add_response(response)

            if Engine._check_for_victory(meta_info):
                return

        response: Response = Engine._make_valid_response(game, "Город засыпает...")
        meta_info.add_response(response)

        Engine.start_thief(meta_info)

    @staticmethod
    def start_balance(meta_info: Meta, player_numbers: list[int]):
        game: Game = meta_info.game
        if game.state != State.VOTE:
            raise RuntimeError(f"Unknown phase change in start_balance: {game.state}")

        game.state = State.BALANCE
        game.balance_players = player_numbers
        game.current_votes = {"acquit": 0, "kill": 0, "revote": 0}
        game.vote_history = {}
        game.build_daily_queue()

        response: Response = Engine._make_valid_response(
            game,
            f"Баланс между игроками: {player_numbers}\n"
            f"Первым голосует игрок #{game.order_queue[0].number}. Пишите /balance",
        )
        meta_info.add_response(response)

    @staticmethod
    def finish_balance(meta_info: Meta):
        game: Game = meta_info.game
        if game.state != State.BALANCE:
            raise RuntimeError(f"Unknown phase change in finish_balance: {game.state}")

        votes = game.current_votes
        critical_vote = max(votes.values())

        if votes["acquit"] == critical_vote:
            response: Response = Engine._make_valid_response(
                game,
                "Все оправданы\nГород засыпает...",
            )
            meta_info.add_response(response)
            Engine.start_thief(meta_info)
            return

        if votes["revote"] == critical_vote:
            game.vote_count += 1
            game.state = State.REVOTE
            game.current_votes = {num: 0 for num in game.balance_players}
            game.vote_history = {}
            game.build_daily_queue()

            response: Response = Engine._make_valid_response(
                game, "Переголосование! Пишите /vote за игроков на балансе"
            )
            meta_info.add_response(response)
            return

        assert votes["kill"] == critical_vote

        killed = []
        saved = []
        for num in game.balance_players:
            if game.players_by_number[num].has_alibi:
                saved.append(num)
            else:
                game.players_by_number[num].is_alive = False
                killed.append(num)

        killed_str = ", ".join(map(str, killed)) if killed else "никто"
        msg = f"По результатам баланса убиты: {killed_str}."
        if saved:
            saved_str = ", ".join(map(str, saved))
            msg += f"\nСпасены алиби: {saved_str}."

        response: Response = Engine._make_valid_response(game, msg)
        meta_info.add_response(response)

        if Engine._check_for_victory(meta_info):
            return

        response: Response = Engine._make_valid_response(game, "Город засыпает...")
        meta_info.add_response(response)
        Engine.start_thief(meta_info)

    @staticmethod
    def start_thief(meta_info: Meta):
        game: Game = meta_info.game
        game.state = State.THIEF
        game.night_actions = {}
        game.expected_night_actors = {}

        for p in game.players.values():
            p.is_glued = False
            p.has_alibi = False

        alive_players = game.filter_players(lambda p: p.is_alive)

        thief = next((p for p in alive_players if p.role == "Вор"), None)
        thief_in_preset = "Вор" in game.current_preset

        if not thief_in_preset:
            Engine.start_night(meta_info)
            return

        game.timer_manager.update_timer("thief_timeout", meta_info, game.day_count)
        game.timer_manager.restart_timer("thief_timeout")

        response: Response = Engine._make_valid_response(
            game,
            f"Ждём ход вора (у него есть {THIEF_TIME} секунд)",
        )
        meta_info.add_response(response)

        if not thief:
            game.timer_manager.update_timer("simulate_thief", meta_info)
            game.timer_manager.restart_timer(
                "simulate_thief", random.randint(THIEF_LOWER, THIEF_UPPER)
            )
            return

        thief_action_info = ROLE_NIGHT_ACTIONS["Вор"][0]
        game.expected_night_actors[thief.user_id] = [thief_action_info[0]]

        generate_callback = lambda number: NIGHT_CALLBACK_TEMPLATE.format(
            chat_id=game.chat_id, action=thief_action_info[0], target=number
        )
        thief_options = [
            (f"№{t.number} ({t.name})", generate_callback(t.number))
            for t in alive_players
        ]
        thief_options.append(("Никого не клеить", generate_callback(NULL_OPTION)))

        response = ResponseWithOptions(
            thief.user_id,
            thief_action_info[1],
            thief_options,
            valid=True,
            cmd=QueryType.NIGHT_ACTION,
        )
        meta_info.add_response(response)

    @staticmethod
    def start_night(meta_info: Meta):
        game: Game = meta_info.game
        if game.state != State.THIEF:
            raise RuntimeError(f"Unknown phase change in start_night: {game.state}")

        game.state = State.NIGHT
        game.expected_night_actors.clear()
        alive_players = game.filter_players(lambda p: p.is_alive)

        response: Response = Engine._make_valid_response(
            game,
            f"Активные роли делают свой ход. У них есть {NIGHT_TIME} секунд на все действия",
        )
        meta_info.add_response(response)

        game.timer_manager.update_timer("night_reminder", meta_info, game.day_count)
        game.timer_manager.start_timer("night_reminder")

        for p in alive_players:
            if p.role == "Вор" or p.is_glued:
                continue

            if p.role not in ROLE_NIGHT_ACTIONS.keys():
                continue

            actions = ROLE_NIGHT_ACTIONS[p.role]

            generate_callback = lambda action, number: NIGHT_CALLBACK_TEMPLATE.format(
                chat_id=game.chat_id, action=action.value, target=number
            )
            game.expected_night_actors[p.user_id] = [act[0] for act in actions]
            game.night_actions.setdefault(p.user_id, {})

            for act_code, text in actions:
                action_options = []
                match act_code:
                    case NightAction.MANIAC_HEAL:
                        button_text = ROLE_NIGHT_ACTIONS[p.role][1][1]
                        action_options = [
                            (button_text, generate_callback(act_code, p.number))
                        ]
                    case NightAction.TWO_FACE_CHECK:
                        if p.found_mafia:
                            continue
                    case NightAction.TWO_FACE_KILL:
                        if not p.found_mafia:
                            continue
                    case other:
                        action_options = [
                            (
                                f"№{t.number} ({t.name})",
                                generate_callback(other, t.number),
                            )
                            for t in alive_players
                        ]

                response = ResponseWithOptions(
                    p.user_id,
                    text,
                    action_options,
                    valid=True,
                    cmd=QueryType.NIGHT_ACTION,
                )
                meta_info.add_response(response)

        if not game.expected_night_actors:
            if game.simulation:
                game.timer_manager.update_timer("simulate_night", meta_info)
                game.timer_manager.restart_timer(
                    "simulate_night", random.randint(NIGHT_LOWER, NIGHT_UPPER)
                )
                return

            Engine.finish_night(meta_info)

    @staticmethod
    def finish_night(meta_info: Meta):
        Engine._generate_night_moves(meta_info)
        game: Game = meta_info.game

        healed = set()
        mafia_votes = {}
        killed_this_night = set()
        putana_client = None
        alive = game.filter_players(lambda p: p.is_alive)

        shurikens_before = {p.number for p in alive if p.shurikens > 0}
        mafia_dead = not any(p.is_alive for p in alive if p.role in game.mafia_team)
        mafia_blocked = (
            any(p.is_glued for p in alive if p.role in game.mafia_team) or mafia_dead
        )

        actions = []
        for uid, acts in game.night_actions.items():
            for code, target in acts.items():
                actions.append(
                    {
                        "actor": game.players[uid],
                        "code": code,
                        "target": game.players_by_number[target],
                    }
                )

        for a in actions:
            if a["actor"].is_glued:
                continue
            if a["code"] == NightAction.HEAL:
                healed.add(a["target"].number)
                a["actor"].last_healed = a["target"].number
                a["target"].shurikens = 0
            elif a["code"] == NightAction.TULA:
                a["target"].has_alibi = True
                a["actor"].last_healed = a["target"].number
                a["target"].shurikens = 0
                putana_client = a["target"]
            elif a["code"] == NightAction.MANIAC_HEAL:
                healed.add(a["target"].number)
                a["target"].shurikens = 0

        def is_healed(number):
            healed_by_others = number in healed
            if healed_by_others:
                return True

            return putana_client is not None and number == putana_client.number

        for a in actions:
            if a["code"] == NightAction.ALIBI and not a["actor"].is_glued:
                a["target"].has_alibi = True
                a["actor"].last_alibi = a["target"].number

        for a in actions:
            if a["code"] == NightAction.SHURIKEN and not a["actor"].is_glued:
                if not is_healed(a["target"].number):
                    a["target"].shurikens += 1

        mafia_victim = None
        if not mafia_blocked:
            for a in actions:
                if a["code"] == NightAction.VOTE and not a["actor"].is_glued:
                    weight = 2 if a["actor"].role == "Дон" else 1
                    mafia_votes[a["target"].number] = (
                        mafia_votes.get(a["target"].number, 0) + weight
                    )
            if mafia_votes:
                max_v = max(mafia_votes.values())
                leaders = [t for t, v in mafia_votes.items() if v == max_v]
                if leaders:
                    mafia_victim = game.players_by_number[random.choice(leaders)]
            else:
                LOGGER.verbose_debug("Entire mafia skipped night move")
                if alive and not game.simulation:
                    mafia_victim = random.choice(alive)

        solo_victims = []
        for a in actions:
            if a["actor"].is_glued:
                continue
            if a["code"] in [NightAction.MANIAC_KILL, NightAction.TWO_FACE_KILL]:
                solo_victims.append(a["target"])

        if mafia_victim:
            if (
                not is_healed(mafia_victim.number)
                and mafia_victim.role != "Бессмертный"
            ):
                killed_this_night.add(mafia_victim.number)

        for victim in solo_victims:
            if not is_healed(victim.number) and victim.role != "Бессмертный":
                killed_this_night.add(victim.number)

        for p in alive:
            if p.shurikens >= 2 and not is_healed(p.number):
                if p.role == "Бессмертный":
                    p.shurikens = 0
                else:
                    killed_this_night.add(p.number)

        for p in alive:
            if p.role == "Тула" and p.number in killed_this_night:
                if not putana_client or putana_client.number == p.number:
                    continue
                if (
                    putana_client.role == "Бессмертный"
                    or putana_client.number in healed
                ):
                    continue
                killed_this_night.add(putana_client.number)

        announcement = "Город просыпается\n\n"
        if killed_this_night:
            for num in killed_this_night:
                game.players_by_number[num].is_alive = False
            announcement += (
                f"Этой ночью были убиты: {', '.join(map(str, killed_this_night))}.\n"
            )
        else:
            announcement += "Этой ночью никто не умер!\n"

        lost_shurikens = [
            num
            for num in shurikens_before
            if game.players_by_number[num].is_alive
            and game.players_by_number[num].shurikens == 0
        ]
        if lost_shurikens:
            announcement += f"Сюрикены были успешно извлечены (сброшены) у игроков: {', '.join(map(str, lost_shurikens))}\n"

        current_shurikens = [p.number for p in alive if p.shurikens == 1]
        if current_shurikens:
            announcement += f"Внимание! По 1 сюрикену сейчас висит на игроках: {', '.join(map(str, current_shurikens))}\n"

        response: Response = Engine._make_valid_response(game, announcement)
        meta_info.add_response(response)

        if Engine._check_for_victory(meta_info):
            return

        Engine.start_day(meta_info)

    @staticmethod
    async def _simulate_thief(meta_info: Meta):
        response: Response = Engine._make_valid_response(
            meta_info.game,
            "Вор никого не заклеил",
        )
        meta_info.add_response(response)
        Engine.start_night(meta_info)

    @staticmethod
    async def _simulate_night(meta_info: Meta):
        await sleep(random.randint(NIGHT_LOWER, NIGHT_UPPER))
        Engine.finish_night(meta_info)

    @staticmethod
    async def _thief_timeout(meta_info: Meta, current_day: int):
        game: Game = meta_info.game
        if game.state != State.THIEF or game.day_count != current_day:
            return

        response: Response = Engine._make_valid_response(game, "Вор никого не заклеил")
        meta_info.add_response(response)

        game.expected_night_actors.clear()
        alive: list[Player] = game.filter_players(lambda p: p.is_alive)
        thief = next((p for p in alive if p.role == "Вор"), None)
        if thief:
            thief.last_rek = None

        Engine.start_night(meta_info)

    @staticmethod
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

    @staticmethod
    async def _night_timeout(meta_info: Meta, current_day: int):
        game: Game = meta_info.game
        if game.state != State.NIGHT or game.day_count != current_day:
            return

        response = Response(
            game.chat_id,
            "⏰ <b>Время вышло!</b> Ночь затянулась.",
            parse_mode="HTML",
            valid=True,
        )
        meta_info.add_response(response)
        game.expected_night_actors.clear()

        Engine.finish_night(meta_info)
