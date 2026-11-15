"""Markdown-отчёты об экспериментах в experiments/runs/."""
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "experiments" / "runs"


def write_report(name, cfg, body):
    """Записать отчёт experiments/runs/<name>.md (с шапкой из конфига).

    name  — имя файла без .md (например, run_1_train / run_1_eval)
    cfg   — загруженный конфиг (для шапки: версия, гиперпараметры)
    body  — markdown-тело с результатами
    """
    REPORTS.mkdir(parents=True, exist_ok=True)
    path = REPORTS / f"{name}.md"
    server = cfg.get("server", {}) or {}
    training = cfg.get("training", {}) or {}
    header = (
        f"# Эксперимент: `{name}`\n\n"
        f"| поле | значение |\n|---|---|\n"
        f"| дата | {datetime.now():%Y-%m-%d %H:%M} |\n"
        f"| Minecraft | {server.get('version', '?')} |\n"
        f"| алгоритм | {training.get('algorithm', 'ppo')} |\n"
        f"| timesteps | {training.get('total_timesteps', '?')} |\n"
        f"| device | {training.get('device', '?')} |\n"
        f"| autoaim | {cfg.get('autoaim')} |\n"
        f"| dummy_still | {cfg.get('dummy_still')} |\n\n"
    )
    path.write_text(header + body.strip() + "\n", encoding="utf-8")
    print(f"[report] {path}")
    return path
