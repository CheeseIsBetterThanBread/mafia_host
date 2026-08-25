import re
from pathlib import Path

import yaml

from config.settings import CONFIG_DIR, SOURCE_DIR

CONFIG_PATH = CONFIG_DIR / "commands.yaml"
TARGET_DIR = SOURCE_DIR / "routing"
TARGET_DIR.mkdir(parents=True, exist_ok=True)


class CodeGenerator:
    def __init__(self, yaml_path: str, output_dir: str, force: bool):
        self.yaml_path = yaml_path
        self.output_dir = Path(output_dir)
        self.commands = []
        self.known_tags = {
            "internal",
            "is_admin",
            "no_game",
            "game_created",
            "in_game",
            "is_alive",
            "is_your_turn",
        }
        self.existing_guards = set()
        self.existing_handlers = set()

        self.handles_dir = self.output_dir / "handles"
        self.handles_dir.mkdir(parents=True, exist_ok=True)

        self.force = force

        self._check_existing_files()

    def _check_existing_files(self):
        for file in Path(TARGET_DIR).glob("guard_*.py"):
            self.existing_guards.add(file.stem.replace("guard_", ""))

        for file in self.handles_dir.glob("*.py"):
            if file.stem != "__init__":
                self.existing_handlers.add(file.stem)

    def load_yaml(self):
        with open(self.yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.commands = data.get("commands", [])

        for cmd in self.commands:
            if "handle" not in cmd:
                raise ValueError("Каждая команда должна содержать поле 'handle'")
            if "info" not in cmd:
                raise ValueError("Каждая команда должна содержать поле 'info'")

            tags = cmd.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]
            for tag in tags:
                if tag not in self.known_tags:
                    raise ValueError(
                        f"Неизвестный тег '{tag}' для команды {cmd['handle']}"
                    )

    def generate_help(self):
        content = "COMMANDS = {\n"
        for cmd in self.commands:
            tags = cmd.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]
            if "internal" in tags:
                continue

            handle = cmd["handle"]
            info = cmd["info"]
            content += f'    "{handle}": "{info}",\n'
        content += "}\n\n"

        content += "def get_help():\n"
        content += "    result = ['Доступные команды']\n"
        content += "    for cmd, info in COMMANDS.items():\n"
        content += '        result.append(f"  {cmd:15} - {info}")\n'
        content += "    return '\\n'.join(result)\n"

        help_path = self.output_dir / "help_message.py"
        help_path.write_text(content, encoding="utf-8")

    def generate_query(self):
        content = "from enum import Enum\n\n"
        content += "class QueryType(str, Enum):\n"

        for cmd in self.commands:
            handle = cmd["handle"]
            enum_name = self._to_enum_name(handle)
            content += f'    {enum_name} = "{handle}"\n'

        content += "\n    @classmethod\n"
        content += "    def from_string(cls, value: str):\n"
        content += "        try:\n"
        content += "            return cls(value)\n"
        content += "        except ValueError:\n"
        content += "            return None\n"

        query_path = self.output_dir / "query.py"
        query_path.write_text(content, encoding="utf-8")

    def generate_handlers(self):
        for cmd in self.commands:
            handle = cmd["handle"]

            if handle in self.existing_handlers and not self.force:
                continue

            content = ""

            tags = cmd.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]

            if tags:
                content += "# Доступ защищен тегами:\n"
                content += f"# {', '.join(tags)}\n"
                if "internal" in tags:
                    content += "# Для этой команды требуется guard\n"

                content += "\n\n"

            content += f"async def handle_{handle}(query):\n"
            content += "    # TODO: реализовать логику обработки\n"
            content += "    pass\n"

            handler_path = self.handles_dir / f"{handle}.py"
            handler_path.write_text(content, encoding="utf-8")

            self.existing_handlers.add(handle)

    def generate_guards(self):
        for cmd in self.commands:
            tags = cmd.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]

            if "internal" not in tags:
                continue

            handle = cmd["handle"]
            guard_name = f"guard_{handle}"
            guard_path = self.output_dir / f"{guard_name}.py"

            if (
                guard_path.exists() or handle in self.existing_guards
            ) and not self.force:
                continue

            content = f"async def guard_{handle}(query):\n"
            content += "    # TODO: реализовать логику проверки доступа\n"
            content += "    pass\n"

            guard_path.write_text(content, encoding="utf-8")
            self.existing_guards.add(handle)

    def generate_router(self):
        content = "from auth import *\n"
        content += "from query import QueryType\n"

        for cmd in self.commands:
            handle = cmd["handle"]
            assert handle in self.existing_handlers
            content += f"from handles.{handle} import handle_{handle}\n"

        content += "\n\n"
        content += "def process_query(query):\n"
        content += "    cmd = QueryType.from_string(query.get('cmd'))\n"
        content += "    if cmd is None:\n"
        content += "        raise ValueError('Неизвестная команда')\n\n"

        content += "    match cmd:\n"
        for cmd in self.commands:
            handle = cmd["handle"]
            enum_name = self._to_enum_name(handle)
            tags = cmd.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]

            handler_exists = handle in self.existing_handlers

            content += f"        case QueryType.{enum_name}:\n"

            if not handler_exists:
                content += "            raise NotImplementedError(f'Обработчик для {handle} не реализован')\n"
                continue

            if "internal" in tags:
                guard_exists = handle in self.existing_guards
                if guard_exists:
                    content += f"            return Wrap(query) >> guard_{handle} >> handle_{handle}\n"
                else:
                    content += f"            return Wrap(query) >> handle_{handle}\n"
            else:
                handler_chain = "Wrap(query)"
                for tag in tags:
                    handler_chain += f" >> {tag}_middleware"
                handler_chain += f" >> handle_{handle}"
                content += f"            return {handler_chain}\n"

        content += "        case _:\n"
        content += "            raise ValueError('Неизвестная команда')\n"

        router_path = self.output_dir / "router.py"
        router_path.write_text(content, encoding="utf-8")

    def _to_enum_name(self, handle: str) -> str:
        name = re.sub(r"[-\s]+", "_", handle)
        name = re.sub(r"[^a-zA-Z0-9_]", "", name)
        return name.upper()

    def generate_all(self):
        self.load_yaml()
        self.generate_help()
        self.generate_query()
        self.generate_handlers()
        self.generate_guards()
        self.generate_router()


def generate(force: bool):
    generator = CodeGenerator(CONFIG_PATH, TARGET_DIR, force)
    generator.generate_all()

    print("Commands generated successfully")
