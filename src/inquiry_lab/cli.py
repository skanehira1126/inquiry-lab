import argparse
import sys
from pathlib import Path

from inquiry_lab import __version__
from inquiry_lab.workspace import initialize_workspace


def cli_init(directory: Path, title: str) -> None:
    path = initialize_workspace(directory, title)
    print(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inquiry-lab", description="Create execution-independent analysis workspaces."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(required=True)
    init = commands.add_parser("init", help="expand analysis templates into a new directory")
    init.add_argument("directory", type=Path, help="new workspace directory (must not exist)")
    init.add_argument("--title", required=True, help="single-line analysis title")
    init.set_defaults(func=cli_init)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = vars(build_parser().parse_args(argv))
    func = args.pop("func")
    try:
        func(**args)
    except (OSError, ValueError) as error:
        print(f"inquiry-lab: {error}", file=sys.stderr)
        return 1
    return 0
