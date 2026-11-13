#!/usr/bin/env bash
# Удобный запуск из корня проекта (Linux/Colab):  ./scripts/run.sh [--steps N]
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="$DIR/../.venv/bin/python"
[ -x "$PY" ] || PY="python"
exec "$PY" "$DIR/run_arena.py" "$@"
