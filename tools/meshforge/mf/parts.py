"""Детали-заготовки MeshForge: линии панелей, призмы, трубы. Общие для всех машин (D-018, D-019).

Линии панелей (STYLE_GUIDE §3, v1.1) — тонкие тёмные полосы-наклейки поверх кузова: не текстура
(атлас однотонный), а геометрия. Полоса лежит в касательной плоскости и приподнята на offset по нормали.
"""
from __future__ import annotations

import math

import numpy as np

from .mesh import Mesh

INK = "underbody"        # цвет линий: deepest #1B1030 (гайд §3: не чёрный)
LINE_W = 0.014           # ширина линии панели, м
LINE_OFF = 0.004         # подъём над поверхностью, м (от z-конфликта)


def _n(v):
    v = np.asarray(v, dtype=float)
    ln = np.linalg.norm(v)
    return v / ln if ln > 1e-12 else v


def strip(mesh: Mesh, pts, normals, width=LINE_W, cell=INK, offset=LINE_OFF, mat="atlas", group=0) -> None:
    """Полоса вдоль ломаной pts (≥2 точек) с нормалями поверхности normals: стыки — по биссектрисе."""
    P = [np.asarray(p, dtype=float) for p in pts]
    N = [_n(n) for n in normals]
    if len(P) < 2:
        return
    side = []
    for i in range(len(P)):
        t = P[min(i + 1, len(P) - 1)] - P[max(i - 1, 0)]
        side.append(_n(np.cross(N[i], t)) * (width / 2))
    for i in range(len(P) - 1):
        a0, a1 = P[i] + N[i] * offset, P[i + 1] + N[i + 1] * offset
        q = [a0 - side[i], a1 - side[i + 1], a1 + side[i + 1], a0 + side[i]]
        nrm = _n(N[i] + N[i + 1])
        e = np.cross(q[1] - q[0], q[3] - q[0])
        if float(np.dot(e, nrm)) < 0:
            q.reverse()
        mesh.add([tuple(v) for v in q], cell, mat, group)


def decal(mesh: Mesh, pts, normal, cell, offset=LINE_OFF, mat="atlas", group=0) -> None:
    """Наклейка-многоугольник (огни, решётки, тёмные вставки): обход под нормаль, сдвиг offset."""
    P = [np.asarray(p, dtype=float) for p in pts]
    nn = _n(normal)
    e = Mesh._newell([tuple(p) for p in P])
    if float(np.dot(e, nn)) < 0:
        P.reverse()
    mesh.add([tuple(p + nn * offset) for p in P], cell, mat, group)


def prism(mesh: Mesh, poly2d, axis: str, a0: float, a1: float, cell, mat="atlas", group=0, caps=(True, True),
          side_cells=None) -> None:
    """Призма: многоугольник poly2d в плоскости, перпендикулярной оси axis ('x' | 'y' | 'z'), от a0 до a1.
    Для axis='x' точки — (z, y); 'y' — (x, z); 'z' — (x, y). Наружу ориентируется по знаку объёма."""
    def p3(u, v, a):
        if axis == "x":
            return (a, v, u)
        if axis == "y":
            return (u, a, v)
        return (u, v, a)
    tmp = Mesh("tmp", mesh.smooth_angle)
    A = [p3(u, v, a0) for u, v in poly2d]
    B = [p3(u, v, a1) for u, v in poly2d]
    k = len(poly2d)
    for i in range(k):
        j = (i + 1) % k
        c = cell if side_cells is None else side_cells[i]
        tmp.add([A[i], A[j], B[j], B[i]], c, mat, group)
    if caps[0]:
        tmp.add(list(reversed(A)), cell, mat, group)
    if caps[1]:
        tmp.add(B, cell, mat, group)
    from .loft import orient_outward
    if caps[0] and caps[1]:
        orient_outward(tmp)
    mesh.extend(tmp.polys)


def tube_z(mesh: Mesh, cx: float, cy: float, z0: float, z1: float, r: float, wall: float, seg: int,
           cell_out, cell_rim, cell_in, depth: float = 0.05) -> None:
    """Выхлопная труба вдоль +Z: наружная стенка z0→z1, торец-кольцо на z1, внутренняя стенка вглубь на depth,
    заглушка. Задний торец (z1) смотрит в +Z."""
    ri = r - wall
    ring = lambda rr, z: [(cx + rr * math.cos(2 * math.pi * k / seg), cy + rr * math.sin(2 * math.pi * k / seg), z)
                          for k in range(seg)]
    o0, o1, i1, i0 = ring(r, z0), ring(r, z1), ring(ri, z1), ring(ri, z1 - depth)
    for k in range(seg):
        j = (k + 1) % seg
        mesh.add([o0[k], o0[j], o1[j], o1[k]], cell_out)          # наружу
        mesh.add([o1[k], o1[j], i1[j], i1[k]], cell_rim)          # торец (+Z)
        mesh.add([i1[k], i1[j], i0[j], i0[k]], cell_in)           # внутрь
    mesh.add(list(i0), cell_in)                                   # дно смотрит в +Z (видно с торца)
