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
if command -v apt-get >/dev/null 2>&1; then
  # без python3-venv команда `python3 -m venv` падает на ensurepip (классика Ubuntu/Colab)
  apt-get install -y python3-venv python3-pip || true
fi

# На Colab `python3` часто указывает на managed-интерпретатор с битым ensurepip.
# Берём системный /usr/bin/python3, для которого python3-venv даёт рабочий venv.
PYBASE=""
for c in /usr/bin/python3 python3; do
  if command -v "$c" >/dev/null 2>&1; then PYBASE="$c"; break; fi
done
echo "используем python: $PYBASE"

rm -rf .venv
if "$PYBASE" -m venv .venv; then
  .venv/bin/python -m pip install -U pip
  .venv/bin/python -m pip install -r requirements.txt
else
  echo "!! venv не создался — ставлю зависимости глобально"
  "$PYBASE" -m pip install --break-system-packages -r requirements.txt
fi

echo "==> Node-зависимости"
npm install

echo "==> Minecraft server"
.venv/bin/python scripts/download_server.py

echo "==> Готово. Дальше:  bash scripts/train.sh configs/train.yaml"
