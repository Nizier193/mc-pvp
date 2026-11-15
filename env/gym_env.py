"""Gymnasium-обёртка: один агент (Red) против dummy (Blue).

Наблюдение — вектор из 16 чисел; действие — MultiDiscrete([move, attack, jump, slot]):
  move: 0=стоп, 1=вперёд, 2=назад, 3=влево, 4=вправо
  attack: 0/1;  jump: 0/1;  slot: 0=меч, 1=шерсть, 2=паутина
(авто-прицел включён — агент всегда смотрит на врага, учится «подойти и ударить»).
"""
import math
import time

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from env.arena_env import ArenaEnv, start_full
from env.config import load_config, ports_for
from env.reward import compute_reward


class MinecraftPvPEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, cfg=None, instance_id=0, max_steps=300, manage_server=True):
        super().__init__()
        self.cfg = cfg or load_config()
        self.instance_id = instance_id
        self.max_steps = max_steps
        self._server_proc = None
        self._prev_dist = None
        self._steps = 0
        self._last_raw = None

        self.arena = ArenaEnv(self.cfg, instance_id=instance_id)
        self._agent = self.arena.agent_names()[0]

        if manage_server:
            self._server_proc = self._boot()
        self.arena.spawn_bots()
        self.arena.wait_bots_ready()
        self.arena.wait_players()

        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.MultiDiscrete([5, 2, 2, 3, 2])  # move, attack, jump, slot, use

    def _boot(self):
        from scripts import download_server, setup_arena, start_server
        from env.rcon import RCON

        ports = ports_for(self.cfg, self.instance_id)
        if not (start_server.SERVER_DIR / "server.jar").exists():
            download_server.main()
        server_proc, _ = start_server.start(start_server.ROOT, self.cfg, self.instance_id)
        start_server.wait_ready(self.cfg, ports, proc=server_proc)

        # спавн мира = центр арены, чтобы боты не спавнились далеко
        arena = self.cfg["arena"]
        rcon = RCON(ports["host"], ports["rcon_port"], self.cfg["server"]["rcon_password"])
        rcon.command("gamerule spawnRadius 0")  # боты появляются ровно в точке спавна
        rcon.command(f"setworldspawn {arena['center']['x']} {arena['floor_y'] + 1} {arena['center']['z']}")
        rcon.close()

        # строим арену ДО спавна ботов: они появятся уже на её поверхности
        # (телепорт в y=5 внутрь пола раньше давал кик «Invalid move player packet»)
        setup_arena.build_arena(self.cfg, ports)
        return server_proc

    # --- obs / action ---
    def _flatten(self, o):
        self._last_raw = o
        o = o or {}
        s = o.get("self", {}) or {}
        e = o.get("enemy", {}) or {}
        inv = o.get("inventory", {}) or {}
        ex = bool(e.get("exists"))
        return np.array([
            ((s.get("x", 5) or 5) - 5) / 5.0,
            ((s.get("z", 5) or 5) - 5) / 5.0,
            math.sin(s.get("yaw", 0) or 0),
            math.cos(s.get("yaw", 0) or 0),
            (s.get("pitch", 0) or 0) / 1.5,
            (s.get("health", 20) or 20) / 20.0,
            (s.get("food", 20) or 20) / 20.0,
            1.0 if s.get("onGround") else 0.0,
            (s.get("slot", 0) or 0) / 8.0,
            (e.get("dx", 0) or 0) / 10.0 if ex else 0.0,
            (e.get("dz", 0) or 0) / 10.0 if ex else 0.0,
            (e.get("dist", 12) or 12) / 12.0 if ex else 1.0,
            1.0 if ex else 0.0,
            (inv.get("wool", 0) or 0) / 32.0,
            (inv.get("cobweb", 0) or 0) / 5.0,
            1.0 if inv.get("sword") else 0.0,
        ], dtype=np.float32)

    def _action_to_dict(self, a):
        move, attack, jump, slot, use = int(a[0]), int(a[1]), int(a[2]), int(a[3]), int(a[4])
        return {
            "forward": move == 1,
            "back": move == 2,
            "left": move == 3,
            "right": move == 4,
            "jump": bool(jump),
            "sprint": move == 1,
            "sneak": False,
            "yaw": None, "pitch": None,   # авто-прицел
            "attack": bool(attack),
            "use": bool(use),
            "slot": slot,
        }

    def last_raw(self):
        """Последнее сырое наблюдение (с блоками арены) — для рендера миникарты."""
        return self._last_raw

    # --- Gym API ---
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        obs, rewards, dones = self.arena.reset()
        self._prev_dist = (rewards.get(self._agent) or {}).get("dist")
        self._steps = 0
        return self._flatten(obs.get(self._agent)), {}

    def step(self, action):
        a = self._action_to_dict(action)
        obs, rewards, dones = self.arena.step({self._agent: a})
        info = rewards.get(self._agent) or {}

        r = compute_reward(self._prev_dist, info)
        self._prev_dist = info.get("dist")
        self._steps += 1

        done = False
        if bool(dones.get(self._agent)):
            r -= 10.0            # поражение
            done = True
        if int(info.get("enemy_dead", 0) or 0) > 0:
            r += 10.0            # победа
            done = True
        if self._steps >= self.max_steps:
            done = True          # таймаут

        return self._flatten(obs.get(self._agent)), float(r), bool(done), False, {"raw": info}

    def close(self):
        self.arena.close()
        if self._server_proc is not None:
            try:
                self._server_proc.terminate()
                self._server_proc.wait(timeout=10)
            except Exception:
                try:
                    self._server_proc.kill()
                except Exception:
                    pass
