"""Запустить одну полную сессию: сервер + арена + боты + демо-цикл.

Примеры:
  python scripts/run_arena.py                    # инстанс 0, 15 шагов
  python scripts/run_arena.py --instance-id 1    # другие порты/мир
  python scripts/run_arena.py --steps 40
  python scripts/run_arena.py --skip-server      # сервер уже запущен
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import random
import time

from env.arena_env import ArenaEnv
from env.config import load_config, ports_for
from scripts import download_server, setup_arena, start_server


def random_action():
    return {
        "forward": random.random() < 0.35,
        "back": random.random() < 0.10,
        "left": random.random() < 0.15,
        "right": random.random() < 0.15,
        "jump": random.random() < 0.12,
        "sprint": random.random() < 0.30,
        "sneak": False,
        "yaw": random.uniform(-3.1415, 3.1415),
        "pitch": 0.0,
        "attack": random.random() < 0.40,
        "use": random.random() < 0.10,
        "slot": random.choice([0, 1, 2]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance-id", type=int, default=0)
    ap.add_argument("--steps", type=int, default=15)
    ap.add_argument("--skip-server", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    ports = ports_for(cfg, args.instance_id)
    server_proc = None

    try:
        if not args.skip_server:
            if not (start_server.SERVER_DIR / "server.jar").exists():
                download_server.main()
            server_proc, _ = start_server.start(start_server.ROOT, cfg, args.instance_id)
            start_server.wait_ready(cfg, ports, proc=server_proc)

        env = ArenaEnv(cfg, instance_id=args.instance_id)
        env.spawn_bots()
        env.wait_bots_ready()

        if not args.skip_server:
            # 1) телепорт ботов в зону арены на безопасной высоте -> грузит чанки,
            #    иначе /fill вернёт «Cannot place blocks outside of the world».
            env.teleport_to_spawns(y=5)
            time.sleep(1.5)
            # 2) строим арену
            setup_arena.build_arena(cfg, ports)

        # 3) телепорт в углы + предметы + синхронизация
        obs, events, dones = env.reset()
        agents = env.agent_names()
        print(f"\n=== демо ({len(agents)} агент(а), {args.steps} шагов, случайные действия) ===")
        for step in range(args.steps):
            actions = {n: random_action() for n in agents}
            obs, events, dones = env.step(actions)
            for n in agents:
                o = obs.get(n) or {}
                s = o.get("self", {}) or {}
                e = o.get("enemy", {}) or {}
                inv = o.get("inventory", {}) or {}
                dbg = o.get("debug", {}) or {}
                print(
                    f"step={step:3d} {n}: pos=({s.get('x')},{s.get('y')},{s.get('z')}) hp={s.get('health')} "
                    f"enemy={e.get('exists')} dist={e.get('dist')} "
                    f"inv(w/c/s)={inv.get('wool')}/{inv.get('cobweb')}/{inv.get('sword')} "
                    f"players={dbg.get('players')} entities={dbg.get('entities')}"
                )
            time.sleep(0.05)
        print("=== демо завершено ===")
        env.close()
    finally:
        if server_proc is not None:
            print("[cleanup] останавливаю сервер...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except Exception:
                server_proc.kill()


if __name__ == "__main__":
    main()
