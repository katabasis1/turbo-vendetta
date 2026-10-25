#!/usr/bin/env python3
"""MeshForge: сборка моделей → .glb (D-005, PLAN 1.2).

    python3 tools/meshforge/build.py              собрать всё: атлас, .glb, паспорта, превью
    python3 tools/meshforge/build.py car_01       только эта модель (и её колёса)
    python3 tools/meshforge/build.py --check      ничего не писать: пересобрать в памяти и сравнить с файлами
    python3 tools/meshforge/build.py --no-preview без рендера превью (быстро)

Результат (пути от корня проекта):
  assets/textures/palette_atlas.png           палитра-атлас 256² (mf/atlas.py)
  assets/models/<…>.glb                       путь задаёт Model.out
  docs/art/models/<имя>_report.txt            паспорт: треугольники, размеры, замкнутость
  docs/art/models/<имя>_views.png             превью cel-shading: 3/4 спереди, 3/4 сзади, бок, корма
  docs/art/models/<имя>_silhouette.png        тест силуэта STYLE_GUIDE §5 (64 px бок и 3/4, 32 px корма)
Вывод детерминирован: одни исходники → одни байты .glb и атласа (--check это проверяет).
Код возврата: 0 — всё в порядке; 1 — ошибка паспорта или --check нашёл расхождение.
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

from mf import atlas, gltf, outline, palette, report  # noqa: E402

MODELS = ["wheel_a", "car_01"]          # порядок сборки: колёса раньше машин
ATLAS = "assets/textures/palette_atlas.png"
DOCS = "docs/art/models"
GENERATOR = "MeshForge (tools/meshforge) — Turbo Vendetta"


def load(name: str):
    return importlib.import_module(f"models.{name}")


def rel_uri(glb_out: str) -> str:
    """Путь к атласу относительно папки .glb (glTF: uri относительно файла)."""
    depth = len(Path(glb_out).parent.parts)
    return "../" * depth + ATLAS


def glb_bytes(model) -> bytes:
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "m.glb"
        return gltf.write_glb(p, glb_nodes(model), rel_uri(model.out), GENERATOR)


def glb_nodes(model) -> list:
    """Узлы .glb: меши модели по порядку, затем оболочки контура `<имя>_outline` (S-19)."""
    nodes = [(n.name, n.surfaces()) for n in model.nodes]
    for n in model.nodes:
        if n.name in model.outline:
            nodes.append((f"{n.name}_outline", outline.hull(n.surfaces())[0]))
    return nodes


def atlas_bytes() -> bytes:
    import io
    buf = io.BytesIO()
    atlas.render_image().save(buf, format="PNG", optimize=False, compress_level=9)
    return buf.getvalue()


def passport(name: str, mod, model, wheel_cache: dict) -> dict:
    extra, hull = 0, None
    if model.meta.get("kind") == "car":
        wm = wheel_cache.setdefault(model.meta["wheel"], load(model.meta["wheel"]))
        wmodel = wm.build()
        model.meta["wheel_r"], model.meta["wheel_w"] = wm.R, wm.W
        extra = 4 * sum(n.tri_count() for n in wmodel.nodes)
        hull = mod.hull_for_checks()
    return report.build_report(model, extra_tris=extra, hull=hull)


def previews(name: str, model, wheel_cache: dict) -> None:
    from PIL import Image
    from mf import preview as pv
    out = ROOT / DOCS
    out.mkdir(parents=True, exist_ok=True)
    if model.meta.get("kind") == "car":
        tones = pv.car_tones("pearl_light", "pearl_mid", "pearl_shadow")
        body_p = {"atlas": pv.mat_params(tones, rim=0.35, spec=0.6), "emissive": pv.EMISSIVE}
        wheel_p = {"atlas": pv.mat_params(tones)}
        wmodel = wheel_cache[model.meta["wheel"]].build()
        ws = wmodel.nodes[0].surfaces()
        hulls = [outline.hull(n.surfaces())[0] for n in model.nodes if n.name in model.outline]
        w_hull = outline.hull(ws)[0] if wmodel.outline else None

        def car_items(ink_px: float) -> list:
            """Модель + колёса по якорям + оболочки контура (ink_px = 0 — без контура)."""
            items = [(n.surfaces(), pv.translate(), body_p) for n in model.nodes]
            if ink_px:
                items += [(h, pv.translate(), {"outline": pv.ink(ink_px)}) for h in hulls]
            for k, (x, y, z) in model.anchors.items():
                if k.startswith("wheel_"):
                    M = pv.translate(x, y, z, 180 if x < 0 else 0)
                    items.append((ws, M, wheel_p))
                    if ink_px and w_hull is not None:
                        items.append((w_hull, M, {"outline": pv.ink(ink_px)}))
            return items

        items = car_items(2.0)
        g = model.meta["ground_y"]
        cy = g + 0.6
        shots = [
            ("3/4 спереди", dict(eye=(-4.6, g + 1.6, -5.6), target=(0, g + 0.55, 0), fov_deg=36)),
            ("3/4 сзади (камера погони)", dict(eye=(4.2, g + 2.0, 6.4), target=(0, g + 0.6, 0), fov_deg=36)),
            ("бок", dict(eye=(12, cy, 0), target=(0, cy, 0), ortho_height=3.0)),
            ("корма", dict(eye=(0, cy, 12), target=(0, cy, 0), ortho_height=1.8)),
        ]
        tiles = []
        for title, kw in shots:
            im = pv.render(items, size=(640, 400), ss=2, ground_y=g, shadow_box=(1.1, 2.5), **kw)
            tiles.append(pv.label(im, title))
        sheet = Image.new("RGB", (1280, 800))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 2) * 640, (i // 2) * 400))
        sheet.save(out / f"{name}_views.png", optimize=True)
        # тест силуэта §5: заливка тёмным, высота машины 64 px (бок, 3/4); корма 32 px — по огням
        ink = palette.hex_rgb(palette.resolve("ui_ink"))
        bg = palette.hex_rgb(palette.resolve("sky_coral"))
        sil = []
        for title, kw, h_px, fill in (
            ("бок, 64 px", dict(eye=(12, cy, 0), target=(0, cy, 0), ortho_height=3.0), 64, True),
            ("3/4 сзади, 64 px", dict(eye=(4.2, g + 2.0, 6.4), target=(0, g + 0.6, 0), fov_deg=36), 64, True),
            ("корма, 32 px", dict(eye=(0, g + 1.3, 9), target=(0, g + 0.55, 0), fov_deg=20), 32, False),
        ):
            mask_im = pv.render(items, size=(640, 400), ss=1, background=False, **kw)
            m = mask_im.convert("L").point(lambda v: 255 if v > 0 else 0)
            bb = m.getbbox()
            if fill:
                im = Image.composite(Image.new("RGB", m.size, ink), Image.new("RGB", m.size, bg), m)
            else:
                im = pv.render(car_items(1.5), size=(640, 400), ss=1, ground_y=g, shadow_box=(1.1, 2.5), **kw)
            crop = im.crop(bb)
            k = h_px / crop.height
            small = crop.resize((max(1, round(crop.width * k)), h_px), Image.BOX)
            big = small.resize((small.width * 4, small.height * 4), Image.NEAREST)
            canvas = Image.new("RGB", (big.width + 24, big.height + 48), bg)
            canvas.paste(big, (12, 36))
            sil.append(pv.label(canvas, title))
        W = sum(s.width for s in sil) + 20 * (len(sil) + 1)
        H = max(s.height for s in sil) + 40
        sheet = Image.new("RGB", (W, H), palette.hex_rgb(palette.resolve("ui_panel")))
        x = 20
        for s in sil:
            sheet.paste(s, (x, 20))
            x += s.width + 20
        sheet.save(out / f"{name}_silhouette.png", optimize=True)
    elif model.meta.get("kind") == "wheel":
        prm = {"atlas": pv.mat_params(pv.car_tones("pearl_light", "pearl_mid", "pearl_shadow"))}
        items = [(n.surfaces(), pv.translate(), prm) for n in model.nodes]
        items += [(outline.hull(n.surfaces())[0], pv.translate(), {"outline": pv.ink(2.0)})
                  for n in model.nodes if n.name in model.outline]
        tiles = []
        for title, eye in (("снаружи (+X)", (1.6, 0.25, 0.9)), ("изнутри (−X)", (-1.6, 0.25, -0.9))):
            im = pv.render(items, eye=eye, target=(0, 0, 0), fov_deg=30, size=(400, 400), ss=2)
            tiles.append(pv.label(im, title))
        sheet = Image.new("RGB", (800, 400))
        for i, t in enumerate(tiles):
            sheet.paste(t, (i * 400, 0))
        sheet.save(out / f"{name}_views.png", optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("models", nargs="*", help="имена из models/ (по умолчанию все)")
    ap.add_argument("--check", action="store_true", help="сравнить с файлами, ничего не писать")
    ap.add_argument("--no-preview", action="store_true")
    a = ap.parse_args()
    names = a.models or MODELS
    bad = palette.palette_ok()
    if bad:
        print("ОШИБКА палитры (§2: чёрный/серый):", ", ".join(bad))
        return 1
    fails = 0
    ab = atlas_bytes()
    ap_ = ROOT / ATLAS
    if a.check:
        if not ap_.exists() or ap_.read_bytes() != ab:
            print(f"РАСХОЖДЕНИЕ: {ATLAS} не совпадает со сборкой — запустить build.py")
            fails += 1
    else:
        ap_.parent.mkdir(parents=True, exist_ok=True)
        ap_.write_bytes(ab)
        print(f"атлас → {ATLAS} ({len(ab)} байт)")
    wheel_cache: dict = {}
    for name in names:
        mod = load(name)
        if name.startswith("wheel"):
            wheel_cache[name] = mod
        model = mod.build()
        rep = passport(name, mod, model, wheel_cache)
        text = report.format_report(rep)
        data = glb_bytes(model)
        out = ROOT / model.out
        if a.check:
            if not out.exists() or out.read_bytes() != data:
                print(f"РАСХОЖДЕНИЕ: {model.out} не совпадает со сборкой — запустить build.py {name}")
                fails += 1
            if rep["errors"]:
                print(text)
                fails += 1
            continue
        print(text)
        if rep["errors"]:
            print(f"{name}: .glb не записан — исправить ошибки паспорта")
            fails += 1
            continue
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        gltf.read_glb(out)                       # перечитать и проверить по спецификации
        (ROOT / DOCS).mkdir(parents=True, exist_ok=True)
        (ROOT / DOCS / f"{name}_report.txt").write_text(text + "\n", encoding="utf-8")
        print(f"→ {model.out} ({len(data)} байт), паспорт {DOCS}/{name}_report.txt")
        if not a.no_preview:
            previews(name, model, wheel_cache)
            print(f"→ превью {DOCS}/{name}_*.png")
    if a.check:
        print("meshforge check ok" if not fails else f"meshforge check: расхождений/ошибок {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
