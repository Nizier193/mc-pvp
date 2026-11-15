#!/usr/bin/env bash
# Обучение. Запуск: bash scripts/train.sh [config.yaml]
set -e
cd "$(dirname "$0")/.."
CONFIG="${1:-configs/train.yaml}"
if [ -x .venv/bin/python ] && .venv/bin/python -c "import numpy" 2>/dev/null; then
  PY=.venv/bin/python
elif [ -x /usr/bin/python3 ] && /usr/bin/python3 -c "import numpy" 2>/dev/null; then
  PY=/usr/bin/python3
else
  PY=python3
fi
"$PY" rl/train.py --config "$CONFIG"
