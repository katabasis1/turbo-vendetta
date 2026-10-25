"""Палитра-атлас 256×256 (ARCHITECTURE §2: assets/textures/palette_atlas.png) и UV в него.

Раскладка (сетка 16 px):
- строки 0–7 — однотонные клетки 16×16 (до 128 цветов): все цвета STYLE_GUIDE §2 по порядку mf/palette.ALL;
- строки 8–15 — градиенты-полосы 256×16: U = t ∈ [0; 1] вдоль полосы («градиентные атласы» PLAN 1.2).

UV однотонной клетки — её центр: у всех вершин грани одна UV, производные UV = 0, поэтому GPU берёт мип 0
и соседние клетки не просачиваются ни на каком расстоянии. UV градиента — центр строки по V, t по U
с отступом 2 px от краёв.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import palette

SIZE = 256
CELL = 16
COLS = SIZE // CELL            # 16
FLAT_ROWS = 8
RAMP_ROW0 = 8
RAMP_PAD = 2.0                 # px от края полосы


@dataclass(frozen=True)
class Ramp:
    name: str
    stops: tuple[tuple[float, str], ...]   # (t, цвет палитры); между стопами — линейно, равные t = жёсткая граница
    note: str = ""


# Градиенты. Цвета — только из палитры.
RAMPS: tuple[Ramp, ...] = (
    Ramp("glass_blik", ((0.0, "glass"), (0.50, "glass"), (0.50, "concrete_light"), (0.62, "concrete_light"),
                        (0.62, "glass"), (1.0, "glass")),
         "стекло §2.3: тёмное + одна жёсткая полоса блика; t — диагональ по стеклу"),
    Ramp("asphalt", ((0.0, "asphalt_far"), (1.0, "asphalt_near")), "асфальт §2.2: даль → у камеры"),
    Ramp("sky", ((0.0, "sky_zenith"), (0.25, "sky_top"), (0.5, "sky_mid"), (0.75, "sky_coral"), (1.0, "sky_amber")),
         "небо-полусфера, запасной вариант S-14"),
    Ramp("trail", ((0.0, "trail_head"), (1.0, "trail_tail")), "шлейф огней §2.3: голова → хвост"),
    Ramp("concrete3", ((0.0, "concrete_light"), (1 / 3, "concrete_light"), (1 / 3, "concrete_mid"), (2 / 3, "concrete_mid"),
                       (2 / 3, "concrete_shadow"), (1.0, "concrete_shadow")), "бетон в 3 тона §2.2, ступенями"),
    Ramp("pearl_sill", ((0.0, "pearl_light"), (0.7, "pearl_light"), (1.0, "pearl_mid")),
         "перламутр: к порогу темнее (запечённое затенение снизу)"),
    Ramp("rival_sill", ((0.0, "rival_light"), (0.7, "rival_light"), (1.0, "rival_mid")), "то же для синего соперника"),
)


def _flat_names() -> list[str]:
    names = list(palette.ALL.keys())
    if len(names) > COLS * FLAT_ROWS:
        raise ValueError("палитра не помещается в 128 клеток")
    return names


FLAT = {n: i for i, n in enumerate(_flat_names())}
RAMP_INDEX = {r.name: i for i, r in enumerate(RAMPS)}


def flat_uv(name: str) -> tuple[float, float]:
    """UV центра однотонной клетки. Имя — из палитры или псевдоним (mf/palette.ALIASES)."""
    hexv = palette.resolve(name)
    key = next((k for k, v in palette.ALL.items() if v == hexv), None)
    if key is None or key not in FLAT:
        raise KeyError(f"нет клетки для «{name}»")
    i = FLAT[key]
    cx, cy = i % COLS, i // COLS
    return ((cx + 0.5) * CELL / SIZE, (cy + 0.5) * CELL / SIZE)


def ramp_uv(name: str, t: float) -> tuple[float, float]:
    if name not in RAMP_INDEX:
        raise KeyError(f"нет градиента «{name}» (mf/atlas.RAMPS)")
    t = min(1.0, max(0.0, t))
    row = RAMP_ROW0 + RAMP_INDEX[name]
    u = (RAMP_PAD + t * (SIZE - 2 * RAMP_PAD)) / SIZE
    return (u, (row + 0.5) * CELL / SIZE)


def is_ramp(name: str) -> bool:
    return name in RAMP_INDEX


def uv(name: str, t: float | None = None) -> tuple[float, float]:
    return ramp_uv(name, 0.5 if t is None else t) if is_ramp(name) else flat_uv(name)


def _ramp_color(r: Ramp, t: float) -> tuple[float, float, float]:
    st = r.stops
    if t <= st[0][0]:
        return palette.hex_rgb(palette.resolve(st[0][1]))
    for (t0, c0), (t1, c1) in zip(st, st[1:]):
        if t0 <= t <= t1 and t1 > t0:
            a, b = palette.hex_rgb(palette.resolve(c0)), palette.hex_rgb(palette.resolve(c1))
            k = (t - t0) / (t1 - t0)
            return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))
    return palette.hex_rgb(palette.resolve(st[-1][1]))


def render_image():
    """Атлас как PIL.Image RGBA (альфа = 255 везде; резерв под маску блика)."""
    from PIL import Image
    img = Image.new("RGBA", (SIZE, SIZE), palette.hex_rgb(palette.resolve("deepest")) + (255,))
    px = img.load()
    for name, i in FLAT.items():
        rgb = palette.hex_rgb(palette.ALL[name])
        x0, y0 = (i % COLS) * CELL, (i // COLS) * CELL
        for y in range(y0, y0 + CELL):
            for x in range(x0, x0 + CELL):
                px[x, y] = rgb + (255,)
    for r in RAMPS:
        y0 = (RAMP_ROW0 + RAMP_INDEX[r.name]) * CELL
        for x in range(SIZE):
            t = min(1.0, max(0.0, (x + 0.5 - RAMP_PAD) / (SIZE - 2 * RAMP_PAD)))
            rgb = tuple(int(round(v)) for v in _ramp_color(r, t))
            for y in range(y0, y0 + CELL):
                px[x, y] = rgb + (255,)
    return img


def write_png(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    render_image().save(path, format="PNG", optimize=False, compress_level=9)


def sample(u: float, v: float) -> tuple[int, int, int]:
    """Цвет атласа по UV (для превью и проверок)."""
    global _IMG
    try:
        _IMG
    except NameError:
        _IMG = render_image().convert("RGB").load()
    x = min(SIZE - 1, max(0, int(u * SIZE)))
    y = min(SIZE - 1, max(0, int(v * SIZE)))
    return _IMG[x, y]
