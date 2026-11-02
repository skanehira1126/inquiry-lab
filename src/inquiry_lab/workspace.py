import shutil
from datetime import date
from importlib.resources import files
from pathlib import Path
from string import Template


def initialize_workspace(directory: Path, title: str) -> Path:
    """Expand prose templates into a new directory; refuse any existing destination."""
    title = title.strip()
    if not title or len(title.splitlines()) != 1:
        raise ValueError("title must be a non-empty single line")

    templates = files("inquiry_lab").joinpath("templates")
    contents = {
        destination: Template(templates.joinpath(source).read_text(encoding="utf-8")).substitute(
            title=title, created_date=date.today().isoformat()
        )
        for source, destination in (
            ("initial-request.md", "requests/001-initial.md"),
            ("result.md", "runs/001/result.md"),
            ("output.md", "output.md"),
        )
    }

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
