"""Обёртка над процессом Node (mineflayer): общение JSON-строками stdin/stdout."""
import json
import queue
import shutil
import subprocess
import threading
import time

from env.config import ROOT


class BotProcess:
    def __init__(self, name, host, port, version="1.8.9", script="agent_bot.js", autoaim=False, still=False):
        self.name = name
        node = shutil.which("node") or "node"
        script_path = ROOT / "bots" / script
        cmd = [node, str(script_path), "--name", name, "--host", host,
               "--port", str(port), "--version", version]
        if autoaim:
            cmd += ["--autoaim", "1"]
        if still:
            cmd += ["--still", "1"]
        self.proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._q = queue.Queue()
        self._t = threading.Thread(target=self._reader, daemon=True)
        self._t.start()

    def _reader(self):
        for line in self.proc.stdout:
            line = line.strip()
            if not line:
                continue
            if line.startswith("{"):
                try:
                    self._q.put(json.loads(line))
                except json.JSONDecodeError:
                    pass
            else:
                print(f"[{self.name}] {line}", flush=True)

    def send(self, obj):
        self.proc.stdin.write(json.dumps(obj) + "\n")
        self.proc.stdin.flush()

    def recv(self, timeout=15.0):
        try:
            return self._q.get(timeout=timeout)
        except queue.Empty:
            return None

    def wait_ready(self, timeout=60.0):
        import time as _t
        deadline = _t.time() + timeout
        while _t.time() < deadline:
            msg = self.recv(timeout=max(0.1, deadline - _t.time()))
            if msg and msg.get("type") == "ready":
                return msg
            if self.proc.poll() is not None:
                raise RuntimeError(f"бот {self.name} завершился (exit={self.proc.returncode})")
        raise TimeoutError(f"бот {self.name} не готов за {timeout}s")

    def close(self):
        try:
            self.send({"type": "stop"})
        except Exception:
            pass
        try:
            self.proc.terminate()
        except Exception:
            pass
        time.sleep(0.3)
        try:
            self.proc.kill()
        except Exception:
            pass
