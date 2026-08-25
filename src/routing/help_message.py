COMMANDS = {
    "help": "Выводит сообщение с доступными командами",
    "open_game": "Открывает регистрацию на игру",
}


def get_help():
    result = ["Доступные команды"]
    for cmd, info in COMMANDS.items():
        result.append(f"  {cmd:15} - {info}")
    return "\n".join(result)
