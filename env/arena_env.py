"""Gym-подобная обёртка 1v1 PvP-арены (символьное наблюдение).

Роль агента управляется через stdin/stdout-протокол, роль dummy живёт автономно
и служит baseline-соперником. Для self-play обе роли делаются agent.
"""
import time

from env.bot_process import BotProcess
from env.config import load_config, ports_for
from env.rcon import RCON


def _default_action():
    return {
        "forward": False, "back": False, "left": False, "right": False,
        "jump": False, "sprint": False, "sneak": False,
        "yaw": None, "pitch": None, "attack": False, "use": False, "slot": None,
    }


class ArenaEnv:
    def __init__(self, cfg=None, instance_id=0):
        self.cfg = cfg or load_config()
        self.ports = ports_for(self.cfg, instance_id)
        self.password = self.cfg["server"]["rcon_password"]
        self.bots = {}

    # --- RCON ---
    def _rcon(self):
        return RCON(self.ports["host"], self.ports["rcon_port"], self.password)

    def rcon(self, *cmds):
        rcon = self._rcon()
        outs = [rcon.command(c) for c in cmds]
        rcon.close()
        return outs

    def teleport_to_spawns(self, y=None):
        """Телепорт ботов в углы арены (грузит чанки перед /fill)."""
        arena = self.cfg["arena"]
        if y is None:
            y = arena["floor_y"] + 1
        cmds = [
            f"tp {ag['name']} {arena['spawns'][i]['x']} {y} {arena['spawns'][i]['z']}"
            for i, ag in enumerate(self.cfg["agents"])
        ]
        self.rcon(*cmds)

    # --- боты ---
    def spawn_bots(self):
        scripts = {"agent": "agent_bot.js", "dummy": "dummy_bot.js"}
        autoaim = bool(self.cfg.get("autoaim", False))
        still = bool(self.cfg.get("dummy_still", False))
        for ag in self.cfg["agents"]:
            script = scripts.get(ag.get("role", "agent"), "agent_bot.js")
            self.bots[ag["name"]] = BotProcess(
                ag["name"], self.ports["host"], self.ports["port"],
                version=self.cfg["server"].get("version", "1.8.9"),
                script=script,
                autoaim=autoaim and ag.get("role", "agent") == "agent",
                still=still and ag.get("role", "dummy") == "dummy",
            )

    def wait_bots_ready(self, timeout=90.0):
        for name, bot in self.bots.items():
            bot.wait_ready(timeout=timeout)

    def agent_names(self):
        return [a["name"] for a in self.cfg["agents"] if a.get("role", "agent") == "agent"]

    # --- эпизод ---
    def reset(self):
        """Сброс эпизода: сброс флагов, телепорт в углы (bot.teleport), выдача предметов."""
        for name in self.agent_names():
            self.bots[name].send({"type": "reset"})
        arena = self.cfg["arena"]
        items = self.cfg["items"]
        y = arena["floor_y"] + 1
        cmds = []
        for i, ag in enumerate(self.cfg["agents"]):
            name = ag["name"]
            sp = arena["spawns"][i]
            self.bots[name].send({"type": "reset"})
            cmds += [
                f"clear {name}",
                f"tp {name} {sp['x']} {y} {sp['z']}",
                f"replaceitem entity {name} container.{items['sword_slot']} {items['sword']} 1",
                f"replaceitem entity {name} container.{items['wool_slot']} {items['wool']} {items['wool_count']}",
                f"replaceitem entity {name} container.{items['cobweb_slot']} {items['cobweb']} {items['cobweb_count']}",
            ]
        self.rcon(*cmds)
        time.sleep(0.5)
        return self.step({n: _default_action() for n in self.agent_names()})

    def step(self, actions):
        for name in self.agent_names():
            self.bots[name].send({"type": "step", "action": actions.get(name, _default_action())})
        obs, rewards, dones = {}, {}, {}
        for name in self.agent_names():
            msg = self.bots[name].recv(timeout=5.0) or {}
            obs[name] = msg.get("obs")
            rewards[name] = msg.get("reward", {})
            dones[name] = msg.get("done", False)
        return obs, rewards, dones

    def close(self):
        for bot in self.bots.values():
            bot.close()


def start_full(cfg, instance_id=0):
    """Полный старт одного инстанса: сервер + арена + боты.

    Возвращает (env, server_proc). server_proc нужно terminate() после работы.
    """
    from scripts import download_server, setup_arena, start_server
    from env.rcon import RCON

    ports = ports_for(cfg, instance_id)
    if not (start_server.SERVER_DIR / "server.jar").exists():
        download_server.main()
    server_proc, _ = start_server.start(start_server.ROOT, cfg, instance_id)
    start_server.wait_ready(cfg, ports, proc=server_proc)

    # спавн мира = центр арены ДО подключения ботов: иначе они заспавнятся далеко
    # и /tp на 300+ блоков вызовет «Invalid move packet» (kick).
    arena = cfg["arena"]
    rcon = RCON(ports["host"], ports["rcon_port"], cfg["server"]["rcon_password"])
    rcon.command(f"setworldspawn {arena['center']['x']} {arena['floor_y'] + 1} {arena['center']['z']}")
    rcon.close()

    env = ArenaEnv(cfg, instance_id=instance_id)
    env.spawn_bots()
    env.wait_bots_ready()
    env.teleport_to_spawns(y=5)   # грузим чанки арены
    time.sleep(1.5)
    setup_arena.build_arena(cfg, ports)
    return env, server_proc
