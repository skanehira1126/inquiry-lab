from pathlib import Path

import pytest

from inquiry_lab.cli import main


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
