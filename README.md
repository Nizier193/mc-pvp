# mc-pvp — символическое RL для PvP в Minecraft 1.16.5

Среда «1 на 1»: арена 10×10, два бота, у каждого алмазный меч, 32 белой шерсти
и 5 паутинок. Задача — победить соперника.

Стек: сервер Minecraft 1.16.5 (vanilla, offline) + боты Mineflayer (Node.js) +
RL на Python (PPO, Stable-Baselines3). Наблюдение **символьное** (вектор 16 чисел),
действие — `MultiDiscrete([движение, удар, прыжок, слот])`.

## Быстрый старт (Google Colab / Linux)

```bash
git clone https://github.com/Nizier193/mc-pvp.git
cd mc-pvp

# 1) установка всего (Java, Node, ImageMagick, pip, npm, server.jar)
bash scripts/setup.sh

# 2) обучение (конфиг YAML, артефакты в artefacts/runs/<run>/)
bash scripts/train.sh configs/train.yaml

# 3) инференс + гифка боя на карте
bash scripts/eval.sh configs/train.yaml artefacts/runs/run_1/model.zip
```

## Конфиги (YAML)

- `configs/train.yaml` — всё в одном: сервер, арена, предметы, агенты, гиперпараметры
  PPO и секция `output` (куда сохранять артефакты).
- Меняешь конфиг → передаёшь в `train.sh` / `eval.sh`.

Секция `output`:
```yaml
output:
  base_dir: artefacts
  run_name: run_1
```

## Артефакты обучения

```
artefacts/runs/<run_name>/
├── model.zip        # обученная модель (SB3)
├── config.yaml      # копия конфига
├── tb/              # tensorboard
└── episodes/        # гифки боя (после eval.sh)
    └── episode_0/{episode.gif, map.png, episode.json}
```

## Структура

```
mc-pvp/
├── configs/train.yaml            # YAML-конфиг обучения
├── config/                       # JSON-фолбэк + шаблон server.properties
├── bots/                         # Mineflayer-боты (agent + dummy)
├── env/                          # RCON, env-обёртка, Gymnasium, reward
├── rl/                           # train.py, eval.py, baseline_attack.py
├── scripts/                      # download/start/setup_arena + setup.sh/train.sh/eval.sh
├── requirements.txt / package.json
└── artefacts/                    # выходные артефакты (gitignored)
```

## Локально (Windows)

```powershell
cd mc-pvp
# Python 3.12 (полный путь, т.к. python на PATH может быть заглушкой Store)
C:\Users\<user>\AppData\Local\Programs\Python\Python312\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm install
.\.venv\Scripts\python.exe scripts\run_arena.py --steps 20   # дымовой тест
```

## Требования

- Node.js ≥ 18 (боты Mineflayer).
- Java 8 или 11 (сервер 1.16.5).
- Python 3.9+.
- ImageMagick (для сборки гифок).

## Награда

`+1` за нанесённый удар, `−1` за полученный, `+0.1` за сближение, `+10` победа, `−10` поражение.
См. `env/reward.py`.
