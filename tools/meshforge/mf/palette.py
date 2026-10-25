"""Цвета из STYLE_GUIDE.md §2 (v1, D-013). Имя → HEX. Правка цвета = правка гайда (новая версия + D-xxx).

Чистые #000000 и нейтрально-серые запрещены (§2): проверка — palette_ok().
"""
from __future__ import annotations

# §2.1 небо и свет
SKY = {
    "sky_zenith": "#24163F", "sky_top": "#46286E", "sky_mid": "#9D4488", "sky_coral": "#EB7B93",
    "sky_amber": "#F6B26B", "sun": "#FFF1D6", "cloud_body": "#6A3A80", "cloud_edge": "#F3A0A8",
}
# §2.2 мир
WORLD = {
    "city_far": "#7A4A86", "city_near": "#3A2260", "window_warm": "#FFC870", "window_pink": "#FF8FC8",
    "window_cyan": "#8FE8FF", "concrete_light": "#A390C0", "concrete_mid": "#715194", "concrete_shadow": "#402A69",
    "asphalt_far": "#6A3F7C", "asphalt_near": "#2E1D47", "marking": "#EEC2E4", "deepest": "#1B1030",
}
# §2.3 машины
CARS = {
    "pearl_light": "#FAF2F4", "pearl_mid": "#D9B0BE", "pearl_shadow": "#9E6396", "hero_stripe": "#E8364F",
    "rival_light": "#4448C8", "rival_mid": "#3030B2", "rival_shadow": "#212274", "glass": "#2A1A48",
    "brake": "#FF4F6E", "headlight": "#FFF6E0", "trail_head": "#FF5FA2", "trail_tail": "#B5408E",
}
# §2.4 эффекты (повторы цветов мира не дублируем)
FX = {"flash_core": "#FFFEDA", "flash_edge": "#F4AC5A", "smoke_light": "#D5B1BB", "white": "#FFFFFF"}
# §2.5 интерфейс
UI = {
    "ui_ink": "#130C27", "ui_panel": "#1B1433", "ui_panel_sel": "#2C2050", "ui_text": "#FCF7F9",
    "ui_text2": "#BCA4D1", "ui_cta": "#F13858", "ui_defense": "#54DFFA", "ui_threat": "#FFE45C",
}

ALL: dict[str, str] = {**SKY, **WORLD, **CARS, **FX, **UI}

# Детали машин (STYLE_GUIDE §5: «тёмные диски», стекло, тёмная отделка) — псевдонимы на цвета гайда, новых цветов нет.
ALIASES = {
    "tire": "city_near",          # резина: самый тёмный «живой» лиловый, не чёрный
    "rim": "concrete_shadow",     # тёмный диск
    "hub": "concrete_mid",        # ступица / центр диска
    "trim": "glass",              # чёрная отделка: решётка, нижняя губа бампера, рамки — цвет стекла
    "underbody": "deepest",       # днище, арки изнутри
    "sparks": "window_warm", "smoke_shadow": "concrete_light", "score": "flash_edge",
}


def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def resolve(name: str) -> str:
    """Имя или псевдоним → HEX."""
    seen = set()
    while name in ALIASES:
        if name in seen:
            raise ValueError(f"цикл псевдонимов: {name}")
        seen.add(name)
        name = ALIASES[name]
    if name.startswith("#"):
        return name.upper()
    if name not in ALL:
        raise KeyError(f"цвета «{name}» нет в палитре STYLE_GUIDE §2 (mf/palette.py)")
    return ALL[name]


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c: float) -> float:
    c = max(0.0, c)
    return c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def palette_ok() -> list[str]:
    """Нарушения §2: чистый чёрный и нейтрально-серые (R = G = B, кроме белого)."""
    bad = []
    for k, h in ALL.items():
        r, g, b = hex_rgb(h)
        if (r, g, b) == (0, 0, 0) or (r == g == b and (r, g, b) != (255, 255, 255)):
            bad.append(f"{k} {h}")
    return bad
