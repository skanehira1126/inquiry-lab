from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import unquote

import pytest

from inquiry_lab.cli import main
from inquiry_lab.workspace import create_run


def test_init_expands_analysis_documents_without_execution_files(tmp_path, capsys):
    destination = tmp_path / "analyses" / "売上 分析"
    title = "売上の変化 ${created_date} {{TITLE}}"

    assert main(["init", str(destination), "--title", title]) == 0

    output = capsys.readouterr()
    assert output.out.strip() == str(destination)
    assert output.err == ""
    assert {str(path.relative_to(destination)) for path in destination.rglob("*")} == {
        "requests",
        "requests/001-initial.md",
        "runs",
        "runs/001",
        "runs/001/result.md",
        "runs/001/artifacts",
        "report",
        "output.md",
    }
    request = (destination / "requests/001-initial.md").read_text(encoding="utf-8")
    result = (destination / "runs/001/result.md").read_text(encoding="utf-8")
    report = (destination / "output.md").read_text(encoding="utf-8")
    assert f"# {title}\n" in request
    assert f"# Run result: {title}\n" in result
    assert f"# {title}\n" in report
    assert "## Acceptance criteria" in request
    assert "- Created: ${created_date}" not in request
    assert "## Data quality and timing" in result
    assert "## Current conclusions" in report
    assert (destination / "runs/001" / "../../requests/001-initial.md").is_file()
    for document in (request, result, report):
        assert "notebook-workbench:required" not in document
        assert "run.yaml" not in document
        assert ".ipynb" not in document
        assert "accepted" not in document.lower()


@pytest.mark.parametrize("kind", ["empty", "populated", "file", "symlink", "dangling"])
def test_init_refuses_existing_destination_without_changing_it(tmp_path, capsys, kind):
    destination = tmp_path / "analysis"
    target = tmp_path / "target"
    if kind in {"empty", "populated"}:
        destination.mkdir()
        if kind == "populated":
            (destination / "output.md").write_bytes(b"existing report")
    elif kind == "file":
        destination.write_bytes(b"existing file")
    else:
        if kind == "symlink":
            target.mkdir()
            (target / "output.md").write_bytes(b"linked report")
        destination.symlink_to(target, target_is_directory=True)

    before = {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert main(["init", str(destination), "--title", "Example"]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "inquiry-lab:" in output.err
    assert "Traceback" not in output.err
    assert before == {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    if kind in {"symlink", "dangling"}:
        assert destination.is_symlink()
        assert destination.readlink() == target
    if kind == "dangling":
        assert not target.exists()
    if kind == "empty":
        assert list(destination.iterdir()) == []


@pytest.mark.parametrize("title", ["   ", "first\nsecond", "first\rsecond"])
def test_init_rejects_invalid_title_before_creating_directories(tmp_path, capsys, title):
    destination = tmp_path / "parent" / "analysis"
    assert main(["init", str(destination), "--title", title]) == 1
    assert not destination.parent.exists()
    assert "title" in capsys.readouterr().err


def test_init_removes_partial_workspace_after_write_failure(tmp_path, monkeypatch, capsys):
    destination = tmp_path / "analysis"
    unrelated = tmp_path / "keep.txt"
    unrelated.write_bytes(b"keep")
    original_write_text = Path.write_text

    def fail_result_write(path, *args, **kwargs):
        if path.name == "result.md":
            raise OSError("disk full")
        return original_write_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_result_write)
    assert main(["init", str(destination), "--title", "Example"]) == 1
    assert not destination.exists()
    assert unrelated.read_bytes() == b"keep"
    output = capsys.readouterr()
    assert output.out == ""
    assert "disk full" in output.err


@pytest.mark.parametrize("args", [[], ["init", "unused"], ["unknown"]])
def test_cli_reports_argument_errors(args, capsys):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_init_selects_eda_template_for_first_run(tmp_path, capsys):
    destination = tmp_path / "eda"
    title = "EDA ${title}"
    assert main(["init", str(destination), "--title", title, "--template", "eda"]) == 0
    assert capsys.readouterr().out.strip() == str(destination)
    result = (destination / "runs/001/result.md").read_text(encoding="utf-8")
    assert result.startswith(f"# {title}\n")
    assert "## 1. 今回の観察の位置づけ" in result
    assert "## 付録. 作業記録" in result
    assert "`run-001`" in result
    assert "../../requests/001-initial.md" in result
    assert "${request_link}" not in result
    assert "## Current conclusions" in (destination / "output.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("template", ["default", "eda"])
def test_run_new_adds_template_without_changing_workspace(tmp_path, capsys, template):
    destination = tmp_path / "analysis"
    assert main(["init", str(destination), "--title", "Initial"]) == 0
    before = {path: path.read_bytes() for path in destination.rglob("*") if path.is_file()}
    capsys.readouterr()

    assert (
        main(
            [
                "run",
                "new",
                "--workspace",
                str(destination),
                "--title",
                "  Follow-up  ",
                "--template",
                template,
            ]
        )
        == 0
    )

    run = destination / "runs/002"
    assert capsys.readouterr().out.strip() == str(run)
    assert {path.name for path in run.iterdir()} == {"result.md", "artifacts"}
    result = (run / "result.md").read_text(encoding="utf-8")
    assert "Follow-up\n" in result
    assert "`run-002`" in result and "run-001" not in result
    assert "../../requests/001-initial.md" in result
    assert ("## 1. 今回の観察の位置づけ" in result) == (template == "eda")
    assert all(path.read_bytes() == content for path, content in before.items())
    assert not (destination / "history").exists()


@pytest.mark.parametrize("absolute", [False, True])
def test_run_request_link_resolves_from_run_not_cwd(tmp_path, absolute):
    destination = tmp_path / "analysis"
    assert main(["init", str(destination), "--title", "Initial"]) == 0
    (destination / "runs/999").mkdir()
    request = destination / "requests/追加 (条件)#1.md"
    request.write_text("# Follow-up", encoding="utf-8")
    argument = request if absolute else request.relative_to(destination)
    assert (
        main(
            [
                "run",
                "new",
                "--workspace",
                str(destination),
                "--title",
                "Follow-up",
                "--request",
                str(argument),
            ]
        )
        == 0
    )
    run = destination / "runs/1000"
    result = (run / "result.md").read_text(encoding="utf-8")
    link = result.split("[request](<", 1)[1].split(">)", 1)[0]
    assert (run / unquote(link)).resolve() == request
    assert "%23" in link and "%20" in link
    assert "`run-1000`" in result


@pytest.mark.parametrize("kind", ["empty", "populated", "file", "symlink", "dangling"])
def test_run_new_skips_existing_paths_without_changing_them(tmp_path, kind):
    workspace = tmp_path / "analysis"
    assert main(["init", str(workspace), "--title", "Initial"]) == 0
    run = workspace / "runs/003"
    target = tmp_path / "target"
    if kind in {"empty", "populated"}:
        run.mkdir()
        if kind == "populated":
            (run / "result.md").write_bytes(b"existing result")
    elif kind == "file":
        run.write_bytes(b"existing file")
    else:
        if kind == "symlink":
            target.mkdir()
            (target / "result.md").write_bytes(b"linked result")
        run.symlink_to(target, target_is_directory=True)
    before = {path: path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert main(["run", "new", "--workspace", str(workspace), "--title", "New"]) == 0
    assert (workspace / "runs/004/result.md").is_file()
    assert not (workspace / "runs/002").exists()
    assert all(path.read_bytes() == content for path, content in before.items())
    if kind in {"symlink", "dangling"}:
        assert run.is_symlink() and run.readlink() == target
    if kind == "dangling":
        assert not target.exists()
    if kind == "empty":
        assert list(run.iterdir()) == []


@pytest.mark.parametrize(
    "title,request_path",
    [
        (" \n ", "requests/001-initial.md"),
        ("First\nSecond", "requests/001-initial.md"),
        ("Valid", "requests/missing.md"),
    ],
)
def test_run_new_invalid_input_leaves_workspace_unchanged(tmp_path, title, request_path):
    assert main(["init", str(tmp_path / "analysis"), "--title", "Initial"]) == 0
    workspace = tmp_path / "analysis"
    before = set(workspace.rglob("*"))
    assert (
        main(
            [
                "run",
                "new",
                "--workspace",
                str(workspace),
                "--title",
                title,
                "--request",
                request_path,
            ]
        )
        == 1
    )
    assert set(workspace.rglob("*")) == before


@pytest.mark.parametrize("kind", ["missing", "symlink"])
def test_run_new_requires_existing_runs_directory(tmp_path, kind):
    workspace = tmp_path / "analysis"
    workspace.mkdir()
    request = tmp_path / "request.md"
    request.write_text("# Request", encoding="utf-8")
    target = tmp_path / "other-runs"
    target.mkdir()
    if kind == "symlink":
        (workspace / "runs").symlink_to(target, target_is_directory=True)
    assert (
        main(
            [
                "run",
                "new",
                "--workspace",
                str(workspace),
                "--title",
                "New",
                "--request",
                str(request),
            ]
        )
        == 1
    )
    assert not (workspace / "runs/002").exists()
    assert list(target.iterdir()) == []


def test_run_new_cleans_up_only_new_run_on_write_failure(tmp_path, monkeypatch, capsys):
    workspace = tmp_path / "analysis"
    assert main(["init", str(workspace), "--title", "Initial"]) == 0
    before = {path: path.read_bytes() for path in workspace.rglob("*") if path.is_file()}
    original_mkdir = Path.mkdir

    def fail_artifacts(path, *args, **kwargs):
        if path == workspace / "runs/002/artifacts":
            raise OSError("disk full")
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", fail_artifacts)
    capsys.readouterr()
    assert main(["run", "new", "--workspace", str(workspace), "--title", "New"]) == 1
    assert not (workspace / "runs/002").exists()
    assert all(path.read_bytes() == content for path, content in before.items())
    output = capsys.readouterr()
    assert output.out == "" and "disk full" in output.err


@pytest.mark.parametrize(
    "args",
    [
        ["run"],
        ["run", "new"],
        ["run", "new", "2", "--workspace", ".", "--title", "New"],
        ["init", "unused", "--title", "New", "--template", "unknown"],
    ],
)
def test_run_template_cli_argument_errors(args, capsys):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert "usage:" in capsys.readouterr().err


def test_packaged_eda_template_matches_skill_asset():
    root = Path(__file__).resolve().parents[1]
    assert (root / "src/inquiry_lab/templates/eda-result.md").read_bytes() == (
        root / "skills/eda/assets/result.md"
    ).read_bytes()


def test_run_new_starts_at_one_and_ignores_nonnumeric_names(tmp_path, capsys):
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs/notes").mkdir()
    (tmp_path / "runs/999-backup").mkdir()
    request = tmp_path / "request.md"
    request.write_text("# Request", encoding="utf-8")
    assert (
        main(
            [
                "run",
                "new",
                "--workspace",
                str(tmp_path),
                "--title",
                "First",
                "--request",
                str(request),
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.strip() == str(tmp_path / "runs/001")
    assert "`run-001`" in (tmp_path / "runs/001/result.md").read_text(encoding="utf-8")


def test_concurrent_run_creation_reserves_distinct_numbers(tmp_path, monkeypatch):
    workspace = tmp_path / "analysis"
    assert main(["init", str(workspace), "--title", "Initial"]) == 0
    barrier = Barrier(4)
    original_mkdir = Path.mkdir

    def simultaneous_mkdir(path, *args, **kwargs):
        if path == workspace / "runs/002":
            barrier.wait(timeout=5)
        return original_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", simultaneous_mkdir)
    titles = [f"Observation {index}" for index in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(
            pool.map(lambda title: create_run(workspace, title, template="eda"), titles)
        )

    assert {path.name for path in results} == {"002", "003", "004", "005"}
    for path, title in zip(results, titles, strict=True):
        content = (path / "result.md").read_text(encoding="utf-8")
        assert content.startswith(f"# {title}\n")
        assert f"`run-{path.name}`" in content
        assert (path / "artifacts").is_dir()
    assert (
        (workspace / "runs/001/result.md")
        .read_text(encoding="utf-8")
        .startswith("# Run result: Initial\n")
    )
