"""Офлайн-превью: программный растеризатор с той же формулой, что shaders/cel_lit.gdshader
(3 ступени по N·L к солнцу, сдвиг тени к лиловому, кромка, аниме-блик), в линейном цвете.
Нужен, чтобы видеть модель без движка: ракурсы, лист контактов, тест силуэта (STYLE_GUIDE §11).
Это приближение: без тумана, без теней от геометрии, фон — небо-градиент и асфальт с пятном тени.
"""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageDraw

from . import atlas, palette

# Глобальные uniform из project.godot [shader_globals]
SUN_DIR = np.array([-0.35, 0.25, -0.9])
SUN_COLOR = (1.0, 0.945, 0.839)
SHADOW_TINT = (0.251, 0.165, 0.412)
RIM_COLOR = (0.953, 0.627, 0.659)


def lin(rgb):
    return np.array([palette.srgb_to_linear(c) for c in rgb])


def srgb_img(a: np.ndarray) -> np.ndarray:
    a = np.clip(a, 0, None)
    out = np.where(a <= 0.0031308, a * 12.92, 1.055 * np.power(a, 1 / 2.4) - 0.055)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def car_tones(light: str, mid: str, shadow: str, mix: float = 0.35) -> dict:
    """Тона материала cel_lit под атлас (клетка = светлый тон), чтобы полутон и тень на экране совпали с
    палитрой §2.3. Считается в линейном цвете; результат — sRGB, как пишется в .tres (source_color)."""
    L, M, S = (lin([c / 255 for c in palette.hex_rgb(palette.resolve(x))]) for x in (light, mid, shadow))
    sun = lin(SUN_COLOR)
    tint = lin(SHADOW_TINT)
    t_mid = (M / L) / ((1 + sun) / 2)
    t_sh = ((S / L) - mix * tint) / (1 - mix)
    to = lambda v: tuple(round(palette.linear_to_srgb(float(c)), 3) for c in v)
    return {"tone_light": (1.0, 1.0, 1.0), "tone_mid": to(t_mid), "tone_shadow": to(t_sh), "shadow_tint_mix": mix}


def mat_params(tones: dict | None = None, rim=0.0, spec=0.0) -> dict:
    t = tones or {"tone_light": (1, 1, 1), "tone_mid": (0.72, 0.72, 0.72), "tone_shadow": (0.45, 0.45, 0.45), "shadow_tint_mix": 0.35}
    return {"light": lin(t["tone_light"]), "mid": lin(t["tone_mid"]), "shadow": lin(t["tone_shadow"]),
            "mix": t["shadow_tint_mix"], "rim": rim, "spec": spec, "emissive": False}


EMISSIVE = {"emissive": True}


def _look_at(eye, target, up=(0, 1, 0)):
    eye, target, up = map(lambda v: np.array(v, dtype=float), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f)
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return eye, r, u, f


def _atlas_lin():
    img = np.asarray(atlas.render_image().convert("RGB"), dtype=np.float64) / 255.0
    return np.where(img <= 0.04045, img / 12.92, ((img + 0.055) / 1.055) ** 2.4)


_ATLAS = None


def render(items, eye, target, fov_deg=40.0, size=(960, 600), ss=2, ground_y=None, shadow_box=None,
           ortho_height=None, background=True, outline=0.0, sun_dir=None):
    """items: [(surfaces, M(4×4), {'atlas': params, 'emissive': EMISSIVE})]. → PIL.Image RGB.
    ortho_height — ортографическая камера (высота кадра в метрах) для вида сбоку/сзади/сверху.
    outline — толщина тушевого контура в пикселях итогового кадра (STYLE_GUIDE v1.1 §3, D-018): линия по краю
    силуэта и по разрывам глубины (то, что даст вывернутая оболочка в игре), цвет `deepest`. 0 — без контура.
    sun_dir — направление на солнце вместо глобального SUN_DIR (студийный свет для сравнения с референсом)."""
    global _ATLAS
    if _ATLAS is None:
        _ATLAS = _atlas_lin()
    W, H = size[0] * ss, size[1] * ss
    eye, R, U, F = _look_at(eye, target)
    aspect = W / H
    tanf = math.tan(math.radians(fov_deg) / 2)
    zbuf = np.full((H, W), np.inf)
    nbuf = np.zeros((H, W, 3)); uvbuf = np.zeros((H, W, 2)); pbuf = np.zeros((H, W, 3))
    mbuf = np.full((H, W), -1, dtype=np.int32)
    mats = []
    for surfaces, M, params in items:
        for mat, s in surfaces.items():
            mats.append(params[mat])
            mid = len(mats) - 1
            P = s["positions"].astype(np.float64) @ M[:3, :3].T + M[:3, 3]
            N = s["normals"].astype(np.float64) @ np.linalg.inv(M[:3, :3]).T
            N /= np.linalg.norm(N, axis=1, keepdims=True)
            UV = s["uvs"].astype(np.float64)
            rel = P - eye
            xc, yc, zc = rel @ R, rel @ U, rel @ F           # zc — глубина вперёд
            if ortho_height is None:
                sx = (xc / (zc * tanf * aspect) * 0.5 + 0.5) * W
                sy = (0.5 - yc / (zc * tanf) * 0.5) * H
            else:
                hh = ortho_height / 2
                sx = (xc / (hh * aspect) * 0.5 + 0.5) * W
                sy = (0.5 - yc / hh * 0.5) * H
            idx = s["indices"].reshape(-1, 3)
            for a, b, c in idx:
                if min(zc[a], zc[b], zc[c]) <= 0.05:
                    continue
                x0, y0, x1, y1, x2, y2 = sx[a], sy[a], sx[b], sy[b], sx[c], sy[c]
                area = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
                if area >= 0:            # экран y вниз: лицевая (против часовой в мире) даёт area < 0
                    continue
                minx, maxx = int(max(0, math.floor(min(x0, x1, x2)))), int(min(W - 1, math.ceil(max(x0, x1, x2))))
                miny, maxy = int(max(0, math.floor(min(y0, y1, y2)))), int(min(H - 1, math.ceil(max(y0, y1, y2))))
                if minx > maxx or miny > maxy:
                    continue
                gx, gy = np.meshgrid(np.arange(minx, maxx + 1) + 0.5, np.arange(miny, maxy + 1) + 0.5)
                w0 = ((x1 - gx) * (y2 - gy) - (x2 - gx) * (y1 - gy)) / area
                w1 = ((x2 - gx) * (y0 - gy) - (x0 - gx) * (y2 - gy)) / area
                w2 = 1 - w0 - w1
                inside = (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
                if not inside.any():
                    continue
                if ortho_height is None:   # перспективно-правильная интерполяция
                    q0, q1, q2 = w0 / zc[a], w1 / zc[b], w2 / zc[c]
                    qs = q0 + q1 + q2
                    q0, q1, q2 = q0 / qs, q1 / qs, q2 / qs
                    depth = 1 / qs
                else:
                    q0, q1, q2 = w0, w1, w2
                    depth = w0 * zc[a] + w1 * zc[b] + w2 * zc[c]
                sub = zbuf[miny:maxy + 1, minx:maxx + 1]
                m = inside & (depth < sub)
                if not m.any():
                    continue
                sub[m] = depth[m]
                for buf, attr in ((nbuf, N), (pbuf, P)):
                    v = q0[..., None] * attr[a] + q1[..., None] * attr[b] + q2[..., None] * attr[c]
                    buf[miny:maxy + 1, minx:maxx + 1][m] = v[m]
                v = q0[..., None] * UV[a] + q1[..., None] * UV[b] + q2[..., None] * UV[c]
                uvbuf[miny:maxy + 1, minx:maxx + 1][m] = v[m]
                mbuf[miny:maxy + 1, minx:maxx + 1][m] = mid
    # ---------------- фон
    img = np.zeros((H, W, 3))
    py, px = np.mgrid[0:H, 0:W] + 0.5
    if ortho_height is None:
        dx = (px / W * 2 - 1) * tanf * aspect
        dy = (1 - py / H * 2) * tanf
        dirs = R[None, None] * dx[..., None] + U[None, None] * dy[..., None] + F[None, None]
        origins = np.broadcast_to(eye, dirs.shape)
    else:
        hh = ortho_height / 2
        origins = eye + R[None, None] * ((px / W * 2 - 1) * hh * aspect)[..., None] + U[None, None] * ((1 - py / H * 2) * hh)[..., None]
        dirs = np.broadcast_to(F, origins.shape)
    dirs = dirs / np.linalg.norm(dirs, axis=2, keepdims=True)
    if background:
        el = np.clip(dirs[..., 1], -1, 1)
        sky_stops = [(-0.05, "sky_amber"), (0.06, "sky_coral"), (0.18, "sky_mid"), (0.40, "sky_top"), (0.8, "sky_zenith")]
        cols = [lin([c / 255 for c in palette.hex_rgb(palette.resolve(n))]) for _t, n in sky_stops]
        ts = [t for t, _n in sky_stops]
        for ch in range(3):
            img[..., ch] = np.interp(el, ts, [c[ch] for c in cols])
        if ground_y is not None:
            hit = dirs[..., 1] < -1e-6
            t = np.where(hit, (ground_y - origins[..., 1]) / np.where(hit, dirs[..., 1], -1), np.inf)
            gp = origins + dirs * t[..., None]
            dist = np.linalg.norm(gp - eye, axis=2)
            near, far = lin([c / 255 for c in palette.hex_rgb(palette.resolve("asphalt_near"))]), lin([c / 255 for c in palette.hex_rgb(palette.resolve("asphalt_far"))])
            k = np.clip((dist - 4) / 60, 0, 1)[..., None]
            gcol = near * (1 - k) + far * k
            if shadow_box is not None:
                hx, hz = shadow_box
                e = (gp[..., 0] / hx) ** 2 + (gp[..., 2] / hz) ** 2
                sh = np.clip(1.2 - e, 0, 1)[..., None] * 0.6
                gcol = gcol * (1 - sh) + lin([c / 255 for c in palette.hex_rgb(palette.resolve("deepest"))]) * sh
            g = hit & np.isfinite(t)
            img[g] = gcol[g]
    # ---------------- затенение (как cel_lit)
    sd = SUN_DIR if sun_dir is None else np.asarray(sun_dir, dtype=float)
    l = sd / np.linalg.norm(sd)
    sun, tint, rimc = lin(SUN_COLOR), lin(SHADOW_TINT), lin(RIM_COLOR)
    tex_xy = np.clip((uvbuf * atlas.SIZE).astype(int), 0, atlas.SIZE - 1)
    albedo = _ATLAS[tex_xy[..., 1], tex_xy[..., 0]]
    n = nbuf / np.maximum(np.linalg.norm(nbuf, axis=2, keepdims=True), 1e-9)
    view = eye - pbuf if ortho_height is None else np.broadcast_to(-F, pbuf.shape)
    view = view / np.maximum(np.linalg.norm(view, axis=2, keepdims=True), 1e-9)

    def sstep(e0, e1, x):
        t = np.clip((x - e0) / (e1 - e0), 0, 1)
        return t * t * (3 - 2 * t)

    for mid, prm in enumerate(mats):
        m = mbuf == mid
        if not m.any():
            continue
        if prm.get("emissive"):
            img[m] = albedo[m] * prm.get("energy", 1.0)
            continue
        ndl = n[m] @ l
        to_light = sstep(0.55 - 0.03, 0.55 + 0.03, ndl)[:, None]
        to_mid = sstep(0.05 - 0.03, 0.05 + 0.03, ndl)[:, None]
        c_light = prm["light"] * sun
        c_mid = prm["mid"] * (1 + sun) / 2
        c_sh = prm["shadow"] * (1 - prm["mix"]) + tint * prm["mix"]
        c = c_sh * (1 - to_mid) + (c_mid * (1 - to_light) + c_light * to_light) * to_mid
        c = c * albedo[m]
        fres = 1 - np.clip(np.sum(n[m] * view[m], axis=1), 0, 1)
        c = c * (1 - (sstep(0.58, 0.62, fres) * prm["rim"])[:, None]) + rimc * (sstep(0.58, 0.62, fres) * prm["rim"])[:, None]
        hv = l + view[m]
        hv /= np.maximum(np.linalg.norm(hv, axis=1, keepdims=True), 1e-9)
        spec = np.sum(n[m] * hv, axis=1)
        c = c + (sstep(0.925, 0.935, spec) * prm["spec"])[:, None]
        img[m] = c
    if outline > 0:
        img = _ink(img, zbuf, ortho_height is not None, outline * ss)
    out = Image.fromarray(srgb_img(img), "RGB")
    return out.resize(size, Image.LANCZOS) if ss > 1 else out


def _ink(img, zbuf, ortho, px):
    """Контур: край покрытия + разрыв глубины (относительный в перспективе, абсолютный в орто), утолщение до px."""
    cov = np.isfinite(zbuf)
    z = np.where(cov, zbuf, 1e6)
    edge = np.zeros(cov.shape, dtype=bool)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        a = z
        b = np.roll(np.roll(z, dy, 0), dx, 1)
        ca, cb = cov, np.roll(np.roll(cov, dy, 0), dx, 1)
        near = np.minimum(a, b)
        jump = np.abs(a - b) > (0.12 if ortho else 0.035 * near)
        e = (ca != cb) | (ca & cb & jump)
        # линию рисуем на ближней стороне разрыва (как оболочка вокруг ближнего тела)
        edge |= e & (a <= b)
        edge |= np.roll(np.roll(e & (b < a), -dy, 0), -dx, 1)
    r = max(1, int(round(px / 2)))
    thick = edge.copy()
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    for dy, dx in zip(yy.ravel(), xx.ravel()):
        if dy * dy + dx * dx <= r * r and (dy or dx):
            thick |= np.roll(np.roll(edge, dy, 0), dx, 1)
    ink = lin([c / 255 for c in palette.hex_rgb(palette.resolve("deepest"))])
    img = img.copy()
    img[thick] = ink
    return img


def silhouette(img_rgb: Image.Image, target_h: int, bg_ref: Image.Image) -> Image.Image:
    """Уменьшить до target_h по высоте объекта (тест читаемости §11) и увеличить «пикселями» ×4 для просмотра."""
    w, h = img_rgb.size
    small = img_rgb.resize((max(1, round(w * target_h / h)), target_h), Image.BOX)
    return small.resize((small.width * 4, small.height * 4), Image.NEAREST)


_FONT = None


def _font():
    """Шрифт с кириллицей для подписей превью (системный Noto Sans; нет — встроенный PIL, латиница)."""
    global _FONT
    if _FONT is None:
        from PIL import ImageFont
        for f in ("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
            try:
                _FONT = ImageFont.truetype(f, 14)
                break
            except OSError:
                continue
        else:
            _FONT = ImageFont.load_default()
    return _FONT


def label(img: Image.Image, text: str) -> Image.Image:
    d = ImageDraw.Draw(img)
    f = _font()
    x0, y0, x1, y1 = d.textbbox((6, 3), text, font=f)
    d.rectangle([0, 0, x1 + 6, y1 + 4], fill=(19, 12, 39))
    d.text((6, 3), text, fill=(252, 247, 249), font=f)
    return img


def translate(x=0.0, y=0.0, z=0.0, rot_y_deg=0.0) -> np.ndarray:
    a = math.radians(rot_y_deg)
    M = np.eye(4)
    M[:3, :3] = [[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]]
    M[:3, 3] = (x, y, z)
    return M
