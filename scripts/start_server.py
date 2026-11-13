"""Запустить сервер Minecraft 1.8.9 и дождаться готовности RCON.

Запуск:  python scripts/start_server.py [instance_id]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import shutil
import subprocess
import time

from env.config import ROOT, SERVER_DIR, load_config, ports_for
from env.rcon import RCON


def ensure_runtime_files(root, cfg, ports):
    SERVER_DIR.mkdir(exist_ok=True)

    eula = SERVER_DIR / "eula.txt"
    if not eula.exists():
        # ВНИМАНИЕ: eula=true означает принятие пользовательского соглашения Mojang.
        eula.write_text("eula=true\n", encoding="utf-8")
        print("[warn] создан eula.txt (eula=true) — это принятие EULA Mojang")

    tmpl = (root / "config" / "server.properties.template").read_text(encoding="utf-8")
    props = (
        tmpl.replace("{PORT}", str(ports["port"]))
        .replace("{RCON_PORT}", str(ports["rcon_port"]))
        .replace("{RCON_PASSWORD}", cfg["server"]["rcon_password"])
        .replace("{LEVEL_NAME}", ports["level_name"])
    )
    (SERVER_DIR / "server.properties").write_text(props, encoding="utf-8")


def start(root, cfg, instance_id=0):
    ports = ports_for(cfg, instance_id)
    ensure_runtime_files(root, cfg, ports)

    jar = SERVER_DIR / "server.jar"
    if not jar.exists():
        raise FileNotFoundError(f"{jar} отсутствует. Сначала: python scripts/download_server.py")

    java = shutil.which("java") or "java"
    mem = cfg["server"].get("memory", "1G")
    # свежий мир каждый запуск (иначе остаются устаревшие точки спавна ботов)
    world = SERVER_DIR / ports["level_name"]
    if world.exists():
        shutil.rmtree(world, ignore_errors=True)
    log = open(SERVER_DIR / f"server_{instance_id}.log", "wb")
    cmd = [java, "-Xms512M", f"-Xmx{mem}", "-jar", str(jar), "nogui"]
    proc = subprocess.Popen(cmd, cwd=str(SERVER_DIR), stdout=log, stderr=subprocess.STDOUT)
    print(f"[server] pid={proc.pid} порт={ports['port']} rcon={ports['rcon_port']} лог=server_{instance_id}.log")
    return proc, ports


def wait_ready(cfg, ports, timeout=180.0, proc=None):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc is not None and proc.poll() is not None:
            raise RuntimeError(
                f"сервер завершился (exit={proc.returncode}). Смотри server/*.log — "
                f"вероятно, версия Java несовместима с 1.8.9 (нужна Java 8 или 17)."
            )
        try:
            rcon = RCON(ports["host"], ports["rcon_port"], cfg["server"]["rcon_password"])
            rcon.close()
            return True
        except Exception as e:  # connection refused, пока сервер грузится
            last = e
            time.sleep(2.0)
    raise TimeoutError(f"сервер не поднялся за {timeout}s: {last}")


if __name__ == "__main__":
    cfg = load_config()
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    proc, ports = start(ROOT, cfg, iid)
    try:
        wait_ready(cfg, ports)
        print("[server] READY. Ctrl+C для остановки.")
        proc.wait()
    except KeyboardInterrupt:
        print("[server] остановка...")
    finally:
        proc.terminate()
