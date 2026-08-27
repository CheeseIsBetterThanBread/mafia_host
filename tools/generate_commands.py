import ast
import re
from pathlib import Path

import yaml

from config.settings import CONFIG_DIR, SOURCE_DIR, INTERNAL_TAG, KNOWN_TAGS

CONFIG_PATH = CONFIG_DIR / "commands.yaml"
TARGET_DIR = SOURCE_DIR / "routing"
TARGET_DIR.mkdir(parents=True, exist_ok=True)


class CodeGenerator:
    def __init__(self, yaml_path: str, output_dir: str, force: bool):
        self.yaml_path = yaml_path
        self.output_dir = Path(output_dir)
        self.commands = []
        self.known_tags = KNOWN_TAGS
        self.existing_guards = set()
        self.existing_handlers = set()

        self.handles_dir = self.output_dir / "handles"
        self.handles_dir.mkdir(parents=True, exist_ok=True)

        self.guards_dir = self.output_dir / "guards"
        self.guards_dir.mkdir(parents=True, exist_ok=True)

        self.existing_query_classes = set()
        self.event_file = SOURCE_DIR / "connection" / "event.py"

        self.force = force

        self.common_imports = "from src.models.meta import Meta, Result\n\n"

        self._load_yaml()
        self._scan_event_file()
        self._validate_queries()
        self._check_existing_files()

    def _scan_event_file(self):
        if not self.event_file.exists():
            print(f"Файл {self.event_file} не найден, пропускаем валидацию")
            return

        try:
            with open(self.event_file, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content)
            class_definitions = {}

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef) and not isinstance(
                    node, ast.Assign
                ):
                    continue

                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    bases = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            bases.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            bases.append(base.attr)

                    class_definitions[class_name] = {
                        "bases": bases,
                        "is_query": self._is_query_class(
                            class_name, bases, class_definitions
                        ),
                    }

                    if class_definitions[class_name]["is_query"]:
                        self.existing_query_classes.add(class_name)
                    continue

                for target in node.targets:
                    if not isinstance(target, ast.Name):
                        continue

                    if isinstance(node.value, ast.Name):
                        value_name = node.value.id
                        alias_to_old = (
                            value_name in class_definitions
                            and class_definitions[value_name]["is_query"]
                        )
                        if alias_to_old or self._is_query_class(value_name, [], {}):
                            alias_name = target.id
                            self.existing_query_classes.add(alias_name)

        except Exception as _:
            pass

    @staticmethod
    def _is_query_class(
        class_name: str, bases: list[str], class_definitions: dict
    ) -> bool:
        if class_name == "Query":
            return True

        if class_name.endswith("Query") or class_name.startswith("Query"):
            return True

        if "Query" in bases:
            return True

        for base in bases:
            if base in class_definitions and class_definitions[base]["is_query"]:
                return True

        return False

    @staticmethod
    def _handle_to_class_name(handle: str) -> str:
        parts = handle.split("_")
        class_name = "".join(word.capitalize() for word in parts)
        return class_name + "Query"

    def _get_expected_classes(self, cmd: dict) -> set[str]:
        handle = cmd["handle"]
        expected_classes = {self._handle_to_class_name(handle)}

        aliases: list[str] | str = cmd.get("alias", [])
        if not isinstance(aliases, list):
            aliases = [aliases]

        for alias in aliases:
            if alias.endswith("Query"):
                expected_classes.add(alias)
            else:
                expected_classes.add(self._handle_to_class_name(alias))

        return expected_classes

    def _validate_queries(self):
        missing_queries = []

        for cmd in self.commands:
            handle = cmd["handle"]
            if not (self._get_expected_classes(cmd) & self.existing_query_classes):
                missing_queries.append(handle)

        if not missing_queries:
            return

        error_msg = (
            f"Отсутствуют классы Query для следующих команд в {self.event_file}:\n"
        )
        for handle in missing_queries:
            expected_class = self._handle_to_class_name(handle)
            error_msg += f"\t- {handle} требует класса {expected_class}\n"

        raise ValueError(error_msg)

    def _check_existing_files(self):
        for file in self.guards_dir.glob("*.py"):
            self.existing_guards.add(file.stem)

        for file in self.handles_dir.glob("*.py"):
            self.existing_handlers.add(file.stem)

    def _sort_tags(self, tags):
        if not isinstance(tags, list):
            tags = [tags]

        return sorted(tags, key=lambda x: self.known_tags.get(x, 999))

    def _load_yaml(self):
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
                if tag == INTERNAL_TAG:
                    assert tags == [INTERNAL_TAG]
                    return

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
            if INTERNAL_TAG in tags or "admin" in tags:
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

            content = self.common_imports

            tags = cmd.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]

            if tags:
                content += "# Доступ защищен тегами:\n"
                content += f"# {', '.join(tags)}\n"
                if INTERNAL_TAG in tags:
                    content += "# Для этой команды требуется guard\n"

                content += "\n\n"

            content += f"async def handle_{handle}(meta_info: Meta) -> Result:\n"
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

            if INTERNAL_TAG not in tags:
                continue

            handle = cmd["handle"]
            guard_path = self.guards_dir / f"{handle}.py"

            if handle in self.existing_guards and not self.force:
                continue

            content = self.common_imports
            content += f"async def guard_{handle}(meta_info: Meta) -> Result:\n"
            content += "    # TODO: реализовать логику проверки доступа\n"
            content += "    pass\n"

            guard_path.write_text(content, encoding="utf-8")
            self.existing_guards.add(handle)

    def generate_router(self):
        content = "from auth import *\n"
        content += "from query import QueryType\n"

        additional_content = "\n"
        for cmd in self.commands:
            handle = cmd["handle"]
            tags = cmd.get("tags", [])
            if not isinstance(tags, list):
                tags = [tags]

            if INTERNAL_TAG not in tags:
                continue

            assert handle in self.existing_guards
            additional_content += f"from guards.{handle} import guard_{handle}\n"

        content += additional_content + "\n"

        for cmd in self.commands:
            handle = cmd["handle"]
            assert handle in self.existing_handlers
            content += f"from handles.{handle} import handle_{handle}\n"

        content += "\n\n"
        content += "def process_query(query):\n"
        content += "    cmd = QueryType.from_string(query.get('cmd', ''))\n"

        content += "    match cmd:\n"
        for cmd in self.commands:
            handle = cmd["handle"]
            enum_name = self._to_enum_name(handle)
            tags = self._sort_tags(cmd.get("tags", []))

            content += f"        case QueryType.{enum_name}:\n"

            if INTERNAL_TAG in tags:
                content += f"            return Wrap(query) >> guard_{handle} >> handle_{handle}\n"
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
        self.generate_help()
        self.generate_query()
        self.generate_handlers()
        self.generate_guards()
        self.generate_router()


def generate(force: bool):
    generator = CodeGenerator(CONFIG_PATH, TARGET_DIR, force)
    generator.generate_all()

    print("Commands generated successfully")
