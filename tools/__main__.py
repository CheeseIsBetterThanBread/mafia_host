import argparse

from tools.generate_roles import generate as generate_roles
from tools.generate_commands import generate as generate_commands

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Генератор кода из YAML файлов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Принудительно перегенерировать все файлы, даже если они существуют",
        default=False,
    )

    args = parser.parse_args()

    generate_roles()
    generate_commands(args.force)
