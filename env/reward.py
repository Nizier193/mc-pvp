"""Функция награды: +1 за удар, -1 за полученный удар, +0.1 за сближение.

Победа/поражение добавляются снаружи (в env/скрипте): +10 победа, -10 поражение.
"""


def compute_reward(prev_dist, reward_info):
    info = reward_info or {}
    r = 0.0
    r += 1.0 * int(info.get("hits_landed", 0) or 0)          # +1 за нанесённый удар
    if (info.get("damage_taken", 0) or 0) > 0:                # -1 за полученный удар
        r -= 1.0
    dist = info.get("dist")
    if prev_dist is not None and dist is not None:
        r += 0.1 * max(0.0, prev_dist - dist)                 # +0.1 за сближение
    return r
