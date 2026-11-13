"""Загрузка конфига проекта (YAML или JSON) и вычисление портов инстанса."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = ROOT / "server"

DEFAULT_YAML = ROOT / "configs" / "train.yaml"
DEFAULT_JSON = ROOT / "config" / "arena.json"


def _load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_config(path=None):
    """Загрузить конфиг.

    - с аргументом: путь к .yaml/.yml или .json.
    - без аргумента: configs/train.yaml (если PyYAML доступен),
      иначе config/arena.json (JSON-фолбэк для машин без PyYAML).
    """
    if path is not None:
        p = Path(path)
        if p.suffix in (".yaml", ".yml"):
            return _load_yaml(p)
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    if DEFAULT_YAML.exists():
        try:
            return _load_yaml(DEFAULT_YAML)
        except ImportError:
            pass  # PyYAML не установлен — падаем на JSON
    if DEFAULT_JSON.exists():
        with open(DEFAULT_JSON, encoding="utf-8") as f:
            return json.load(f)
    raise FileNotFoundError(
        "нет конфига: configs/train.yaml или config/arena.json"
    )


def ports_for(cfg, instance_id=0):
    """Один инстанс = свой сервер (порты + мир), чтобы можно было параллелить."""
    s = cfg["server"]
    step = int(s.get("port_step", 10))
    return {
        "host": s.get("host", "127.0.0.1"),
        "port": int(s["port"]) + instance_id * step,
        "rcon_port": int(s["rcon_port"]) + instance_id * step,
        "level_name": f"{s.get('level_name', 'world')}_{instance_id}",
    }
