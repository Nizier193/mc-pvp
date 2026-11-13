"""Запустить N инстансов параллельно (масштабирование среды).

Каждый инстанс — отдельный сервер со своими портами и миром, плюс свои боты.
Порты инстансов не пересекаются благодаря port_step в config/arena.json.

Пример:  python scripts/launch_instances.py --instances 4 --steps 50
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import argparse
import concurrent.futures
import subprocess


def _run_one(iid, steps, skip_server):
    script = Path(__file__).resolve().parent / "run_arena.py"
    cmd = [sys.executable, str(script), "--instance-id", str(iid), "--steps", str(steps)]
    if skip_server:
        cmd.append("--skip-server")
    return subprocess.run(cmd, cwd=str(Path(__file__).resolve().parent.parent))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", type=int, default=2)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--skip-server", action="store_true")
    args = ap.parse_args()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.instances) as ex:
        futs = [ex.submit(_run_one, i, args.steps, args.skip_server) for i in range(args.instances)]
        for i, f in enumerate(futs):
            print(f"[instance {i}] exit={f.result().returncode}")


if __name__ == "__main__":
    main()
