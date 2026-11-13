"""Скачать официальный сервер Minecraft 1.8.9 (server.jar) в server/.

Запуск:  python scripts/download_server.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import urllib.request

from env.config import SERVER_DIR, load_config

MANIFEST_URL = "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"


def main():
    cfg = load_config()
    version = cfg["server"].get("version", "1.8.9")
    SERVER_DIR.mkdir(exist_ok=True)
    dest = SERVER_DIR / "server.jar"

    if dest.exists():
        print(f"[ok] {dest} уже есть ({dest.stat().st_size} байт) — пропускаю.")
        return dest

    print("Получаю версионный манифест...")
    with urllib.request.urlopen(MANIFEST_URL, timeout=30) as r:
        manifest = json.load(r)

    entry = next((v for v in manifest["versions"] if v["id"] == version), None)
    if entry is None:
        raise SystemExit(f"Версия {version} не найдена в манифесте.")

    with urllib.request.urlopen(entry["url"], timeout=30) as r:
        meta = json.load(r)

    url = meta["downloads"]["server"]["url"]
    size = meta["downloads"]["server"]["size"]
    print(f"Скачиваю server {version} ({size} байт)...")
    urllib.request.urlretrieve(url, dest)
    print(f"[ok] сохранено: {dest} ({dest.stat().st_size} байт)")
    return dest


if __name__ == "__main__":
    main()
