#!/usr/bin/env bash
# Обучение. Запуск: bash scripts/train.sh [config.yaml]
set -e
cd "$(dirname "$0")/.."
CONFIG="${1:-configs/train.yaml}"
if [ -x .venv/bin/python ]; then PY=.venv/bin/python; else PY=python3; fi
"$PY" rl/train.py --config "$CONFIG"
