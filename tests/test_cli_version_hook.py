import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.mark.skipif(os.name != "posix", reason="the fixture uses a POSIX executable")
@pytest.mark.parametrize(
    ("cli_output", "warning"),
    [
        ("inquiry-lab 2.1.0", None),
        ("inquiry-lab 2.0.0", "2.0.0"),
        (None, "PATH 上に CLI が見つかりません"),
        ("unknown", "版を取得できません"),
    ],
)
def test_version_check(tmp_path, cli_output, warning):
    root = tmp_path / "plugin cache"
    (root / "hooks").mkdir(parents=True)
    (root / ".codex-plugin").mkdir()
    (root / ".codex-plugin/plugin.json").write_text('{"version":"2.1.0"}')
    script = Path(__file__).resolve().parents[1] / "plugins/inquiry-lab/hooks/check_cli_version.py"
    installed = root / "hooks" / script.name
    installed.write_bytes(script.read_bytes())
    if cli_output is not None:
        cli = tmp_path / "inquiry-lab"
        cli.write_text(f'#!/bin/sh\n[ "$*" = --version ] && echo "{cli_output}"\n')
        cli.chmod(0o755)
    result = subprocess.run(
        [sys.executable, "-I", "-S", installed],
        cwd=tmp_path,
        env={**os.environ, "PATH": str(tmp_path)},
        capture_output=True,
        text=True,
        check=True,
    )
    if warning is None:
        assert result.stdout == ""
    else:
        message = json.loads(result.stdout)["systemMessage"]
        assert warning in message
        assert "2.1.0" in message
