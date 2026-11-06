import argparse
import json
import sys
from pathlib import Path

from inquiry_lab import __version__
from inquiry_lab.data import DataArgumentError, inspect_data, list_data_values, render_data_text
from inquiry_lab.history import record_entry, render_history
from inquiry_lab.workspace import create_run, initialize_workspace


def cli_init(directory: Path, title: str, template: str) -> None:
    path = initialize_workspace(directory, title, template)
    print(path)


def cli_run_new(workspace: Path, title: str, request: Path, template: str) -> None:
    print(create_run(workspace, title, request, template))


def cli_history_record(workspace: Path, input_file: Path | None) -> None:
    if input_file is None:
        entry = json.load(sys.stdin)
    else:
        entry = json.loads(input_file.read_text(encoding="utf-8"))
    print(record_entry(workspace, entry))


def cli_history_render(workspace: Path) -> None:
    print(render_history(workspace))


def cli_data_inspect(
    path: Path, columns: list[str] | None, head: int, null_counts: bool, as_json: bool
) -> None:
    result = inspect_data(path, columns=columns, head=head, null_counts=null_counts)
    print(
        json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)
        if as_json
        else render_data_text(result),
        end="\n" if as_json else "",
    )


def cli_data_values(
    path: Path, columns: list[str], by: list[str], limit: int, group_limit: int, as_json: bool
) -> None:
    result = list_data_values(path, columns=columns, by=by, limit=limit, group_limit=group_limit)
    print(
        json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2)
        if as_json
        else render_data_text(result),
        end="\n" if as_json else "",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inquiry-lab", description="Prepare analysis workspaces and inspect data."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(required=True)
    data = commands.add_parser("data", help="inspect CSV, TSV, or Parquet files (read-only)")
    data_actions = data.add_subparsers(required=True)
    inspect = data_actions.add_parser("inspect", help="show schema, row count, and preview")
    inspect.add_argument("path", type=Path)
    inspect.add_argument("--columns", nargs="+")
    inspect.add_argument("--head", type=int, default=5)
    inspect.add_argument(
        "--null-counts", action="store_true", help="scan selected columns for missing values"
    )
    inspect.add_argument("--json", dest="as_json", action="store_true")
    inspect.set_defaults(func=cli_data_inspect)
    values = data_actions.add_parser("values", help="count values across all rows")
    values.add_argument("path", type=Path)
    values.add_argument("--columns", nargs="+", required=True)
    values.add_argument("--by", nargs="+", default=[])
    values.add_argument(
        "--limit", type=int, default=10, help="maximum displayed values per column"
    )
    values.add_argument("--group-limit", type=int, default=20, help="maximum displayed groups")
    values.add_argument("--json", dest="as_json", action="store_true")
    values.set_defaults(func=cli_data_values)
    init = commands.add_parser("init", help="expand analysis templates into a new directory")
    init.add_argument("directory", type=Path, help="new workspace directory (must not exist)")
    init.add_argument("--title", required=True, help="single-line analysis title")
    init.add_argument("--template", choices=("default", "eda"), default="default")
    init.set_defaults(func=cli_init)
    run = commands.add_parser("run", help="prepare run documents")
    run_actions = run.add_subparsers(required=True)
    new = run_actions.add_parser("new", help="create the next numbered run without overwriting")
    new.add_argument("--workspace", type=Path, required=True)
    new.add_argument("--title", required=True, help="single-line run title")
    new.add_argument(
        "--request",
        type=Path,
        default=Path("requests/001-initial.md"),
        help="existing request document, relative to workspace or absolute",
    )
    new.add_argument("--template", choices=("default", "eda"), default="default")
    new.set_defaults(func=cli_run_new)
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
    parser = build_parser()
    args = vars(parser.parse_args(argv))
    func = args.pop("func")
    try:
        func(**args)
    except DataArgumentError as error:
        parser.error(str(error))
    except (OSError, ValueError) as error:
        print(f"inquiry-lab: {error}", file=sys.stderr)
        return 1
    return 0
