import os
import shutil
from datetime import date
from importlib.resources import files
from pathlib import Path
from string import Template
from urllib.parse import quote


def validate_title(title: str) -> str:
    title = title.strip()
    if not title or len(title.splitlines()) != 1:
        raise ValueError("title must be a non-empty single line")
    return title


def render_run(title: str, number: int, request_link: str, template: str) -> str:
    sources = {"default": "result.md", "eda": "eda-result.md"}
    if template not in sources:
        raise ValueError(f"unknown run template: {template}")
    source = files("inquiry_lab").joinpath("templates", sources[template])
    return Template(source.read_text(encoding="utf-8")).substitute(
        title=title, run_id=f"run-{number:03d}", request_link=request_link
    )


def initialize_workspace(directory: Path, title: str, template: str = "default") -> Path:
    """Expand prose templates into a new directory; refuse any existing destination."""
    title = validate_title(title)

    templates = files("inquiry_lab").joinpath("templates")
    contents = {
        destination: Template(templates.joinpath(source).read_text(encoding="utf-8")).substitute(
            title=title, created_date=date.today().isoformat()
        )
        for source, destination in (
            ("initial-request.md", "requests/001-initial.md"),
            ("output.md", "output.md"),
        )
    }
    contents["runs/001/result.md"] = render_run(
        title, 1, "../../requests/001-initial.md", template
    )

    directory = directory.expanduser().absolute()
    # mkdir reserves the destination without following or replacing an existing final symlink.
    directory.mkdir(parents=True)
    try:
        for relative_path, content in contents.items():
            path = directory / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        (directory / "runs/001/artifacts").mkdir()
        (directory / "report").mkdir()
    except OSError:
        shutil.rmtree(directory)
        raise
    return directory


def create_run(
    workspace: Path,
    title: str,
    request: Path = Path("requests/001-initial.md"),
    template: str = "default",
) -> Path:
    """Reserve the next run number and expand its template without replacing existing paths."""
    title = validate_title(title)
    workspace = workspace.expanduser().absolute()
    runs = workspace / "runs"
    if runs.is_symlink() or not runs.is_dir():
        raise ValueError(f"runs must be an existing directory, not a symlink: {runs}")
    request = request.expanduser()
    if not request.is_absolute():
        request = workspace / request
    if not request.is_file():
        raise ValueError(f"request is not a file: {request}")
    number = (
        max(
            (
                int(path.name)
                for path in runs.iterdir()
                if path.name.isascii() and path.name.isdecimal()
            ),
            default=0,
        )
        + 1
    )
    while True:
        directory = runs / f"{number:03d}"
        request_link = quote(Path(os.path.relpath(request, directory)).as_posix(), safe="/.")
        content = render_run(title, number, request_link, template)
        try:
            # mkdir reserves the number even when another writer read the same maximum.
            directory.mkdir()
        except FileExistsError:
            number += 1
            continue
        break

    try:
        (directory / "result.md").write_text(content, encoding="utf-8")
        (directory / "artifacts").mkdir()
    except OSError:
        shutil.rmtree(directory)
        raise
    return directory
