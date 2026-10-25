"""Лофт по сечениям, фаски, тела вращения.

Лофт: сечения — ломаные с одинаковым числом точек; соседние сечения соединяются четырёхугольниками.
Ориентацию граней задаёт порядок точек; для замкнутого тела проще собрать как получится и вызвать
orient_outward() — он разворачивает всё по знаку объёма.
"""
from __future__ import annotations

import math

import numpy as np

from .mesh import Mesh, Poly


def chamfer2d(pts, corners, d):
    """Фаска на углах ломаной (2D или 3D): угол i заменяется двумя точками на соседних рёбрах на расстоянии d.
    corners — индексы углов (не первая и не последняя точка у открытой ломаной)."""
    out = []
    P = [np.array(p, dtype=float) for p in pts]
    for i, p in enumerate(P):
        if i in corners and 0 < i < len(P) - 1:
            a, b = P[i - 1], P[i + 1]
            da, db = np.linalg.norm(a - p), np.linalg.norm(b - p)
            ka, kb = min(d, 0.45 * da) / max(da, 1e-9), min(d, 0.45 * db) / max(db, 1e-9)
            out.append(tuple(p + (a - p) * ka))
            out.append(tuple(p + (b - p) * kb))
        else:
            out.append(tuple(p))
    return out


def loft(mesh: Mesh, sections, face_fn) -> None:
    """sections: [[(x,y,z) × K] × S]. face_fn(i, j) → None (пропустить) или dict(cell, mat?, group?, tfn?)
    для полосы между сечениями i, i+1 и рёбрами j, j+1. tfn(p) → t для градиентной клетки."""
    S = len(sections)
    K = len(sections[0])
    assert all(len(s) == K for s in sections), "у сечений лофта разное число точек"
    for i in range(S - 1):
        A, B = sections[i], sections[i + 1]
        for j in range(K - 1):
            f = face_fn(i, j)
            if not f:
                continue
            pts = [A[j], B[j], B[j + 1], A[j + 1]]
            tfn = f.get("tfn")
            mesh.add(pts, f["cell"], f.get("mat", "atlas"), f.get("group", 0),
                     None if tfn is None else [tfn(p) for p in pts])


def signed_volume(mesh: Mesh) -> float:
    v = 0.0
    for _mat, _cell, _g, P, _t, _n, _a in mesh.triangles():
        v += float(np.dot(P[0], np.cross(P[1], P[2]))) / 6.0
    return v


def flip(mesh: Mesh) -> None:
    for p in mesh.polys:
        p.pts.reverse()
        if p.t is not None:
            p.t.reverse()


def orient_outward(mesh: Mesh) -> float:
    """Замкнутое тело: если объём < 0, развернуть все грани. Возвращает объём (> 0)."""
    v = signed_volume(mesh)
    if v < 0:
        flip(mesh)
        v = -v
    return v


def revolve(mesh: Mesh, profile, segments: int, face_fn, phase: float = 0.0) -> None:
    """Тело вращения вокруг оси X. profile: [(x, r)] — ломаная от одного торца к другому.
    face_fn(j, k) → dict(cell, mat?, group?) для полосы профиля j..j+1 в сегменте k. Точки с r = 0 дают треугольники."""
    rings = []
    for k in range(segments + 1):
        a = phase + 2 * math.pi * k / segments
        ca, sa = math.cos(a), math.sin(a)
        rings.append([(x, r * ca, r * sa) for x, r in profile])
    for k in range(segments):
        A, B = rings[k], rings[k + 1]
        for j in range(len(profile) - 1):
            f = face_fn(j, k)
            if not f:
                continue
            mesh.add([A[j], A[j + 1], B[j + 1], B[j]], f["cell"], f.get("mat", "atlas"), f.get("group", 0))


def box(mesh: Mesh, c, size, cell, mat="atlas", group=0, skip=()) -> None:
    """Параллелепипед: центр c, размер size. skip — стороны без граней: '+x','-x','+y','-y','+z','-z'."""
    cx, cy, cz = c
    hx, hy, hz = size[0] / 2, size[1] / 2, size[2] / 2
    V = {(sx, sy, sz): (cx + sx * hx, cy + sy * hy, cz + sz * hz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)}
    faces = {
        "+x": [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
        "-x": [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)],
        "+y": [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)],
        "-y": [(-1, -1, 1), (-1, -1, -1), (1, -1, -1), (1, -1, 1)],
        "+z": [(1, -1, 1), (1, 1, 1), (-1, 1, 1), (-1, -1, 1)],
        "-z": [(-1, -1, -1), (-1, 1, -1), (1, 1, -1), (1, -1, -1)],
    }
    for k, f in faces.items():
        if k not in skip:
            mesh.add([V[q] for q in f], cell, mat, group)


def quad_on(mesh: Mesh, pts, cell, mat="atlas", normal=None, offset=0.0, group=0) -> None:
    """Плоская наклейка (огни, решётка): 4+ точки, сдвиг offset по нормали (от z-конфликта),
    обход выравнивается под заданную нормаль."""
    P = [np.array(p, dtype=float) for p in pts]
    n = Mesh._newell(pts)
    if normal is not None:
        if float(np.dot(n, normal)) < 0:
            P.reverse()
            n = -n
        nn = np.array(normal, dtype=float) / np.linalg.norm(normal)
    else:
        nn = n / max(np.linalg.norm(n), 1e-12)
    mesh.add([tuple(p + nn * offset) for p in P], cell, mat, group)
