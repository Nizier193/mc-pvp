#!/usr/bin/env bash
# Инференс + гифка боя. Запуск: bash scripts/eval.sh [config.yaml] <model.zip>
set -e
cd "$(dirname "$0")/.."
CONFIG="${1:-configs/train.yaml}"
MODEL="${2:?usage: eval.sh <config.yaml> <model.zip>}"
.venv/bin/python rl/eval.py --config "$CONFIG" --model "$MODEL"
