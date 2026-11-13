"""Скриптовый атакующий агент: проверка сигналов награды без обучения.

Агент сближается с врагом (авто-прицел) и бьёт вблизи. Логирует награду:
+1 удар, -1 полученный удар, +0.1 сближение, +10 победа, -10 поражение.

Запуск:  python rl/baseline_attack.py --steps 400
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env.arena_env import start_full
from env.config import load_config
from env.reward import compute_reward


def attack_action(dist):
    close = dist is not None and dist < 3.2
    return {
        "forward": dist is None or dist > 2.5,   # сближаемся, останавливаемся вблизи
        "back": False, "left": False, "right": False,
        "jump": False, "sprint": dist is not None and dist > 2.5, "sneak": False,
        "yaw": None, "pitch": None,
        "attack": close,        # бьём вблизи
        "use": False, "slot": 0,  # меч
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance-id", type=int, default=0)
    ap.add_argument("--steps", type=int, default=400)
    args = ap.parse_args()

    cfg = load_config()
    env, server_proc = None, None
    total = 0.0
    hits = 0
    taken = 0
    wins = 0
    losses = 0
    episodes = 0
    prev_dist = None

    try:
        env, server_proc = start_full(cfg, args.instance_id)
        agent = env.agent_names()[0]

        obs, rewards, dones = env.reset()
        prev_dist = (rewards.get(agent) or {}).get("dist")
        episodes += 1

        print(f"[baseline] скриптовый атакующий, {args.steps} шагов")
        for step in range(args.steps):
            a = attack_action(prev_dist)
            obs, rewards, dones = env.step({agent: a})
            info = rewards.get(agent) or {}
            r = compute_reward(prev_dist, info)

            done = bool(dones.get(agent)) or int(info.get("enemy_dead", 0) or 0) > 0
            if dones.get(agent):
                r -= 10.0
                losses += 1
            if int(info.get("enemy_dead", 0) or 0) > 0:
                r += 10.0
                wins += 1
            total += r
            hits += int(info.get("hits_landed", 0) or 0)
            if (info.get("damage_taken", 0) or 0) > 0:
                taken += 1
            prev_dist = info.get("dist")

            if step % 20 == 0 or done:
                o = obs.get(agent) or {}
                s = o.get("self", {}) or {}
                e = o.get("enemy", {}) or {}
                bx = (s.get("x") or 0) + (e.get("dx") or 0) if e.get("exists") else None
                bz = (s.get("z") or 0) + (e.get("dz") or 0) if e.get("exists") else None
                print(f"step={step:4d} Red=({s.get('x')},{s.get('z')}) yaw={s.get('yaw')} Blue=({bx},{bz}) "
                      f"held={info.get('held')} slot={info.get('slot')} atk={info.get('attacks')} "
                      f"hits={info.get('hits_landed')} dist={info.get('dist')} hp={info.get('self_hp')}")

            if done:
                obs, rewards, dones = env.reset()
                prev_dist = (rewards.get(agent) or {}).get("dist")
                episodes += 1
        env.close()
    finally:
        if server_proc is not None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except Exception:
                server_proc.kill()

    print(f"\n=== итог за {args.steps} шагов ({episodes} эпизод(ов)) ===")
    print(f"суммарная награда = {total:+.1f}")
    print(f"нанесено ударов  = {hits}")
    print(f"получено ударов  = {taken}")
    print(f"побед = {wins}, поражений = {losses}")


if __name__ == "__main__":
    main()
