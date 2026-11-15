#!/usr/bin/env bash
# Инференс + гифка боя. Запуск: bash scripts/eval.sh [config.yaml] <model.zip>
set -e
cd "$(dirname "$0")/.."
CONFIG="${1:-configs/train.yaml}"
MODEL="${2:?usage: eval.sh <config.yaml> <model.zip>}"
if [ -x .venv/bin/python ] && .venv/bin/python -c "import numpy" 2>/dev/null; then
  PY=.venv/bin/python
elif [ -x /usr/bin/python3 ] && /usr/bin/python3 -c "import numpy" 2>/dev/null; then
  PY=/usr/bin/python3
else
  PY=python3
fi
"$PY" rl/eval.py --config "$CONFIG" --model "$MODEL"
