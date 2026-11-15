#!/usr/bin/env bash
# Обучение. Запуск: bash scripts/train.sh [config.yaml]
set -e
ORIG_PWD="$(pwd)"
cd "$(dirname "$0")/.."
CONFIG="${1:-configs/train.yaml}"
# если передан путь относительно ноутбука (mc-pvp/...), а мы уже в mc-pvp — разрешаем его
if [ ! -f "$CONFIG" ] && [ -f "$ORIG_PWD/$CONFIG" ]; then
  CONFIG="$ORIG_PWD/$CONFIG"
fi
if [ -x .venv/bin/python ] && .venv/bin/python -c "import numpy" 2>/dev/null; then
  PY=.venv/bin/python
elif [ -x /usr/bin/python3 ] && /usr/bin/python3 -c "import numpy" 2>/dev/null; then
  PY=/usr/bin/python3
else
  PY=python3
fi
"$PY" rl/train.py --config "$CONFIG"
