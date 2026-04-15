from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent


def pyinstaller_path() -> Path:
    if sys.platform == "win32":
        return ROOT / ".venv" / "Scripts" / "pyinstaller.exe"
    return ROOT / ".venv" / "bin" / "pyinstaller"


def main() -> int:
    executable = pyinstaller_path()
    if not executable.exists():
        print("PyInstaller が見つかりません。.venv に requirements.txt をインストールしてください。")
        return 1

    mode_flag = "--onedir" if sys.platform == "darwin" else "--onefile"
    command = [str(executable), "--noconfirm", "--clean", mode_flag, "--windowed", "--name", "train-hassha", str(ROOT / "main.py")]

    environment = os.environ.copy()
    environment["PYINSTALLER_CONFIG_DIR"] = str(ROOT / ".pyinstaller")

    subprocess.run(command, cwd=ROOT, check=True, env=environment)
    print(f"ビルド完了: {ROOT / 'dist'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
