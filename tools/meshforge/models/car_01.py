"""car_01 v2 «Сэнко» — машина игрока (D-019, бриф docs/art/cars/car_01/BRIEF.md, референсы утверждены 2026-10-25).

Японское купе начала 90-х в широком кузове: длинный клиновидный нос с поп-апами, кабина-фонарь с тёмными
стойками, накладные гранёные арки (зад шире кабины), жалюзи на капоте, воздухозаборник перед задней аркой,
утиный хвост + GT-крыло на двух стойках, огни-лопасти по 3 сегмента, диффузор с рёбрами, две круглые трубы.

Как построено:
* кузов — лофт по сечениям (половина x ≥ 0 + зеркало). Сечения заданы в метрах подложки
  `docs/art/cars/car_01/underlay/car_01_side_grid.png` (zn — от носа, h — от земли) и переводятся в
  координаты машины функцией zr(): оси колёс общие для всех машин (ARCHITECTURE §8.5: z −1,35 / +1,30,
  колея ±0,78, ступица y 0,09), поэтому база 2,65 вместо 2,55 на картинке, свесы 0,97 / 0,78 (D-020);
* 14 точек сечения: P0 центр верха · P1 край полосы героя · P2 внутренний верх (горб капота / край заднего
  стекла) · P3 кромка крыши / шов капота · P4 пояс (низ окна) / верх крыла · P5 плечо · P6 кромка накладной
  арки · P7 бок · P8 нижняя складка · P9 верх порога · P10 низ порога · P11 = P12 внутренняя стенка арки
  (в арке P11 поднимается) · P13 центр днища;
* накладные арки — сдвиг P6…P10 наружу по таблицам flare(); переход за 3 см по z — ступенька «на болтах»;
* линии панелей и наклейки — mf/parts.py поверх лофта; крыло, зеркала, трубы, рёбра, сплиттер — отдельные
  замкнутые детали в том же узле body (контур — инвертированная оболочка, нормали контура — TEXCOORD_1).
"""
from __future__ import annotations

import math

import numpy as np

from mf import loft as L
from mf import parts as PT
from mf.mesh import Mesh
from mf.model import Model

NAME = "car_01"
OUT = "assets/models/cars/car_01/car_01.glb"

# ---------------------------------------------------------------- общий контракт машин (ARCHITECTURE §8.5)
HUB_H = 0.325                 # высота ступицы над землёй = радиус шины wheel_a
HUB_Y = 0.09                  # ступица в координатах корня
Y0 = HUB_Y - HUB_H            # земля: −0,235
TRACK_X = 0.78
AXLES = (-1.35, 1.30)
X_INNER = 0.64                # внутренняя стенка арки (шина от 0,675 с вылетом wheel_a +0,02)
ARCH_R = 0.37                 # радиус выреза арки (шина 0,325 + 4,5 см)
ARCH_N = 6                    # сегментов дуги арки

# ---------------------------------------------------------------- подложка → машина
ZN_AF, ZN_AR, ZN_TAIL = 1.07, 3.62, 4.40     # оси и корма на подложке (м от носа)
NOSE_Z = -2.32


def zr(zn: float) -> float:
    """Метры подложки от носа → z машины (кусочно-линейно, оси совпадают с общими)."""
    if zn <= ZN_AF:
        return NOSE_Z + zn * (AXLES[0] - NOSE_Z) / ZN_AF
    if zn <= ZN_AR:
        return AXLES[0] + (zn - ZN_AF) * (AXLES[1] - AXLES[0]) / (ZN_AR - ZN_AF)
    return AXLES[1] + (zn - ZN_AR)


def zn_of(z: float) -> float:
    if z <= AXLES[0]:
        return (z - NOSE_Z) * ZN_AF / (AXLES[0] - NOSE_Z)
    if z <= AXLES[1]:
        return ZN_AF + (z - AXLES[0]) * (ZN_AR - ZN_AF) / (AXLES[1] - AXLES[0])
    return ZN_AR + (z - AXLES[1])


# ---------------------------------------------------------------- ключевые сечения (x, h) × 14
FL = 0.12                      # днище
KEYS = [
    (0.06, [(0, .40), (.09, .40), (.30, .40), (.55, .395), (.68, .39), (.74, .37), (.77, .33), (.78, .26),
            (.77, .18), (.75, .14), (.72, .125), (.58, .125), (.58, .125), (0, .125)]),          # торец носа
    (0.11, [(0, .425), (.09, .425), (.30, .424), (.57, .418), (.73, .413), (.80, .395), (.835, .345), (.845, .26),
            (.835, .175), (.81, .125), (.78, .105), (.60, .115), (.60, .115), (0, .115)]),        # кромка носа
    (0.30, [(0, .548), (.09, .546), (.28, .533), (.56, .517), (.76, .522), (.86, .495), (.885, .44), (.893, .30),
            (.88, .20), (.855, .13), (.835, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),
    (0.70, [(0, .722), (.09, .720), (.27, .706), (.57, .690), (.79, .700), (.885, .672), (.90, .60), (.905, .40),
            (.89, .25), (.865, .14), (.845, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),
    (1.42, [(0, .826), (.09, .824), (.30, .820), (.60, .810), (.79, .808), (.875, .780), (.89, .70), (.895, .48),
            (.88, .26), (.86, .15), (.84, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),           # низ стекла
    (1.90, [(0, 1.012), (.09, 1.007), (.32, .990), (.62, .950), (.80, .800), (.885, .772), (.895, .69), (.90, .48),
            (.885, .26), (.865, .15), (.845, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),
    (2.30, [(0, 1.163), (.09, 1.159), (.36, 1.146), (.60, 1.092), (.795, .802), (.885, .772), (.895, .69), (.90, .48),
            (.885, .26), (.865, .15), (.845, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),       # верх стекла
    (2.65, [(0, 1.170), (.09, 1.166), (.36, 1.152), (.60, 1.100), (.80, .808), (.885, .776), (.895, .70), (.90, .48),
            (.885, .26), (.865, .15), (.845, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),
    (3.00, [(0, 1.135), (.09, 1.131), (.38, 1.115), (.62, 1.060), (.815, .820), (.89, .790), (.90, .72), (.905, .50),
            (.89, .27), (.87, .15), (.85, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),           # начало заднего стекла
    (3.35, [(0, 1.035), (.09, 1.032), (.40, 1.020), (.66, .980), (.84, .845), (.895, .810), (.905, .74), (.91, .51),
            (.895, .28), (.875, .155), (.855, .10), (X_INNER, FL), (X_INNER, FL), (0, FL)]),
    (3.70, [(0, .887), (.09, .886), (.42, .882), (.70, .876), (.85, .866), (.90, .830), (.91, .76), (.915, .52),
            (.90, .29), (.88, .16), (.86, .105), (X_INNER, FL), (X_INNER, FL), (0, FL)]),          # крышка багажника
    (4.22, [(0, .873), (.09, .872), (.42, .869), (.70, .866), (.84, .860), (.885, .830), (.895, .76), (.90, .52),
            (.885, .30), (.86, .18), (.84, .13), (X_INNER, .14), (X_INNER, .14), (0, .14)]),
    (4.33, [(0, .895), (.09, .895), (.42, .893), (.70, .889), (.82, .878), (.865, .842), (.875, .76), (.88, .52),
            (.865, .30), (.84, .195), (.81, .155), (.60, .16), (.60, .16), (0, .16)]),             # утиный хвост
    (4.40, [(0, .862), (.09, .862), (.42, .860), (.70, .856), (.80, .850), (.84, .822), (.855, .76), (.86, .52),
            (.85, .30), (.83, .205), (.80, .175), (.60, .175), (.60, .175), (0, .175)]),           # торец кормы
]
K = 14

# регионы (zn)
ZN_WS0, ZN_WS1 = 1.42, 2.30       # лобовое стекло
ZN_RG0, ZN_RG1 = 3.00, 3.70       # заднее стекло-люк
ZN_Q1 = 3.15                      # конец заднего бокового окна
ZN_DECK = 3.76                    # шов крышки багажника

# накладные арки: (zn, значение) — кусочно-линейно
F_BLEND = [(0.58, 0), (0.61, 1), (1.52, 1), (1.55, 0), (2.86, 0), (2.89, 1), (9, 1)]
F_X = [(0.58, .945), (1.55, .945), (2.86, .965), (4.05, .965), (4.25, .935), (4.40, .885)]
F_TOP = [(0.58, .62), (0.61, .62), (0.82, .728), (1.25, .745), (1.52, .69), (1.55, .69),
         (2.86, .62), (2.89, .62), (3.20, .78), (3.75, .81), (4.15, .79), (4.40, .77)]


def pl(table, x):
    xs = [a for a, _ in table]
    ys = [b for _, b in table]
    return float(np.interp(x, xs, ys))


def base_section(zn: float):
    if zn <= KEYS[0][0]:
        return [tuple(p) for p in KEYS[0][1]]
    for (za, A), (zb, B) in zip(KEYS, KEYS[1:]):
        if za <= zn <= zb:
            t = (zn - za) / (zb - za)
            return [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for a, b in zip(A, B)]
    return [tuple(p) for p in KEYS[-1][1]]


def arch_h(zn: float):
    z = zr(zn)
    for a in AXLES:
        d = z - a
        if abs(d) <= ARCH_R + 1e-9:
            return HUB_H + math.sqrt(max(ARCH_R * ARCH_R - d * d, 0.0))
    return None


def section(zn: float, arch: bool):
    S = [list(p) for p in base_section(zn)]
    b = pl(F_BLEND, zn)
    if b > 0:
        xf, top = pl(F_X, zn), pl(F_TOP, zn)
        dx = (xf - S[7][0]) * b
        S[6] = [S[6][0] + (xf - S[6][0]) * b, S[6][1] + (top - S[6][1]) * b]
        S[7] = [S[7][0] + dx + 0.004 * b, min(S[7][1], top - 0.07)]
        S[8][0] += dx * 0.97
        S[9][0] += dx * 0.90
        S[10][0] += dx * 0.85
        S[5][1] = max(S[5][1], S[6][1] + 0.035 * b)
        S[4][1] = max(S[4][1], S[5][1] + 0.02)
    if arch:
        ah = arch_h(zn)
        if ah is not None:
            ah = min(ah, S[6][1] - 0.02)
            for k in range(7, 12):
                if S[k][1] < ah:
                    S[k][1] = ah
    return [(x, h + Y0, zr(zn)) for x, h in S]


# ---------------------------------------------------------------- станции
def stations():
    st = {(zn, False) for zn, _ in KEYS}
    st |= {(z, False) for z, _ in F_BLEND if z < ZN_TAIL}
    st |= {(ZN_Q1, False)}
    for a in AXLES:
        for k in range(ARCH_N + 1):
            phi = math.pi * (1 - k / ARCH_N)
            st.add((zn_of(a + ARCH_R * math.cos(phi)), True))
    # без арки в станциях внутри выреза быть не может — убрать совпадения
    out = sorted(st, key=lambda s: (round(s[0], 6), 0 if (not s[1] and zr(s[0]) < _nearest_axle(s[0])) else 1
                                    if s[1] else 2))
    clean = []
    for zn, ar in out:
        if not ar and arch_h(zn) is not None and _strict_inside(zn):
            continue
        clean.append((zn, ar))
    return clean


def _nearest_axle(zn):
    z = zr(zn)
    return min(AXLES, key=lambda a: abs(a - z))


def _strict_inside(zn):
    z = zr(zn)
    return any(abs(z - a) < ARCH_R - 1e-6 for a in AXLES)


STATIONS = stations()
SECS = [section(zn, ar) for zn, ar in STATIONS]
ZNS = [zn for zn, _ in STATIONS]


# ---------------------------------------------------------------- поверхность (для линий и наклеек)
def surf(zn: float, s: float):
    """Точка лофта: zn — между станциями (берётся первая подходящая пара), s — дробный индекс точки сечения."""
    i = max(0, min(len(ZNS) - 2, int(np.searchsorted(ZNS, zn, side="right")) - 1))
    while i < len(ZNS) - 2 and ZNS[i + 1] - ZNS[i] < 1e-9:
        i += 1
    za, zb = ZNS[i], ZNS[i + 1]
    t = 0.0 if zb - za < 1e-9 else min(max((zn - za) / (zb - za), 0.0), 1.0)
    j = int(min(max(math.floor(s), 0), K - 2))
    u = s - j
    A, B = np.array(SECS[i]), np.array(SECS[i + 1])
    pa = A[j] * (1 - u) + A[j + 1] * u
    pb = B[j] * (1 - u) + B[j + 1] * u
    return pa * (1 - t) + pb * t


def surf_n(zn: float, s: float):
    e = 1e-3
    ds = surf(zn, min(s + e, K - 1)) - surf(zn, max(s - e, 0))
    dz = surf(min(zn + 0.01, ZN_TAIL), s) - surf(max(zn - 0.01, KEYS[0][0]), s)
    n = np.cross(dz, ds)
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else np.array([1.0, 0, 0])


def side_s(zn: float, h: float) -> float:
    """Дробный s на боку (P4…P10), где высота над землёй = h."""
    lo, hi = 4.0, 10.0
    for _ in range(40):
        mid = (lo + hi) / 2
        if surf(zn, mid)[1] - Y0 > h:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def line_z(m: Mesh, s: float, zn0: float, zn1: float, **kw):
    """Линия вдоль кузова по точке сечения s от zn0 до zn1 (через все станции между ними)."""
    zs = [zn0] + [z for z in ZNS if zn0 < z < zn1] + [zn1]
    zs = sorted(set(round(z, 6) for z in zs))
    PT.strip(m, [surf(z, s) for z in zs], [surf_n(z, s) for z in zs], **kw)


def line_s(m: Mesh, zn: float, s0: float, s1: float, **kw):
    """Линия поперёк кузова по станции zn от s0 до s1 (через все точки сечения)."""
    ss = [s0] + [float(k) for k in range(K) if s0 < k < s1] + [s1]
    PT.strip(m, [surf(zn, s) for s in ss], [surf_n(zn, s) for s in ss], **kw)


# ---------------------------------------------------------------- кузов-лофт
def _mid(i):
    return 0.5 * (ZNS[i] + ZNS[i + 1])


def glass_t_ws(p):
    h = p[1] - Y0
    return 0.50 + (h - 0.99) * 2.4 + abs(p[0]) * 0.45


def glass_t_side(p):
    h = p[1] - Y0
    return 0.50 + (h - 0.97) * 2.2 + (p[2] + 0.55) * 0.55


def sill_t(p):
    return float(np.clip((0.56 - (p[1] - Y0)) / 0.42, 0, 1))


def face(i, j):
    zm = _mid(i)
    both_arch = STATIONS[i][1] and STATIONS[i + 1][1]
    any_arch = STATIONS[i][1] or STATIONS[i + 1][1]
    if j >= 7 and any_arch and (both_arch or abs(ZNS[i] - ZNS[i + 1]) < 1e-9):
        return {"cell": "underbody", "group": 3}
    ws = ZN_WS0 <= zm <= ZN_WS1
    rg = ZN_RG0 <= zm <= ZN_RG1
    if j <= 2 and ws:
        return {"cell": "glass_blik", "group": 2, "tfn": glass_t_ws}
    if j <= 1 and rg:
        return {"cell": "glass", "group": 2}
    if j == 0:
        top = zm < ZN_WS0 or (ZN_WS1 < zm < ZN_RG0) or zm > ZN_RG1
        return {"cell": "hero_stripe" if top else "pearl_light", "group": 1}
    if j == 3 and ZN_WS0 <= zm <= ZN_Q1:
        return {"cell": "glass_blik", "group": 2, "tfn": glass_t_side}
    if j in (7, 8):
        return {"cell": "pearl_sill", "group": 1, "tfn": sill_t}
    if j == 9:
        return {"cell": "trim", "group": 4}
    if j >= 10:
        return {"cell": "underbody", "group": 3}
    return {"cell": "pearl_light", "group": 1}


def hull_half() -> Mesh:
    m = Mesh("half", smooth_angle=34.0)
    L.loft(m, SECS, face)
    # торцы: нос смотрит в −Z, корма в +Z
    nose = [SECS[0][k] for k in range(K)]
    PT.decal(m, nose, (0, 0, -1), "pearl_light", offset=0.0, group=0)
    tail = [SECS[-1][k] for k in range(K)]
    PT.decal(m, tail, (0, 0, 1), "pearl_light", offset=0.0, group=0)
    return m


def hull_full() -> Mesh:
    half = hull_half()
    full = Mesh("body", smooth_angle=34.0)
    full.extend(half.polys)
    full.extend(half.mirrored_x().polys)
    L.orient_outward(full)
    return full


def hull_for_checks() -> Mesh:
    return hull_full()


# ---------------------------------------------------------------- линии панелей
def panel_lines(m: Mesh) -> None:
    line_z(m, 3.0, 0.13, ZN_WS0 - 0.01)                       # шов капота
    line_s(m, 0.28, 0.0, 9.0)                                 # шов бампера: поперёк капота и вниз по крылу
    for zn in (0.33, 0.60):                                   # крышки поп-апов
        line_s(m, zn, 3.2, 4.6)
    for s in (3.2, 4.6):
        line_z(m, s, 0.33, 0.60)
    line_s(m, ZN_WS0 + 0.004, 0.0, 4.0)                       # низ лобового
    line_z(m, 4.0, ZN_WS0, ZN_Q1)                             # пояс (низ окон)
    line_s(m, 1.60, 4.05, 9.0)                                # дверь спереди
    line_s(m, 2.78, 4.05, 8.6)                                # дверь сзади
    line_z(m, 6.0, 0.61, 1.52)                                # передняя накладка: кромка
    line_s(m, 0.595, 6.0, 9.6)
    line_s(m, 1.535, 6.0, 9.6)
    line_z(m, 6.0, 2.89, ZN_TAIL - 0.005)                     # задняя накладка: кромка
    line_s(m, 2.875, 6.0, 9.6)
    line_s(m, ZN_DECK, 0.0, 3.0)                              # крышка багажника
    line_z(m, 3.0, ZN_DECK, 4.31)
    # губа арок: по P7 станций выреза
    for a in AXLES:
        idx = [i for i, (zn, ar) in enumerate(STATIONS) if ar and abs(zr(zn) - a) <= ARCH_R + 1e-6]
        pts = [np.array(SECS[i][7]) for i in idx]
        PT.strip(m, pts, [np.array([1.0, 0.0, 0.0])] * len(pts), width=0.02)


# ---------------------------------------------------------------- наклейки кузова
def body_decals(m: Mesh, head: Mesh, tail: Mesh) -> None:
    zf, zt = zr(KEYS[0][0]), zr(ZN_TAIL)
    Fp = lambda x, h: (x, Y0 + h, zf)
    Tp = lambda x, h: (x, Y0 + h, zt)
    # --- нос: рот, боковые воздуховоды, полоса героя на губе, угловые лампы
    PT.decal(m, [Fp(0, .14), Fp(.46, .14), Fp(.49, .305), Fp(0, .305)], (0, 0, -1), "underbody")
    PT.decal(m, [Fp(.54, .14), Fp(.735, .14), Fp(.755, .275), Fp(.56, .28)], (0, 0, -1), "underbody")
    PT.decal(m, [Fp(0, .315), Fp(.09, .315), Fp(.09, .40), Fp(0, .40)], (0, 0, -1), "hero_stripe")
    PT.decal(head, [Fp(.56, .315), Fp(.745, .315), Fp(.765, .352), Fp(.575, .358)], (0, 0, -1), "headlight",
             mat="emissive", offset=0.005)
    # --- корма (камера погони — 90 % времени): тёмная полоса огней, огни-лопасти, знак, полоса героя
    #     сверху вниз через всё, ниже бампера — большой тёмный диффузор (ref_02, ref_03 корма)
    PT.decal(m, [Tp(0, .56), Tp(.83, .56), Tp(.85, .80), Tp(0, .80)], (0, 0, 1), "trim")
    PT.decal(m, [Tp(0, .175), Tp(.80, .175), Tp(.83, .205), Tp(.845, .30), Tp(.62, .37), Tp(0, .37)], (0, 0, 1),
             "underbody")
    PT.decal(m, [Tp(0, .345), Tp(.045, .345), Tp(.045, .862), Tp(0, .862)], (0, 0, 1), "hero_stripe", offset=0.009)
    PT.decal(m, [Tp(.035, .195), Tp(.19, .195), Tp(.19, .33), Tp(.035, .33)], (0, 0, 1), "trim", offset=0.006)
    segs = [((.20, .64), (.37, .645), (.37, .735), (.20, .73)),
            ((.40, .646), (.58, .652), (.58, .742), (.40, .736)),
            ((.61, .653), (.79, .66), (.855, .705), (.79, .75), (.61, .743))]
    for sg in segs:
        PT.decal(tail, [Tp(x, h) for x, h in sg], (0, 0, 1), "brake", mat="emissive", offset=0.006)
    PT.decal(m, [Tp(.05, .64), Tp(.10, .685), Tp(.05, .73)], (0, 0, 1), "pearl_mid", offset=0.010)
    # заход лопасти на боковину: треугольник вперёд по боку
    zn_a, zn_b = 4.27, ZN_TAIL - 0.002
    pts = [surf(zn_b, side_s(zn_b, .75)), surf(zn_b, side_s(zn_b, .66)), surf(zn_a, side_s(zn_a, .715))]
    PT.decal(tail, pts, surf_n(4.36, side_s(4.36, .71)), "brake", mat="emissive", offset=0.006)
    # --- жалюзи на капоте: тёмная коробка + 3 ламели с каждой стороны полосы (ref_03 перёд и сверху)
    a, b, z0, z1 = 1.75, 2.95, 0.84, 1.24
    box = [surf(z0, a), surf(z0, b), surf(z1, b), surf(z1, a)]
    PT.decal(m, box, surf_n((z0 + z1) / 2, (a + b) / 2), "underbody")
    for k in range(3):
        zz = z0 + 0.08 + k * 0.12
        nn = surf_n(zz, (a + b) / 2)
        PT.strip(m, [surf(zz, a + 0.08), surf(zz, b - 0.08)], [nn, nn], width=0.035, cell="pearl_mid", offset=0.008)
    # --- воздухозаборник перед задней аркой: тёмная трапеция + 2 ребра
    def S(zn, h):
        return surf(zn, side_s(zn, h))
    intake = [S(2.58, .24), S(2.875, .24), S(2.875, .64), S(2.72, .64)]
    nrm = surf_n(2.76, side_s(2.76, .45))
    PT.decal(m, intake, nrm, "underbody")
    for h in (.38, .50):
        zf0 = 2.58 + (2.72 - 2.58) * (h - .24) / .40
        PT.strip(m, [S(zf0 + 0.01, h), S(2.855, h)], [nrm, nrm], width=0.025, cell="pearl_mid", offset=0.007)
    # --- ручка двери
    PT.strip(m, [S(2.55, .70), S(2.68, .70)], [nrm, nrm], width=0.022, cell="underbody")


# ---------------------------------------------------------------- навесные детали (половина x ≥ 0)
def aero_half(m: Mesh) -> None:
    # сплиттер: тонкая тёмная губа под носом
    z0, z1 = NOSE_Z, zr(0.22)
    L.box(m, (0.43, Y0 + 0.075, (z0 + z1) / 2), (0.86, 0.03, z1 - z0), "trim", skip=("-x",))
    # GT-крыло: профиль (z, h), размах 0…0.78; полоса героя на середине (x < 0.13)
    prof = [(1.73, 1.100), (1.80, 1.135), (1.90, 1.152), (2.02, 1.178), (2.02, 1.160), (1.92, 1.128), (1.80, 1.100)]
    xs = [0.0, 0.09, 0.785]
    rings = [[(x, Y0 + h, z) for z, h in prof] + [(x, Y0 + prof[0][1], prof[0][0])] for x in xs]
    for a in range(len(xs) - 1):
        for j in range(len(prof)):
            A, B = rings[a], rings[a + 1]
            top = j < 3
            cell = "hero_stripe" if (top and a == 0) else ("trim" if not top else "pearl_light")
            m.add([A[j], A[j + 1], B[j + 1], B[j]], cell, group=5)
    # торцевые пластины: (z, h) многоугольник, толщина по x
    plate = [(1.66, 1.075), (1.75, 1.190), (2.11, 1.195), (2.11, 0.985), (1.93, 0.955)]
    PT.prism(m, [(z, Y0 + h) for z, h in plate], "x", 0.785, 0.80, "trim")
    # стойки крыла
    post = [(1.74, 0.86), (1.90, 0.86), (1.93, 1.13), (1.85, 1.13)]
    PT.prism(m, [(z, Y0 + h) for z, h in post], "x", 0.41, 0.43, "trim")
    # зеркало-капля на тонкой ножке
    zc, hc, xc = zr(1.62), 0.905, 0.925
    ring = [(-.055, .00), (-.035, .032), (.035, .032), (.065, .00), (.035, -.03), (-.035, -.03)]
    st = [(zc - 0.08, 0.45), (zc - 0.03, 1.0), (zc + 0.03, 1.0)]
    R = [[(xc + u * k, Y0 + hc + v * k, z) for u, v in ring] for z, k in st]
    for a in range(2):
        for j in range(6):
            jj = (j + 1) % 6
            m.add([R[a][j], R[a][jj], R[a + 1][jj], R[a + 1][j]], "pearl_light", group=6)
    m.add(list(reversed(R[0])), "pearl_light", group=6)
    m.add(R[2], "glass")
    PT.prism(m, [(0.86, Y0 + .845), (0.89, Y0 + .885), (0.89, Y0 + .905), (0.86, Y0 + .87)], "z",
             zc - 0.005, zc + 0.025, "trim")
    # две круглые трубы по центру
    PT.tube_z(m, 0.105, Y0 + 0.262, zr(4.30), zr(ZN_TAIL) + 0.04, 0.055, 0.012, 8, "trim", "rim_lip", "underbody")
    # диффузор: 3 ребра на половину (всего 6), стоят в тёмной нише кормы
    for x in (0.42, 0.58, 0.72):
        z0, z1 = zr(4.22), zr(ZN_TAIL) + 0.05
        L.box(m, (x, Y0 + 0.235, (z0 + z1) / 2), (0.016, 0.21, z1 - z0), "trim", skip=("+y", "-z"))


# ---------------------------------------------------------------- сборка
def build() -> Model:
    hull = hull_full()
    det_half = Mesh("det", smooth_angle=34.0)
    head_half = Mesh("head", smooth_angle=34.0)
    tail_half = Mesh("tail", smooth_angle=34.0)
    panel_lines(det_half)
    body_decals(det_half, head_half, tail_half)
    aero_half(det_half)
    body = Mesh("body", smooth_angle=34.0)
    body.extend(hull.polys)
    body.extend(det_half.polys)
    body.extend(det_half.mirrored_x().polys)
    head = Mesh("head", smooth_angle=34.0)
    head.extend(head_half.polys)
    head.extend(head_half.mirrored_x().polys)
    tail = Mesh("tail", smooth_angle=34.0)
    tail.extend(tail_half.polys)
    tail.extend(tail_half.mirrored_x().polys)
    zf, zt = zr(KEYS[0][0]), zr(ZN_TAIL)
    anchors = {
        "tail_light_l": (-0.50, Y0 + 0.69, zt + 0.012), "tail_light_r": (0.50, Y0 + 0.69, zt + 0.012),
        "head_light_l": (-0.66, Y0 + 0.335, zf - 0.010), "head_light_r": (0.66, Y0 + 0.335, zf - 0.010),
        "popup_hinge_l": (-0.71, Y0 + 0.60, zr(0.60)), "popup_hinge_r": (0.71, Y0 + 0.60, zr(0.60)),
        "exhaust_l": (-0.13, Y0 + 0.235, zt + 0.035), "exhaust_r": (0.13, Y0 + 0.235, zt + 0.035),
        "wheel_fl": (-TRACK_X, HUB_Y, AXLES[0]), "wheel_fr": (TRACK_X, HUB_Y, AXLES[0]),
        "wheel_rl": (-TRACK_X, HUB_Y, AXLES[1]), "wheel_rr": (TRACK_X, HUB_Y, AXLES[1]),
        "ground_y": (0.0, Y0, 0.0),
    }
    return Model(
        name=NAME, out=OUT, nodes=[body, tail, head], anchors=anchors,
        meta={"kind": "car", "budget_tris": 4000, "wheel": "wheel_a", "dims": (4.40, 1.92, 1.17),
              "ground_y": Y0, "axles": AXLES, "track_x": TRACK_X, "x_inner": X_INNER},
        closed=[],
        outline=["body"],
    )
