"""Колесо A — стандартное колесо машин (STYLE_GUIDE §5: колёса Ø ≈ 0.65 м, тёмные диски).

Ось колеса — X, центр — начало координат, лицевая сторона диска смотрит в +X (правый борт).
Для левых колёс сцена поворачивает узел на 180° вокруг Y (ARCHITECTURE §8.5, 1.3).
5 спиц: 15 сегментов, узор «спица, проём, проём» — вращение видно без лишних треугольников.
"""
from __future__ import annotations

from mf.loft import orient_outward, revolve
from mf.mesh import Mesh
from mf.model import Model

R = 0.325          # радиус шины (Ø 0.65)
W = 0.22           # ширина шины
SEG = 15

PROFILE = [
    (-0.100, 0.215),   # 0 внутренний борт у диска
    (-0.110, 0.290),   # 1 внутреннее плечо
    (-0.090, R),       # 2 протектор, внутренний край
    (0.090, R),        # 3 протектор, наружный край
    (0.110, 0.290),    # 4 наружное плечо
    (0.100, 0.215),    # 5 наружный борт у диска
    (0.095, 0.205),    # 6 закраина диска
    (0.068, 0.190),    # 7 «тарелка» диска (утоплена)
    (0.068, 0.075),    # 8 к ступице
    (0.088, 0.060),    # 9 колпак ступицы
    (0.088, 0.0),      # 10 центр
]


def build() -> Model:
    m = Mesh("wheel", smooth_angle=30.0)

    def face(j, k):
        if j in (0, 1, 2, 3, 4):           # шина: протектор и боковины — сглаженные
            return {"cell": "tire", "group": 1}
        if j == 5:
            return {"cell": "tire", "group": 0}
        if j == 6:
            return {"cell": "rim"}           # закраина
        if j == 7:                           # спицы и проёмы
            return {"cell": "rim" if k % 3 == 0 else "underbody"}
        if j == 8:
            return {"cell": "hub"}
        return {"cell": "hub"}

    revolve(m, PROFILE, SEG, face)
    # внутренняя сторона (к машине): плоский диск
    revolve(m, [(-0.100, 0.0), (-0.100, 0.215)], SEG, lambda j, k: {"cell": "underbody"})
    orient_outward(m)
    return Model(
        name="wheel_a", out="assets/models/wheels/wheel_a.glb", nodes=[m],
        meta={"budget_tris": 400, "radius": R, "width": W, "kind": "wheel"},
        closed=["wheel"],
    )
