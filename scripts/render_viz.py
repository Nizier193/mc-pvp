"""Рендер визуализаций эпизода из viz/episode.json (без matplotlib).

Создаёт:
  viz/map.png       — карта арены сверху + траектории обоих игроков
  viz/episode.gif   — анимация точек на карте (через ImageMagick)
  viz/distance.png  — дистанция между игроками по времени
  viz/health.png    — здоровье агента по времени
  viz/episode.csv   — сырые данные

Запуск:  python scripts/render_viz.py
"""
import sys
import json
import struct
import zlib
import shutil
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ROOT = Path(__file__).resolve().parent.parent
VIZ = ROOT / "viz"


# ---------------- minimal PNG writer (stdlib: zlib) ----------------
def _chunk(typ, data):
    c = struct.pack(">I", len(data)) + typ + data
    return c + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)


def write_png(path, w, h, pixels):
    raw = b"".join(b"\x00" + bytes(v for px in row for v in px) for row in pixels)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw, 9)
    with open(path, "wb") as f:
        f.write(sig + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", idat) + _chunk(b"IEND", b""))


def new_image(w, h, color):
    return [[color for _ in range(w)] for _ in range(h)]


def fill_rect(img, x0, y0, x1, y1, color):
    x0, x1 = max(0, int(x0)), min(len(img[0]), int(x1) + 1)
    y0, y1 = max(0, int(y0)), min(len(img), int(y1) + 1)
    for y in range(y0, y1):
        for x in range(x0, x1):
            img[y][x] = color


def draw_dot(img, cx, cy, r, color):
    for y in range(max(0, int(cy - r)), min(len(img), int(cy + r) + 1)):
        for x in range(max(0, int(cx - r)), min(len(img[0]), int(cx + r) + 1)):
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                img[y][x] = color


def draw_line(img, x0, y0, x1, y1, color, thickness=2.0):
    steps = max(1, int(max(abs(x1 - x0), abs(y1 - y0))))
    for i in range(steps + 1):
        t = i / steps
        draw_dot(img, x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, thickness / 2, color)


# ---------------- 3x5 bitmap font ----------------
FONT = {
    "0": ["111", "101", "101", "101", "111"],
    "1": ["010", "110", "010", "010", "111"],
    "2": ["111", "001", "111", "100", "111"],
    "3": ["111", "001", "111", "001", "111"],
    "4": ["101", "101", "111", "001", "001"],
    "5": ["111", "100", "111", "001", "111"],
    "6": ["111", "100", "111", "101", "111"],
    "7": ["111", "001", "010", "010", "010"],
    "8": ["111", "101", "111", "101", "111"],
    "9": ["111", "101", "111", "001", "111"],
    "-": ["000", "000", "111", "000", "000"],
    ".": ["000", "000", "000", "000", "010"],
    " ": ["000", "000", "000", "000", "000"],
}


def draw_text(img, x, y, text, color, scale=2):
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph is None:
            cx += 4 * scale
            continue
        for r in range(5):
            for c in range(3):
                if glyph[r][c] == "1":
                    for sy in range(scale):
                        for sx in range(scale):
                            px, py = cx + c * scale + sx, y + r * scale + sy
                            if 0 <= px < len(img[0]) and 0 <= py < len(img):
                                img[py][px] = color
        cx += 4 * scale


# ---------------- palette ----------------
VOID = (18, 18, 22)
FLOOR = (125, 125, 125)
WALL = (215, 80, 80)
RED = (235, 60, 60)
BLUE = (70, 130, 235)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
GRID = (225, 225, 225)
TRAIL_RED = (255, 170, 170)
TRAIL_BLUE = (170, 200, 255)
WOOL = (248, 248, 248)
COBWEB = (175, 175, 175)


def load_episode():
    with open(VIZ / "episode.json", encoding="utf-8") as f:
        return json.load(f)


def world_to_px(x, z, scale, margin, xmin, zmin):
    return margin + (x - xmin) * scale, margin + (z - zmin) * scale


def arena_geometry(arena):
    side = arena.get("side", 10)
    ox = arena.get("origin", {}).get("x", 0)
    oz = arena.get("origin", {}).get("z", 0)
    # область: floor [ox, ox+side-1] x [oz, oz+side-1], стены на ox-1 и ox+side
    xmin, zmin = ox - 1.0, oz - 1.0
    xmax, zmax = ox + side, oz + side
    return xmin, zmin, xmax, zmax, ox, oz, side


def draw_arena_base(img, xmin, zmin, ox, oz, side, scale, margin):
    # фон = пустота
    for y in range(len(img)):
        for x in range(len(img[0])):
            img[y][x] = VOID
    # пол
    fx0, fy0 = world_to_px(ox, oz, scale, margin, xmin, zmin)
    fx1, fy1 = world_to_px(ox + side, oz + side, scale, margin, xmin, zmin)
    fill_rect(img, fx0, fy0, fx1, fy1, FLOOR)
    # стены (периметр)
    wx0, wy0 = world_to_px(ox - 1, oz - 1, scale, margin, xmin, zmin)
    wx1, wy1 = world_to_px(ox + side, oz + side, scale, margin, xmin, zmin)
    t = max(2, int(scale * 0.22))
    fill_rect(img, wx0 - t, wy0 - t, wx1 + t, wy0 + t, WALL)   # север
    fill_rect(img, wx0 - t, wy1 - t, wx1 + t, wy1 + t, WALL)   # юг
    fill_rect(img, wx0 - t, wy0, wx0 + t, wy1, WALL)           # запад
    fill_rect(img, wx1 - t, wy0, wx1 + t, wy1, WALL)           # восток
    return fx0, fy0, fx1, fy1


def draw_blocks(img, blocks, xmin, zmin, scale, margin):
    """Отрисовка установленных блоков: шерсть — белая, паутина — серая."""
    for blk in blocks:
        x, z, name = blk[0], blk[1], blk[2]
        px, py = world_to_px(x + 0.5, z + 0.5, scale, margin, xmin, zmin)
        color = COBWEB if (name == 'web' or 'cobweb' in name) else WOOL
        s = scale * 0.42
        fill_rect(img, px - s, py - s, px + s, py + s, color)


def positions(frames):
    xs_red, zs_red, xs_blue, zs_blue, dists, hps, steps = [], [], [], [], [], [], []
    for f in frames:
        steps.append(f["step"])
        if f.get("red_x") is not None and f.get("red_z") is not None:
            xs_red.append(f["red_x"]); zs_red.append(f["red_z"])
        if f.get("blue_x") is not None and f.get("blue_z") is not None:
            xs_blue.append(f["blue_x"]); zs_blue.append(f["blue_z"])
        dists.append(f.get("dist"))
        hps.append(f.get("red_hp"))
    return xs_red, zs_red, xs_blue, zs_blue, dists, hps, steps


def render_map(payload):
    arena = payload["arena"]
    frames = payload["frames"]
    xmin, zmin, xmax, zmax, ox, oz, side = arena_geometry(arena)
    scale, margin = 44, 40
    W = int((xmax - xmin) * scale + 2 * margin)
    H = int((zmax - zmin) * scale + 2 * margin)
    img = new_image(W, H, VOID)
    draw_arena_base(img, xmin, zmin, ox, oz, side, scale, margin)
    draw_blocks(img, frames[-1].get("blocks", []) if frames else [], xmin, zmin, scale, margin)

    xs_red, zs_red, xs_blue, zs_blue, _, _, _ = positions(frames)

    # траектория Red (линия) и Blue (линия)
    for arr, color in ((zip(xs_red, zs_red), RED), (zip(xs_blue, zs_blue), BLUE)):
        pts = list(arr)
        for i in range(1, len(pts)):
            x0, z0 = pts[i - 1]
            x1, z1 = pts[i]
            p0 = world_to_px(x0, z0, scale, margin, xmin, zmin)
            p1 = world_to_px(x1, z1, scale, margin, xmin, zmin)
            draw_line(img, p0[0], p0[1], p1[0], p1[1], color, thickness=2.5)

    # старт (квадрат) и конец (крест)
    if xs_red and zs_red:
        sx, sy = world_to_px(xs_red[0], zs_red[0], scale, margin, xmin, zmin)
        ex, ey = world_to_px(xs_red[-1], zs_red[-1], scale, margin, xmin, zmin)
        fill_rect(img, sx - 5, sy - 5, sx + 5, sy + 5, TRAIL_RED)
        draw_dot(img, ex, ey, 6, RED)
    if xs_blue and zs_blue:
        sx, sy = world_to_px(xs_blue[0], zs_blue[0], scale, margin, xmin, zmin)
        ex, ey = world_to_px(xs_blue[-1], zs_blue[-1], scale, margin, xmin, zmin)
        fill_rect(img, sx - 5, sy - 5, sx + 5, sy + 5, TRAIL_BLUE)
        draw_dot(img, ex, ey, 6, BLUE)

    # финальные точки-игроки
    if xs_red and zs_red:
        rx, ry = world_to_px(xs_red[-1], zs_red[-1], scale, margin, xmin, zmin)
        draw_dot(img, rx, ry, 7, RED)
    if xs_blue and zs_blue:
        bx, by = world_to_px(xs_blue[-1], zs_blue[-1], scale, margin, xmin, zmin)
        draw_dot(img, bx, by, 7, BLUE)

    write_png(VIZ / "map.png", W, H, img)
    print("[ok] viz/map.png")


def render_frames(payload):
    arena = payload["arena"]
    frames = payload["frames"]
    xmin, zmin, xmax, zmax, ox, oz, side = arena_geometry(arena)
    scale, margin = 44, 40
    W = int((xmax - xmin) * scale + 2 * margin)
    H = int((zmax - zmin) * scale + 2 * margin)

    out_dir = VIZ / "frames"
    out_dir.mkdir(exist_ok=True)
    for p in out_dir.glob("frame_*.png"):
        p.unlink()

    trail = 12
    for fi, f in enumerate(frames):
        img = new_image(W, H, VOID)
        draw_arena_base(img, xmin, zmin, ox, oz, side, scale, margin)
        draw_blocks(img, f.get("blocks", []), xmin, zmin, scale, margin)
        # хвост Red
        for k in range(1, trail + 1):
            j = fi - k
            if j < 0:
                break
            g = frames[j]
            if g.get("red_x") is None:
                continue
            px, py = world_to_px(g["red_x"], g["red_z"], scale, margin, xmin, zmin)
            alpha = 1 - k / (trail + 1)
            c = (int(TRAIL_RED[0] * alpha + FLOOR[0] * (1 - alpha)),
                 int(TRAIL_RED[1] * alpha + FLOOR[1] * (1 - alpha)),
                 int(TRAIL_RED[2] * alpha + FLOOR[2] * (1 - alpha)))
            draw_dot(img, px, py, 4 + 3 * alpha, c)
        # хвост Blue
        for k in range(1, trail + 1):
            j = fi - k
            if j < 0:
                break
            g = frames[j]
            if g.get("blue_x") is None:
                continue
            px, py = world_to_px(g["blue_x"], g["blue_z"], scale, margin, xmin, zmin)
            alpha = 1 - k / (trail + 1)
            c = (int(TRAIL_BLUE[0] * alpha + FLOOR[0] * (1 - alpha)),
                 int(TRAIL_BLUE[1] * alpha + FLOOR[1] * (1 - alpha)),
                 int(TRAIL_BLUE[2] * alpha + FLOOR[2] * (1 - alpha)))
            draw_dot(img, px, py, 4 + 3 * alpha, c)
        # текущие точки
        if f.get("red_x") is not None:
            rx, ry = world_to_px(f["red_x"], f["red_z"], scale, margin, xmin, zmin)
            draw_dot(img, rx, ry, 7, RED)
        if f.get("blue_x") is not None:
            bx, by = world_to_px(f["blue_x"], f["blue_z"], scale, margin, xmin, zmin)
            draw_dot(img, bx, by, 7, BLUE)
        # номер шага
        draw_text(img, 8, 8, str(f["step"]), WHITE, scale=2)
        write_png(out_dir / f"frame_{fi:04d}.png", W, H, img)

    magick = shutil.which("magick") or "magick"
    frames_png = sorted(str(p) for p in out_dir.glob("frame_*.png"))
    gif = VIZ / "episode.gif"
    subprocess.run([magick, "-delay", "6", "-loop", "0", *frames_png, str(gif)], check=True)
    print(f"[ok] viz/episode.gif ({len(frames_png)} кадров)")


def render_chart(path, xs, ys, color, ymin, ymax, title, xlabel, ylabel):
    W, H = 640, 360
    ml, mr, mt, mb = 55, 15, 25, 40
    img = new_image(W, H, WHITE)
    # сетка
    for i in range(6):
        y = mt + (H - mt - mb) * i / 5
        draw_line(img, ml, y, W - mr, y, GRID, 1)
    # оси
    draw_line(img, ml, mt, ml, H - mb, BLACK, 2)
    draw_line(img, ml, H - mb, W - mr, H - mb, BLACK, 2)
    # кривая
    n = len(xs)
    if n > 1:
        for i in range(1, n):
            x0 = ml + (W - ml - mr) * (i - 1) / (n - 1)
            y0 = mt + (H - mt - mb) * (1 - (ys[i - 1] - ymin) / (ymax - ymin))
            x1 = ml + (W - ml - mr) * i / (n - 1)
            y1 = mt + (H - mt - mb) * (1 - (ys[i] - ymin) / (ymax - ymin))
            draw_line(img, x0, y0, x1, y1, color, 2.5)
    # метки Y
    for i in range(6):
        val = ymin + (ymax - ymin) * i / 5
        draw_text(img, ml - 40, int(mt + (H - mt - mb) * i / 5) - 5, f"{val:.1f}", BLACK, scale=2)
    # заголовок
    draw_text(img, ml, 6, title, BLACK, scale=2)
    write_png(path, W, H, img)
    print(f"[ok] {path.name}")


def render_charts(payload):
    frames = payload["frames"]
    _, _, _, _, dists, hps, steps = positions(frames)
    dists_f = [d if d is not None else 0.0 for d in dists]
    hps_f = [h if h is not None else 0.0 for h in hps]
    render_chart(VIZ / "distance.png", steps, dists_f, BLUE, 0, 12, "distance red-blue (blocks)", "step", "dist")
    render_chart(VIZ / "health.png", steps, hps_f, RED, 0, 20, "red health", "step", "hp")


def render_csv(payload):
    frames = payload["frames"]
    lines = ["step,red_x,red_z,red_hp,blue_x,blue_z,dist"]
    for f in frames:
        lines.append(",".join(str(f.get(k, "")) for k in
                              ["step", "red_x", "red_z", "red_hp", "blue_x", "blue_z", "dist"]))
    (VIZ / "episode.csv").write_text("\n".join(lines), encoding="utf-8")
    print("[ok] viz/episode.csv")


def main():
    payload = load_episode()
    render_map(payload)
    render_frames(payload)
    render_charts(payload)
    render_csv(payload)
    print("готово")


if __name__ == "__main__":
    main()
