#!/usr/bin/env bash
# Настройка окружения (Google Colab / Linux). Запуск: bash scripts/setup.sh
set -e
cd "$(dirname "$0")/.."

echo "==> системные пакеты (Java, Node, ImageMagick)"
if command -v apt-get >/dev/null 2>&1; then
  apt-get update -y
  (apt-get install -y openjdk-8-jdk-headless || apt-get install -y openjdk-11-jdk-headless) || true
  apt-get install -y imagemagick curl || true
fi

echo "==> Node.js"
if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi

echo "==> Python-окружение"
python3 -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt

echo "==> Node-зависимости"
npm install

echo "==> Minecraft server"
.venv/bin/python scripts/download_server.py

echo "==> Готово. Дальше:  bash scripts/train.sh configs/train.yaml"
