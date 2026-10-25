#!/usr/bin/env python3
"""Сравнение модели машины с утверждёнными референсами (D-019 п. 5, BRIEF §7).

    python3 tools/meshforge/compare.py car_01

Выход (docs/art/cars/<имя>/):
  <имя>_model_vs_ref.png   пары «референс | модель»: 3/4 спереди, погоня 3/4 сзади, бок, корма —
                           модель с тушевым контуром (STYLE_GUIDE v1.1, D-018) и студийным светом
  <имя>_overlay_side.png   вид сбоку поверх ортогонального листа ref_03 в его масштабе (297,95 px/м);
                           ось z модели растянута обратно в метры подложки (zn_of модели) — видно,
                           где форма расходится с рисунком. Красное — модель, под ней — референс.
Игровой свет (закат спереди) — в docs/art/models/<имя>_views.png (build.py). Здесь свет студийный: форма.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import build  # noqa: E402
from mf import palette  # noqa: E402
from mf import preview as pv  # noqa: E402

# калибровка ref_03 (docs/art/cars/car_01/src/make_board.py)
S_NOSE, S_GROUND, S_PPM = 84, 436, (1395 - 84) / 4.40
R_CX, R_W, R_GROUND = (458 + 887) / 2, 887 - 458, 754          # корма на листе: рамка по аркам 1,92 м


def scene(name):
    mod = build.load(name)
    model = mod.build()
    wm = build.load(model.meta["wheel"])
    tones = pv.car_tones("pearl_light", "pearl_mid", "pearl_shadow")
    body_p = {"atlas": pv.mat_params(tones, rim=0.35, spec=0.6), "emissive": pv.EMISSIVE}
    wheel_p = {"atlas": pv.mat_params(tones, spec=0.6)}
    items = [(n.surfaces(), pv.translate(), body_p) for n in model.nodes]
    ws = wm.build().nodes[0].surfaces()
    for k, (x, y, z) in model.anchors.items():
        if k.startswith("wheel_"):
            items.append((ws, pv.translate(x, y, z, 180 if x < 0 else 0), wheel_p))
    return mod, model, items


def fit(im, size):
    im = im.convert("RGB")
    k = min(size[0] / im.width, size[1] / im.height)
    im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
    c = Image.new("RGB", size, palette.hex_rgb(palette.resolve("ui_panel")))
    c.paste(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return c


def main(name: str) -> int:
    mod, model, items = scene(name)
    g = model.meta["ground_y"]
    ref = ROOT / "docs/art/cars" / name / "ref"
    out = ROOT / "docs/art/cars" / name
    T = (768, 432)
    ortho = Image.open(ref / f"{name}_ref_03_ortho.png").convert("RGB")
    side_ref = ortho.crop((40, 60, 1340 + 40, 60 + 400))
    rear_ref = ortho.crop((410, 455, 935, 715))
    shots = [
        ("3/4 спереди", Image.open(ref / f"{name}_ref_01_hero.png"),
         dict(eye=(-4.3, g + 1.25, -5.2), target=(0.1, g + 0.5, 0.1), fov_deg=27, sun_dir=(-0.8, 0.7, -0.6))),
        ("погоня 3/4 сзади", Image.open(ref / f"{name}_ref_02_chase.png"),
         dict(eye=(1.5, g + 1.75, 6.4), target=(0, g + 0.6, 0.2), fov_deg=28, sun_dir=(0.5, 0.8, 0.9))),
        ("бок", side_ref, dict(eye=(-12, g + 0.62, 0.05), target=(0, g + 0.62, 0.05), ortho_height=2.5,
                               sun_dir=(-0.9, 0.7, -0.3))),
        ("корма", rear_ref, dict(eye=(0, g + 0.62, 12), target=(0, g + 0.62, 0), ortho_height=1.45,
                                 sun_dir=(0.4, 0.8, 0.9))),
    ]
    rows = []
    for title, rim, kw in shots:
        im = pv.render(items, size=T, ss=2, ground_y=g, shadow_box=(1.1, 2.5), outline=2.0, **kw)
        pair = Image.new("RGB", (T[0] * 2 + 12, T[1]), palette.hex_rgb(palette.resolve("ui_panel")))
        pair.paste(pv.label(fit(rim, T), f"референс — {title}"), (0, 0))
        pair.paste(pv.label(im, f"модель — {title}"), (T[0] + 12, 0))
        rows.append(pair)
    sheet = Image.new("RGB", (rows[0].width, sum(r.height + 12 for r in rows)), palette.hex_rgb(palette.resolve("ui_panel")))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 12
    sheet.save(out / f"{name}_model_vs_ref.png", optimize=True)
    # --- наложение сбоку в масштабе ref_03
    zn_of, zr = getattr(mod, "zn_of", None), getattr(mod, "zr", None)
    length = 4.40
    W, H = int(4.9 * S_PPM), int(1.5 * S_PPM)
    znose = zr(0.0) if zr else -length / 2
    cz = znose + 2.40
    im = pv.render(items, size=(W, H), ss=1, ortho_height=1.5, eye=(-12, g + 0.75, cz), target=(0, g + 0.75, cz),
                   background=False, outline=1.0, sun_dir=(-0.9, 0.7, -0.3))
    a = np.asarray(im).astype(float)
    cov = a.sum(axis=2) > 0
    # столбец пикселя → z модели → метры подложки
    xs = np.arange(W) + 0.5
    zm = cz + (xs - W / 2) / S_PPM
    zn = np.array([zn_of(z) for z in zm]) if zn_of else zm - znose
    # обратная выборка: для каждого столбца подложки ищем столбец модели
    canvas = ortho.copy()
    base = np.asarray(canvas).astype(float)
    dst_x = np.arange(base.shape[1])
    zn_dst = (dst_x - S_NOSE) / S_PPM
    src_x = np.interp(zn_dst, zn, xs - 0.5, left=-1, right=-1).round().astype(int)
    y_top = int(S_GROUND - (g + 0.75 - g + 0.75) * S_PPM)      # верх кадра модели в пикселях листа
    red = np.array([232, 54, 79], dtype=float)
    for yy in range(H):
        ty = y_top + yy
        if not (0 <= ty < base.shape[0]):
            continue
        ok = (src_x >= 0) & (src_x < W)
        sx = np.clip(src_x, 0, W - 1)
        m = ok & cov[yy, sx]
        row = a[yy, sx]
        lum = row.mean(axis=1, keepdims=True) / 255
        tint = red * (0.35 + 0.65 * lum)
        base[ty, m] = base[ty, m] * 0.45 + tint[m] * 0.55
    over = Image.fromarray(base.astype(np.uint8)).crop((40, 40, 1420, 470))
    d = ImageDraw.Draw(over)
    from PIL import ImageFont
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
    d.text((10, 8), f"{name}: модель (красное) поверх ref_03, z растянута в метры подложки", fill=(27, 16, 48), font=fnt)
    over.save(out / f"{name}_overlay_side.png", optimize=True)
    print(f"→ {out.relative_to(ROOT)}/{name}_model_vs_ref.png, {name}_overlay_side.png")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "car_01"))
