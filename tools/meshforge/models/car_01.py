"""Машина №1 — дрифт-купе «клин» (STYLE_GUIDE §5: длинный капот, низкая крыша, кузов-клин; кадры стиля 0.3).

Перламутр + красная полоса героя по центру (капот, крыша, крышка багажника), чёрные стойки и стекло
«в обхват», тёмные пороги. Корма (§5: у каждой машины своя): тёмная панель во всю ширину и две широкие
прямоугольные секции стоп-сигналов, как в утверждённых кадрах.

Размеры (§5): длина 4.40, ширина 1.80 (с зеркалами 1.94), высота 1.25, колёса Ø0.65,
база 2.65 (оси z = −1.35 / +1.30), колея ±0.78 — совпадают с узлами WheelPivot (ARCHITECTURE §8.5).
Начало координат = корень машины; земля на y = −0.235 (центр колеса y = 0.09).

Сечение — правая половина (x ≥ 0), 11 точек сверху вниз:
 0 центр крыши/капота · 1 край полосы · 2 кромка крыши (или капота) · 3 пояс (низ стёкол) · 4 плечо
 5 самое широкое место · 6 порог сверху · 7 порог снаружи · 8 порог внутри · 9 днище у арки · 10 центр днища
Арки колёс поднимают точки 5–8 до дуги (потолок арки), точка 9 остаётся на днище → внутренняя стенка арки.
"""
from __future__ import annotations

import math

from mf import loft
from mf.mesh import Mesh
from mf.model import Model

Y0 = -0.235                 # земля
WHEEL_R = 0.325
HUB_H = WHEEL_R             # высота центра колеса над землёй
AXLES = (-1.35, 1.30)       # z передней и задней оси
TRACK_X = 0.78
ARCH_R = 0.375              # радиус выреза арки (шина 0.325 + зазор)
STRIPE_X = 0.13             # половина ширины полосы героя

# Ключевые сечения: z → (ht, (x,h) точек 2..6, x_o, floor). h — высота над землёй.
#        z      ht     2 кромка        3 пояс          4 плечо         5 широкое       6 порог      x_o   днище
KEYS = [
    (-2.20, 0.56, (0.50, 0.555), (0.64, 0.550), (0.74, 0.540), (0.79, 0.420), (0.77, 0.270), 0.73, 0.22),  # K0 нос (торец, фаска)
    (-2.14, 0.62, (0.52, 0.615), (0.70, 0.610), (0.82, 0.600), (0.865, 0.44), (0.85, 0.240), 0.81, 0.17),  # K1
    (-1.95, 0.68, (0.54, 0.675), (0.74, 0.668), (0.86, 0.655), (0.89, 0.480), (0.88, 0.240), 0.85, 0.15),  # K2 капот спереди
    (-0.80, 0.86, (0.56, 0.852), (0.77, 0.842), (0.88, 0.800), (0.90, 0.550), (0.89, 0.250), 0.86, 0.14),  # K3 низ лобового
    (0.10, 1.25, (0.57, 1.220), (0.81, 0.905), (0.885, 0.82), (0.90, 0.560), (0.89, 0.250), 0.86, 0.14),  # K4 верх лобового
    (0.80, 1.25, (0.56, 1.215), (0.81, 0.905), (0.885, 0.82), (0.90, 0.560), (0.89, 0.250), 0.86, 0.14),  # K5 конец крыши
    (1.20, 1.07, (0.54, 1.045), (0.80, 0.895), (0.885, 0.83), (0.90, 0.570), (0.89, 0.255), 0.86, 0.14),  # K6 стойка C
    (1.62, 0.905, (0.55, 0.900), (0.77, 0.890), (0.875, 0.85), (0.90, 0.580), (0.89, 0.260), 0.86, 0.15),  # K7 низ заднего стекла
    (2.10, 0.93, (0.55, 0.928), (0.74, 0.918), (0.85, 0.870), (0.88, 0.580), (0.86, 0.280), 0.82, 0.18),  # K8 «утиный хвост»
    (2.20, 0.88, (0.52, 0.877), (0.70, 0.870), (0.80, 0.840), (0.84, 0.560), (0.82, 0.300), 0.78, 0.22),  # K9 корма (торец, фаска)
]
Z = [k[0] for k in KEYS]
X_INNER = 0.62              # внутренняя стенка арки (шина от 0.67)

# зоны по z
WINDSHIELD = (Z[3], Z[4])
ROOF = (Z[4], Z[5])
REAR_GLASS = (Z[5], Z[7])
SIDE_GLASS = (Z[3], Z[6])


def _interp(z):
    for a, b in zip(KEYS, KEYS[1:]):
        if a[0] <= z <= b[0]:
            k = 0.0 if b[0] == a[0] else (z - a[0]) / (b[0] - a[0])
            def L(u, v):
                if isinstance(u, tuple):
                    return tuple(L(p, q) for p, q in zip(u, v))
                return u + (v - u) * k
            return tuple(L(u, v) for u, v in zip(a[1:], b[1:]))
    raise ValueError(z)


def _arch_h(z):
    """Высота потолка арки над землёй в точке z (None — вне арки)."""
    for zc in AXLES:
        d = z - zc
        if abs(d) <= ARCH_R + 1e-9:
            return HUB_H + math.sqrt(max(0.0, ARCH_R ** 2 - d * d))
    return None


def _section(z, arch=None):
    ht, p2, p3, p4, p5, p6, xo, fl = _interp(z)
    h1 = ht - 0.004
    pts = [(0.0, ht), (STRIPE_X, h1), p2, p3, p4, p5, p6, (xo, fl), (X_INNER, fl), (X_INNER, fl), (0.0, fl)]
    if arch is not None:
        top = p4[1] - 0.03
        a = min(arch, top)
        for i in (5, 6, 7, 8):
            x, h = pts[i]
            pts[i] = (x, max(h, a))
    return [(x, Y0 + h, z) for x, h in pts]


def _stations():
    """[(z, arch_h | None)]: ключевые сечения + дуги арок. На краю арки — пара сечений с одним z
    (порог и начало дуги): совпадающие точки пары выбрасываются, остаётся вертикальная стенка арки."""
    st = [(z, 1, None) for z in Z]               # (z, порядок при равном z, арка)
    for zc in AXLES:
        n = 8
        for i in range(n + 1):
            phi = math.pi * (1 - i / n)            # 180° (перед) → 0° (зад)
            z = zc + ARCH_R * math.cos(phi)
            h = HUB_H + ARCH_R * math.sin(phi)
            if i == 0:
                st.append((z, 0, None))            # порог перед аркой
            st.append((z, 1, h))
            if i == n:
                st.append((z, 2, None))            # порог за аркой
    st.sort(key=lambda s: (round(s[0], 6), s[1]))
    out = []
    for z, _o, a in st:   # ключевое сечение внутри арки → тоже с аркой
        if a is None and _o == 1 and _arch_h(z) is not None:
            a = _arch_h(z)
        out.append((z, a))
    return out


def _in(z, rng):
    return rng[0] < z < rng[1]


def _glass_t(p, zone):
    x, y, z = p
    h = y - Y0
    if zone == "windshield":
        return 0.10 + 0.95 * (h - 0.86) / 0.39 - 0.30 * abs(x)
    if zone == "rear":
        return 0.10 + 0.95 * (h - 0.90) / 0.35 - 0.30 * abs(x)
    return 0.15 + 0.75 * (z - SIDE_GLASS[0]) / (SIDE_GLASS[1] - SIDE_GLASS[0]) - 0.9 * (h - 0.85)


def body_mesh() -> Mesh:
    st = _stations()
    secs = [_section(z, a) for z, a in st]
    half = Mesh("half", smooth_angle=22.0)
    BODY, GLASS = 1, 2

    def face(i, j):
        zm = 0.5 * (st[i][0] + st[i + 1][0])
        if j in (0, 1):                               # полоса и крыша/капот/стёкла
            if _in(zm, WINDSHIELD):
                return {"cell": "glass_blik", "group": GLASS, "tfn": lambda p: _glass_t(p, "windshield")}
            if _in(zm, REAR_GLASS):
                return {"cell": "glass_blik", "group": GLASS, "tfn": lambda p: _glass_t(p, "rear")}
            return {"cell": "hero_stripe" if j == 0 else "pearl_light", "group": BODY}
        if j == 2:                                    # боковые стёкла / край капота и багажника
            if _in(zm, SIDE_GLASS):
                return {"cell": "glass_blik", "group": GLASS, "tfn": lambda p: _glass_t(p, "side")}
            return {"cell": "pearl_light", "group": BODY}
        if j in (3, 4, 5):
            return {"cell": "pearl_light", "group": BODY}
        if j == 6:
            return {"cell": "trim", "group": 0}       # тёмный порог
        return {"cell": "underbody", "group": 0}      # низ порога, арки, днище

    loft.loft(half, secs, face)
    # ориентация лофта — по известной грани: полоса на крыше должна смотреть вверх
    roof = next(p for p in half.polys if p.cell == "hero_stripe" and _in(sum(q[2] for q in p.pts) / len(p.pts), ROOF))
    if Mesh._newell(roof.pts)[1] < 0:
        loft.flip(half)
    full = Mesh("body", smooth_angle=22.0)
    full.extend(half.polys)
    full.extend(half.mirrored_x().polys)
    # торцы: нос смотрит в −Z, корма в +Z (у них разный обход — задаём нормалью, а не общим разворотом)
    for sec, normal in ((secs[0], (0, 0, -1)), (secs[-1], (0, 0, 1))):
        ring = list(sec) + [(-x, y, z) for x, y, z in reversed(sec[1:-1])]
        loft.quad_on(full, ring, "pearl_light", normal=normal)
    vol = loft.signed_volume(full)
    assert vol > 0, f"кузов вывернут: объём {vol:.3f}"
    return full


def details(body: Mesh) -> tuple[Mesh, Mesh, Mesh, dict]:
    """Наклейки на торцах, зеркала → (дополнения кузова, задние огни, фары, якоря)."""
    extra = Mesh("extra", smooth_angle=22.0)
    tail = Mesh("lights_tail")
    head = Mesh("lights_head")
    zf, zr = Z[0], Z[-1]
    F, B = (0, 0, -1), (0, 0, 1)

    def rect(m, x0, x1, h0, h1, z, cell, normal, off, mat="atlas", sym=True):
        for s in ((1, -1) if sym else (1,)):
            xa, xb = sorted((s * x0, s * x1))
            if not sym and x0 < 0:
                xa, xb = x0, x1
            loft.quad_on(m, [(xa, Y0 + h0, z), (xb, Y0 + h0, z), (xb, Y0 + h1, z), (xa, Y0 + h1, z)],
                         cell, mat, normal=normal, offset=off)

    # корма: тёмная панель во всю ширину, две широкие секции огней, нижняя губа, номер (без текста)
    rect(extra, -0.74, 0.74, 0.585, 0.785, zr, "trim", B, 0.006, sym=False)
    rect(tail, 0.24, 0.72, 0.615, 0.755, zr, "brake", B, 0.012, mat="emissive")
    rect(extra, -0.70, 0.70, 0.235, 0.330, zr, "trim", B, 0.006, sym=False)
    rect(extra, -0.25, 0.25, 0.400, 0.520, zr, "marking", B, 0.006, sym=False)
    # нос: щели фар, решётка, губа
    rect(head, 0.40, 0.66, 0.445, 0.495, zf, "headlight", F, 0.010, mat="emissive")
    rect(extra, -0.36, 0.36, 0.300, 0.400, zf, "trim", F, 0.006, sym=False)
    rect(extra, -0.66, 0.66, 0.225, 0.262, zf, "trim", F, 0.006, sym=False)
    # зеркала у основания стойки A: стоят на поясе (низ стекла), внутренний край утоплен в стекло
    zm = -0.56
    belt = _interp(zm)[2]                      # (x, h) пояса в этом сечении
    for s in (1, -1):
        x0, x1 = belt[0] - 0.03, 0.93
        loft.box(extra, (s * 0.5 * (x0 + x1), Y0 + belt[1] + 0.045, zm), (x1 - x0, 0.09, 0.13), "pearl_light", group=0)
    anchors = {
        "tail_light_l": (-0.48, Y0 + 0.685, zr + 0.012), "tail_light_r": (0.48, Y0 + 0.685, zr + 0.012),
        "head_light_l": (-0.53, Y0 + 0.47, zf - 0.010), "head_light_r": (0.53, Y0 + 0.47, zf - 0.010),
        "wheel_fl": (-TRACK_X, Y0 + HUB_H, AXLES[0]), "wheel_fr": (TRACK_X, Y0 + HUB_H, AXLES[0]),
        "wheel_rl": (-TRACK_X, Y0 + HUB_H, AXLES[1]), "wheel_rr": (TRACK_X, Y0 + HUB_H, AXLES[1]),
        "ground_y": (0.0, Y0, 0.0),
    }
    return extra, tail, head, anchors


def build() -> Model:
    hull = body_mesh()
    extra, tail, head, anchors = details(hull)
    body = Mesh("body", smooth_angle=22.0)
    body.extend(hull.polys)
    body.extend(extra.polys)
    return Model(
        name="car_01", out="assets/models/cars/car_01/car_01.glb", nodes=[body, tail, head],
        anchors=anchors,
        meta={"kind": "car", "budget_tris": 4000, "wheel": "wheel_a", "dims": (4.40, 1.80, 1.25),
              "ground_y": Y0, "axles": AXLES, "track_x": TRACK_X, "x_inner": X_INNER},
        closed=[],
    )


def hull_for_checks() -> Mesh:
    return body_mesh()
