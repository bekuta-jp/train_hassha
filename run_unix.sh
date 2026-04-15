#!/usr/bin/env sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PYTHON_BIN="$ROOT_DIR/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  echo ".venv が見つかりません。先に python3 -m venv .venv を実行してください。"
  exit 1
fi

exec "$PYTHON_BIN" "$ROOT_DIR/main.py" "$@"
