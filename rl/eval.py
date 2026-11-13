"""Инференс обученной модели + рендер гифки боя на карте.

Артефакты: artefacts/runs/<run_name>/episodes/episode_N/{episode.gif, map.png, episode.json}

Запуск:  python rl/eval.py --config configs/train.yaml --model artefacts/runs/run_1/model.zip
"""
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import argparse

from env.gym_env import MinecraftPvPEnv
from env.config import load_config


def flatten_to_state(obs):
    """Восстановить позиции/здоровье из 16-мерного нормализованного вектора."""
    red_x = float(obs[0]) * 5.0 + 5.0
    red_z = float(obs[1]) * 5.0 + 5.0
    red_hp = float(obs[5]) * 20.0
    if float(obs[12]) > 0.5:
        blue_x = red_x + float(obs[9]) * 10.0
        blue_z = red_z + float(obs[10]) * 10.0
        dist = float(obs[11]) * 12.0
    else:
        blue_x = blue_z = dist = None
    return red_x, red_z, blue_x, blue_z, red_hp, dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="configs/train.yaml")
    ap.add_argument("--model", type=str, required=True)
    ap.add_argument("--episodes", type=int, default=2)
    ap.add_argument("--steps", type=int, default=150)
    args = ap.parse_args()

    cfg = load_config(args.config)
    out = (Path(cfg.get("output", {}).get("base_dir", "artefacts")) / "runs"
           / cfg.get("output", {}).get("run_name", "run") / "episodes")
    out.mkdir(parents=True, exist_ok=True)

    from stable_baselines3 import PPO
    import render_viz  # из scripts/

    env = MinecraftPvPEnv(cfg=cfg)
    model = PPO.load(args.model, env=env)

    for ep in range(args.episodes):
        obs, _ = env.reset()
        frames = []
        for step in range(args.steps):
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, done, _, info = env.step(action)
            rx, rz, bx, bz, hp, dist = flatten_to_state(obs)
            frames.append({
                "step": step, "red_x": rx, "red_z": rz, "red_hp": hp,
                "blue_x": bx, "blue_z": bz, "dist": dist,
            })
            if done:
                break

        payload = {"arena": cfg["arena"], "frames": frames}
        ep_dir = out / f"episode_{ep}"
        ep_dir.mkdir(parents=True, exist_ok=True)
        (ep_dir / "episode.json").write_text(json.dumps(payload), encoding="utf-8")

        render_viz.VIZ = ep_dir
        render_viz.render_map(payload)
        render_viz.render_frames(payload)
        print(f"[ok] эпизод {ep}: {ep_dir / 'episode.gif'}")

    env.close()


if __name__ == "__main__":
    main()
