import json

import pytest

from inquiry_lab.cli import main


def test_flat_values_and_nested_summaries_are_read_only(tmp_path, capsys):
    path = tmp_path / "config.json"
    source = {
        "rounds": 2000,
        "rate": 0.05,
        "enabled": True,
        "missing": None,
        "name": "日本語\n設定",
        "model": {"hidden": "nested value"},
        "scores": [1, 2],
    }
    path.write_text(json.dumps(source, ensure_ascii=False), encoding="utf-8-sig")
    before = path.read_bytes()

    assert main(["json", "inspect", str(path)]) == 0
    output = capsys.readouterr()
    assert output.err == ""
    assert output.out == (
        'TYPE object; keys: 7\n"rounds": 2000\n"rate": 0.05\n"enabled": true\n'
        '"missing": null\n"name": "日本語\\n設定"\n'
        '"model": <object: 1 keys>\n"scores": <array: 2 items>\n'
    )
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "options",
    [
        ["--key", "model.params"],
        ["--key", "model", "--key", "params"],
    ],
)
def test_dotted_and_repeated_keys_select_the_same_level(tmp_path, capsys, options):
    path = tmp_path / "config.json"
    path.write_text('{"model": {"params": {"rounds": 2000}}}')
    assert main(["json", "inspect", str(path), *options]) == 0
    assert capsys.readouterr().out == 'TYPE object; keys: 1\n"rounds": 2000\n'


def test_array_selection_and_mixed_path(tmp_path, capsys):
    path = tmp_path / "data.json"
    path.write_text('[{"metrics": {"auc": 0.8}}, null, [1, 2]]')
    assert main(["json", "inspect", str(path)]) == 0
    assert capsys.readouterr().out == (
        "TYPE array; items: 3\n[0]: <object: 1 keys>\n[1]: null\n[2]: <array: 2 items>\n"
    )
    assert main(["json", "inspect", str(path), "--key", "0.metrics", "--key", "auc"]) == 0
    assert capsys.readouterr().out == "0.8\n"


@pytest.mark.parametrize("source", ['{"a": 1, "b": 2}', "[1, 2]"])
def test_entry_limits_report_omissions(tmp_path, capsys, source):
    path = tmp_path / "data.json"
    path.write_text(source)
    assert main(["json", "inspect", str(path), "--head", "1"]) == 0
    output = capsys.readouterr().out
    assert output.splitlines()[1].endswith(": 1")
    assert len(output.splitlines()) == 3
    assert "OMITTED 1 entries" in output
    assert main(["json", "inspect", str(path), "--head", "0"]) == 0
    assert "OMITTED 2 entries" in capsys.readouterr().out


def test_long_scalar_is_explicitly_truncated(tmp_path, capsys):
    path = tmp_path / "data.json"
    path.write_text(json.dumps("x" * 1000))
    assert main(["json", "inspect", str(path)]) == 0
    output = capsys.readouterr().out
    assert "[truncated]" in output
    assert len(output) < 200


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ('{"a.b": 1, "a": {"b": 2}}', "containing '.'"),
        ('{"ok": 1, "other": [{"a.b": 2}]}', "containing '.'"),
        ('{"a": 1, "a": 2}', "duplicate JSON key"),
        ("{", "Expecting"),
        ("NaN", "invalid JSON constant"),
    ],
)
def test_invalid_documents_fail_without_partial_output(tmp_path, capsys, source, message):
    path = tmp_path / "data.json"
    path.write_text(source)
    assert main(["json", "inspect", str(path)]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err


@pytest.mark.parametrize(
    ("options", "message"),
    [
        (["--key", "missing"], "key not found"),
        (["--key", "scalar.child"], "scalar JSON value"),
        (["--key", "items.1"], "index out of range"),
        (["--key", "items.name"], "non-negative array index"),
        (["--key", "scalar..child"], "non-empty"),
        (["--key", ""], "non-empty"),
        (["--head", "-1"], "non-negative"),
    ],
)
def test_invalid_selection_is_an_argument_error(tmp_path, capsys, options, message):
    path = tmp_path / "data.json"
    path.write_text('{"scalar": 1, "items": [0]}')
    with pytest.raises(SystemExit) as error:
        main(["json", "inspect", str(path), *options])
    assert error.value.code == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err


def test_missing_file_is_an_io_error(tmp_path, capsys):
    assert main(["json", "inspect", str(tmp_path / "missing.json")]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "No such file" in output.err
