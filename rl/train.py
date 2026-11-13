"""Обучение PPO (Stable-Baselines3) с YAML-конфигом.

Артефакты сохраняются в artefacts/runs/<run_name>/:
  model.zip     — обученная модель
  config.yaml   — копия конфига
  tb/           — tensorboard-логи

Запуск:  python rl/train.py --config configs/train.yaml
"""
import sys
import shutil
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse

from env.gym_env import MinecraftPvPEnv
from env.config import load_config


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=str, default="configs/train.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    training = cfg.get("training", {})
    output = cfg.get("output", {})

    base = Path(output.get("base_dir", "artefacts"))
    run_name = output.get("run_name") or ("run_" + time.strftime("%Y%m%d_%H%M%S"))
    run_dir = base / "runs" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(args.config, run_dir / "config.yaml")

    from stable_baselines3 import PPO

    env = MinecraftPvPEnv(cfg=cfg, max_steps=training.get("max_episode_steps", 300))
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        n_steps=training.get("n_steps", 1024),
        batch_size=training.get("batch_size", 128),
        learning_rate=training.get("learning_rate", 3e-4),
        gamma=training.get("gamma", 0.99),
        tensorboard_log=str(run_dir / "tb"),
    )
    model.learn(total_timesteps=training.get("total_timesteps", 20000))
    model.save(str(run_dir / "model"))
    env.close()

    print(f"[ok] модель: {run_dir / 'model.zip'}")
    print(f"[ok] артефакты: {run_dir}")


if __name__ == "__main__":
    main()
