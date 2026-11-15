"""Построить арену и выставить правила по config/arena.json через RCON.

Запуск:  python scripts/setup_arena.py [instance_id]
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from env.config import load_config, ports_for
from env.rcon import RCON


def build_arena(cfg, ports):
    arena = cfg["arena"]
    rcon = RCON(ports["host"], ports["rcon_port"], cfg["server"]["rcon_password"])

    def cmd(c):
        out = rcon.command(c)
        if out:
            print(f"  $ {c}\n    -> {out.strip()}")
        return out

    fy = arena["floor_y"]
    h = arena["wall_height"]
    side = arena["side"]
    x0 = arena["origin"]["x"]
    z0 = arena["origin"]["z"]
    x1 = x0 + side - 1
    z1 = z0 + side - 1
    cx, cz = arena["center"]["x"], arena["center"]["z"]

    # 1) Сначала центрируем спавн-чанки на арене: спавн-чанки всегда загружены,
    #    поэтому /fill ниже гарантированно сработает (иначе «outside of the world»).
    cmd(f"setworldspawn {cx} {fy+1} {cz}")
    time.sleep(2.0)

    # 2) Правила мира (валидны для 1.8.9).
    for g, v in [
        ("doDaylightCycle", "false"),
        ("doMobSpawning", "false"),
        ("doFireTick", "false"),
        ("naturalRegeneration", "false"),
        ("doTileDrops", "false"),
    ]:
        cmd(f"gamerule {g} {v}")

    # 3) Пол и стены.
    floor = arena["floor_block"]
    wall = arena["wall_block"]
    print("[arena] пол + толстая опора")
    # толстая опора от y=6 до пола (fy): снизу оставляем воздушный зазор (y=4..5),
    # чтобы боты, спавнящиеся на natural terrain (y=4), не задыхались в залитом
    # полу и доживали до телепорта на арену.
    cmd(f"fill {x0} 6 {z0} {x1} {fy} {z1} {floor}")
    print("[arena] стены")
    cmd(f"fill {x0-1} {fy+1} {z0-1} {x1+1} {fy+h} {z0-1} {wall}")   # север
    cmd(f"fill {x0-1} {fy+1} {z1+1} {x1+1} {fy+h} {z1+1} {wall}")   # юг
    cmd(f"fill {x0-1} {fy+1} {z0} {x0-1} {fy+h} {z1} {wall}")       # запад
    cmd(f"fill {x1+1} {fy+1} {z0} {x1+1} {fy+h} {z1} {wall}")       # восток

    # 4) ВАЖНО: ставим спавн ПОСЛЕ заливки пола — теперь «земля» на арене = fy,
    #    и боты появляются на поверхности (fy+1), а не внутри пола (y=4),
    #    где они задыхались и получали «Invalid move player packet».
    cmd(f"setworldspawn {cx} {fy+1} {cz}")
    cmd("save-all")
    rcon.close()
    print("[arena] готово")


if __name__ == "__main__":
    cfg = load_config()
    iid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    build_arena(cfg, ports_for(cfg, iid))
