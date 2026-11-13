"""Записать один реальный эпизод (позиции игроков) в viz/episode.json.

Агент «блуждает» (случайные действия), dummy-соперник преследует и атакует.
Запуск:  python scripts/record_episode.py [--steps 150]
"""
import sys
import json
import random
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env.arena_env import ArenaEnv
from env.config import load_config, ports_for
from scripts import download_server, setup_arena, start_server

ROOT = Path(__file__).resolve().parent.parent
VIZ = ROOT / "viz"


def wander_action():
    return {
        "forward": random.random() < 0.70,
        "back": False,
        "left": random.random() < 0.15,
        "right": random.random() < 0.15,
        "jump": random.random() < 0.08,
        "sprint": random.random() < 0.30,
        "sneak": False,
        "yaw": random.uniform(-3.1415, 3.1415),
        "pitch": 0.0,
        "attack": random.random() < 0.15,
        "use": random.random() < 0.05,
        "slot": random.choice([0, 1, 2]),
    }


def attack_action(dist):
    close = dist is not None and dist < 3.2
    return {
        "forward": dist is None or dist > 2.5,
        "back": False, "left": False, "right": False,
        "jump": False, "sprint": dist is not None and dist > 2.5, "sneak": False,
        "yaw": None, "pitch": None,
        "attack": close,
        "use": False, "slot": 0,
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance-id", type=int, default=0)
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--policy", type=str, default="attack", choices=["wander", "attack"])
    args = ap.parse_args()

    cfg = load_config()
    ports = ports_for(cfg, args.instance_id)
    server_proc = None
    frames = []

    try:
        if not (start_server.SERVER_DIR / "server.jar").exists():
            download_server.main()
        server_proc, _ = start_server.start(start_server.ROOT, cfg, args.instance_id)
        start_server.wait_ready(cfg, ports, proc=server_proc)

        env = ArenaEnv(cfg, instance_id=args.instance_id)
        env.spawn_bots()
        env.wait_bots_ready()
        env.teleport_to_spawns(y=5)   # грузим чанки
        time.sleep(1.5)
        setup_arena.build_arena(cfg, ports)
        agents = env.agent_names()
        obs, rewards, dones = env.reset()
        prev_dist = (rewards.get(agents[0]) or {}).get("dist") if agents else None

        print(f"[record] политика={args.policy}, {len(agents)} агент(а), {args.steps} шагов")
        for step in range(args.steps):
            if args.policy == "attack":
                actions = {n: attack_action(prev_dist) for n in agents}
            else:
                actions = {n: wander_action() for n in agents}
            obs, rewards, dones = env.step(actions)
            prev_dist = (rewards.get(agents[0]) or {}).get("dist") if agents else None
            for n in agents:
                o = obs.get(n) or {}
                s = o.get("self", {}) or {}
                e = o.get("enemy", {}) or {}
                rec = {
                    "step": step,
                    "red_x": s.get("x"),
                    "red_z": s.get("z"),
                    "red_hp": s.get("health"),
                    "blue_x": None,
                    "blue_z": None,
                    "dist": e.get("dist"),
                }
                if e.get("exists"):
                    rec["blue_x"] = (s.get("x") if s.get("x") is not None else 0) + (e.get("dx") or 0)
                    rec["blue_z"] = (s.get("z") if s.get("z") is not None else 0) + (e.get("dz") or 0)
                frames.append(rec)
        env.close()
    finally:
        if server_proc is not None:
            print("[record] останавливаю сервер...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except Exception:
                server_proc.kill()

    VIZ.mkdir(exist_ok=True)
    out = VIZ / "episode.json"
    payload = {"arena": cfg["arena"], "frames": frames}
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] сохранено {out} ({len(frames)} кадров)")


if __name__ == "__main__":
    main()
