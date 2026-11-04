import argparse
import json
import sys
from pathlib import Path

from inquiry_lab import __version__
from inquiry_lab.history import record_entry, render_history
from inquiry_lab.workspace import initialize_workspace


def cli_init(directory: Path, title: str) -> None:
    path = initialize_workspace(directory, title)
    print(path)


def cli_history_record(workspace: Path, input_file: Path | None) -> None:
    if input_file is None:
        entry = json.load(sys.stdin)
    else:
        entry = json.loads(input_file.read_text(encoding="utf-8"))
    print(record_entry(workspace, entry))


def cli_history_render(workspace: Path) -> None:
    print(render_history(workspace))


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
    history = commands.add_parser("history", help="record and render analysis history")
    actions = history.add_subparsers(required=True)
    record = actions.add_parser("record", help="save a JSON history entry")
    record.add_argument("--workspace", type=Path, required=True)
    record.add_argument("--input", type=Path, dest="input_file", help="JSON file (default: stdin)")
    record.set_defaults(func=cli_history_record)
    render = actions.add_parser("render", help="generate 作業履歴.md from history entries")
    render.add_argument("--workspace", type=Path, required=True)
    render.set_defaults(func=cli_history_render)
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
