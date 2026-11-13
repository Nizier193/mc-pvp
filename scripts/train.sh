#!/usr/bin/env bash
# Обучение. Запуск: bash scripts/train.sh [config.yaml]
set -e
cd "$(dirname "$0")/.."
CONFIG="${1:-configs/train.yaml}"
.venv/bin/python rl/train.py --config "$CONFIG"
