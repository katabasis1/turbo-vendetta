"""Колесо A v2 — диск «звезда» в 5 спиц с полированной полкой (car_01 v2, BRIEF §3, ref_04 «диск»; D-018, D-019).

Ось колеса — X, центр — начало координат, лицевая сторона диска смотрит в +X (правый борт).
Для левых колёс сцена поворачивает узел на 180° вокруг Y (ARCHITECTURE §8.5, 1.3).
Радиус шины R = 0,325 и ширина W = 0,22 — общие для физики (не менять без D-xxx).

Сборка: тело вращения по замкнутому профилю (шина низкого профиля → светлая полка → тёмная «чаша» →
дно) + 5 спиц-призм поверх дна (вогнутые: у ступицы выше, у полки ниже) + колпачок-пятигранник.
Цвета — псевдонимы палитры §2 (mf/palette.py): шина `tire`, полка `rim_lip`, чаша `rim`, дно `underbody`,
спицы `hub`, колпачок `rim_lip`. Контур (D-018) обводит полку и спицы на тёмном дне — колесо читается
«звездой» даже на 64 px.
"""
from __future__ import annotations

import math

from mf import parts as PT
from mf.loft import orient_outward, revolve
from mf.mesh import Mesh
from mf.model import Model

R = 0.325          # радиус шины (Ø 0.65) — физика
W = 0.22           # ширина шины — физика
SEG = 20           # сегментов по кругу (кратно 5 спицам: шов совпадает со спицей)
R_BEAD = 0.240     # посадка шины на диск (низкий профиль: диск ≈ 0,74 Ø колеса, как в ref)
R_LIP = 0.208      # внутренний край полированной полки
X_LIP = 0.104
X_FLOOR = 0.012    # дно чаши (глубокий вылет — «deep dish»)

PROFILE = [
    (-0.100, 0.0),       # 0 центр внутренней стороны
    (-0.100, R_BEAD),    # 1 внутренний борт
    (-0.110, 0.300),     # 2 внутреннее плечо
    (-0.092, R),         # 3 протектор, внутренний край
    (0.092, R),          # 4 протектор, наружный край
    (0.110, 0.300),      # 5 наружное плечо
    (0.100, R_BEAD),     # 6 наружный борт
    (X_LIP, R_LIP),      # 7 полка (светлая, широкая)
    (X_FLOOR, 0.196),    # 8 стенка чаши (тёмная)
    (X_FLOOR, 0.0),      # 9 дно
]

SPOKE_R0, SPOKE_R1 = 0.050, 0.200          # от ступицы до полки
SPOKE_X0, SPOKE_X1 = 0.078, 0.040          # высота лица спицы: у ступицы / у полки (вогнутость)
SPOKE_W0, SPOKE_W1 = 0.060, 0.034          # ширина спицы: у ступицы / у полки


def build() -> Model:
    m = Mesh("wheel", smooth_angle=35.0)

    def face(j, k):
        if j == 0:
            return {"cell": "underbody"}          # внутренняя сторона (к машине)
        if j in (1, 2, 3, 4, 5):
            return {"cell": "tire", "group": 1}   # шина: сглаженная
        if j == 6:
            return {"cell": "rim_lip"}            # наружный борт → полка: светлый обод
        if j == 7:
            return {"cell": "rim"}                # стенка чаши
        return {"cell": "underbody"}              # дно между спицами

    revolve(m, PROFILE, SEG, face, phase=math.pi / SEG)
    orient_outward(m)
    # спицы: призма в плоскости (z, y) повёрнутая на угол a; лицо наклонено (вогнутость)
    for s in range(5):
        a = 2 * math.pi * s / 5 + math.pi / 2
        ca, sa = math.cos(a), math.sin(a)

        def P(r, t, x):          # r — по спице, t — поперёк, x — по оси колеса
            return (x, r * sa + t * ca, r * ca - t * sa)

        hw0, hw1 = SPOKE_W0 / 2, SPOKE_W1 / 2
        top = [P(SPOKE_R0, -hw0, SPOKE_X0), P(SPOKE_R1, -hw1, SPOKE_X1), P(SPOKE_R1, hw1, SPOKE_X1), P(SPOKE_R0, hw0, SPOKE_X0)]
        bot = [(X_FLOOR - 0.004, q[1], q[2]) for q in top]
        sp = Mesh("tmp")
        sp.add(top, "hub")
        # низ спицы лежит в дне — не строится (−2 треугольника × 5)
        for i in range(4):
            j = (i + 1) % 4
            sp.add([bot[i], bot[j], top[j], top[i]], "rim" if i in (0, 2) else "hub")
        orient_outward(sp)          # открытая снизу призма: ориентация по 4 сторонам и лицу
        m.extend(sp.polys)
    # колпачок ступицы: пятигранная призма
    pent = [(0.058 * math.cos(2 * math.pi * k / 5 + math.pi / 2), 0.058 * math.sin(2 * math.pi * k / 5 + math.pi / 2))
            for k in range(5)]
    PT.prism(m, pent, "x", X_FLOOR - 0.004, 0.092, "rim_lip", side_cells=["rim"] * 5, caps=(False, True))
    return Model(
        name="wheel_a", out="assets/models/wheels/wheel_a.glb", nodes=[m],
        meta={"budget_tris": 400, "radius": R, "width": W, "kind": "wheel"},
        closed=[],          # шина + отдельные спицы-призмы: замкнуты по отдельности, общий меш — нет
    )
