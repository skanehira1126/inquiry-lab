"""Manage one worker's current assignment in a shared inquiry tree."""

from pathlib import Path
from tempfile import TemporaryDirectory

from filelock import FileLock
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from inquiry_lab.json_parsing import parse_json
from inquiry_lab.tree_map import load_tree


class WorkerState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    tree_path: str = Field(min_length=1)
    hypothesis_id: str


def _state_path(path: Path) -> Path:
    # Keep the final component so a symlink cannot redirect an update or finish.
    return path.parent.resolve() / path.name


def _read_state(path: Path) -> WorkerState:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Expected a regular worker state file: {path}")
    return WorkerState.model_validate(parse_json(path.read_text(encoding="utf-8-sig")))


def _write_state(path: Path, assignment: WorkerState) -> None:
    with TemporaryDirectory(dir=path.parent, prefix=".state-") as temporary:
        staged = Path(temporary) / "state.json"
        staged.write_text(assignment.model_dump_json(indent=2) + "\n", encoding="utf-8")
        if path.is_file():
            staged.chmod(path.stat().st_mode & 0o777)
        staged.replace(path)


def _state_lock(path: Path) -> FileLock:
    if not path.parent.is_dir():
        raise FileNotFoundError(f"Worker directory does not exist: {path.parent}")
    return FileLock(path.with_name(f".{path.name}.lock"))


def start_state(path: Path, tree_path: Path, hypothesis_id: str) -> Path:
    path = _state_path(path)
    tree_path = tree_path.resolve(strict=True)
    load_tree(tree_path).get_hypothesis(hypothesis_id)
    try:
        reference = tree_path.relative_to(path.parent, walk_up=True)
    except ValueError:
        # Windows paths on separate drives need an absolute reference.
        reference = tree_path
    assignment = WorkerState(tree_path=str(reference), hypothesis_id=hypothesis_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _state_lock(path):
        if path.is_symlink() or path.exists():
            raise FileExistsError(f"Worker state destination already exists: {path}")
        _write_state(path, assignment)
    return path


def show_state(path: Path) -> dict:
    path = _state_path(path)
    assignment = _read_state(path)
    tree_path = (path.parent / assignment.tree_path).resolve(strict=True)
    return load_tree(tree_path).status(tree_path, assignment.hypothesis_id)


def update_state(path: Path, hypothesis_id: str) -> Path:
    path = _state_path(path)
    with _state_lock(path):
        assignment = _read_state(path)
        load_tree(path.parent / assignment.tree_path).get_hypothesis(hypothesis_id)
        assignment.hypothesis_id = hypothesis_id
        _write_state(path, assignment)
    return path


def finish_state(path: Path) -> Path:
    path = _state_path(path)
    with _state_lock(path):
        _read_state(path)
        path.unlink()
    return path
