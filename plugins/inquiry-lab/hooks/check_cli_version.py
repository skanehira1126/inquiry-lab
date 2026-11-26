import json
from pathlib import Path
import re
import shutil
import subprocess


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    expected = json.loads((root / ".codex-plugin/plugin.json").read_text(encoding="utf-8"))[
        "version"
    ]
    cli = shutil.which("inquiry-lab")
    if cli is None:
        detail = "PATH 上に CLI が見つかりません。"
    else:
        detail = f"{cli} の版を取得できません。"
        try:
            result = subprocess.run(
                [cli, "--version"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=True,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        else:
            match = re.fullmatch(rb"inquiry-lab ([A-Za-z0-9.+!-]+)", result.stdout.strip())
            if match:
                actual = match[1].decode("ascii")
                if actual == expected:
                    return
                detail = f"PATH 上の CLI は {actual} ({cli}) です。"

    message = (
        f"inquiry-lab プラグインは {expected} です。{detail} "
        "CLI を使う場合は同じ版を導入してください。"
    )
    print(json.dumps({"systemMessage": message}))


if __name__ == "__main__":
    main()
