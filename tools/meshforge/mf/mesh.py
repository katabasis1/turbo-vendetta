"""Меш MeshForge: многоугольники (материал, клетка атласа, параметр градиента) → треугольники glTF.

Система координат — как в Godot: +Y вверх, −Z вперёд (нос машины), +X вправо, метры.
Обход вершин многоугольника — против часовой стрелки, если смотреть снаружи (лицевая сторона glTF).

Нормали: автосглаживание по углу. Вершина берёт сумму нормалей соседних треугольников той же группы
сглаживания, если угол между гранями < smooth_angle; группа 0 — всегда плоская грань (жёсткие рёбра).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import atlas

EPS_AREA = 1e-7


@dataclass
class Poly:
    pts: list            # [(x, y, z)] ≥ 3, против часовой снаружи
    cell: str            # клетка атласа (палитра / псевдоним) или градиент (atlas.RAMPS)
    mat: str = "atlas"   # 'atlas' | 'emissive'
    group: int = 0       # 0 = плоская; >0 = сглаживается внутри группы
    t: list | None = None  # параметр градиента на вершину (для градиентных клеток)


class Mesh:
    def __init__(self, name: str, smooth_angle: float = 30.0):
        self.name = name
        self.smooth_angle = smooth_angle
        self.polys: list[Poly] = []

    # ------------------------------------------------------------ сборка
    def add(self, pts, cell, mat="atlas", group=0, t=None) -> None:
        pts = [tuple(float(c) for c in p) for p in pts]
        # убрать подряд идущие совпадающие точки (вырожденные рёбра лофта)
        clean, tt = [], []
        for i, p in enumerate(pts):
            if not clean or np.linalg.norm(np.subtract(p, clean[-1])) > 1e-6:
                clean.append(p)
                tt.append(None if t is None else t[i])
        if len(clean) > 1 and np.linalg.norm(np.subtract(clean[0], clean[-1])) < 1e-6:
            clean.pop()
            tt.pop()
        if len(clean) < 3:
            return
        self.polys.append(Poly(clean, cell, mat, group, None if t is None else tt))

    def extend(self, polys) -> None:
        self.polys.extend(polys)

    def copy(self) -> "Mesh":
        m = Mesh(self.name, self.smooth_angle)
        m.polys = [Poly(list(p.pts), p.cell, p.mat, p.group, None if p.t is None else list(p.t)) for p in self.polys]
        return m

    def transformed(self, fn) -> "Mesh":
        """fn: (x, y, z) -> (x, y, z). Если fn меняет ориентацию (зеркало), обход разворачивается — см. mirrored_x."""
        m = self.copy()
        for p in m.polys:
            p.pts = [tuple(fn(*q)) for q in p.pts]
        return m

    def mirrored_x(self) -> "Mesh":
        m = self.transformed(lambda x, y, z: (-x, y, z))
        for p in m.polys:
            p.pts.reverse()
            if p.t is not None:
                p.t.reverse()
        return m

    # ------------------------------------------------------------ треугольники
    @staticmethod
    def _newell(pts) -> np.ndarray:
        n = np.zeros(3)
        for i in range(len(pts)):
            a, b = np.array(pts[i]), np.array(pts[(i + 1) % len(pts)])
            n += np.array([(a[1] - b[1]) * (a[2] + b[2]), (a[2] - b[2]) * (a[0] + b[0]), (a[0] - b[0]) * (a[1] + b[1])])
        return n

    @staticmethod
    def _triangulate(pts) -> list[tuple[int, int, int]]:
        k = len(pts)
        if k == 3:
            return [(0, 1, 2)]
        if k == 4:  # четырёхугольник — по короткой диагонали (меньше «ломаных» граней)
            p = [np.array(q) for q in pts]
            if np.linalg.norm(p[0] - p[2]) <= np.linalg.norm(p[1] - p[3]):
                return [(0, 1, 2), (0, 2, 3)]
            return [(0, 1, 3), (1, 2, 3)]
        # отсечение ушей в плоскости многоугольника
        n = Mesh._newell(pts)
        ln = np.linalg.norm(n)
        if ln < 1e-12:
            return []
        n /= ln
        ax = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
        u = np.cross(n, ax); u /= np.linalg.norm(u)
        v = np.cross(n, u)
        p2 = [(float(np.dot(q, u)), float(np.dot(q, v))) for q in map(np.array, pts)]
        idx = list(range(k))
        tris = []

        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        def inside(pt, a, b, c):
            return cross(a, b, pt) >= -1e-12 and cross(b, c, pt) >= -1e-12 and cross(c, a, pt) >= -1e-12

        guard = 0
        while len(idx) > 3 and guard < 10000:
            guard += 1
            best = None
            for j in range(len(idx)):
                i0, i1, i2 = idx[j - 1], idx[j], idx[(j + 1) % len(idx)]
                a, b, c = p2[i0], p2[i1], p2[i2]
                if cross(a, b, c) <= 1e-12:
                    continue
                if any(inside(p2[m], a, b, c) for m in idx if m not in (i0, i1, i2)):
                    continue
                # ухо с самым «толстым» треугольником — меньше иголок
                e = sorted([math.dist(a, b), math.dist(b, c), math.dist(c, a)])
                q = cross(a, b, c) / (e[2] ** 2 + 1e-12)
                if best is None or q > best[0]:
                    best = (q, j, (i0, i1, i2))
            if best is None:
                break
            tris.append(best[2])
            idx.pop(best[1])
        if len(idx) == 3:
            tris.append(tuple(idx))
        return tris

    def triangles(self):
        """→ список (mat, cell, group, [p0,p1,p2], [t0,t1,t2] | None, нормаль грани, площадь)."""
        out = []
        for p in self.polys:
            for a, b, c in self._triangulate(p.pts):
                P = [np.array(p.pts[i]) for i in (a, b, c)]
                cr = np.cross(P[1] - P[0], P[2] - P[0])
                area = 0.5 * float(np.linalg.norm(cr))
                if area < EPS_AREA:
                    continue
                tt = None if p.t is None else [p.t[i] for i in (a, b, c)]
                out.append((p.mat, p.cell, p.group, P, tt, cr / (2 * area), area))
        return out

    # ------------------------------------------------------------ буферы glTF
    def surfaces(self) -> dict[str, dict]:
        """По материалам: positions (N,3) float32, normals, uvs (N,2), indices (M,) — вершины без повторов."""
        tris = self.triangles()
        cos_lim = math.cos(math.radians(self.smooth_angle))
        # сосед по позиции: (группа, ключ позиции) → [(нормаль грани, площадь)]
        def pkey(p):
            return (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        acc: dict = {}
        for mat, cell, g, P, tt, fn, ar in tris:
            if g:
                for q in P:
                    acc.setdefault((g, pkey(q)), []).append((fn, ar))
        res: dict[str, dict] = {}
        for mat, cell, g, P, tt, fn, ar in tris:
            s = res.setdefault(mat, {"pos": [], "nrm": [], "uv": [], "idx": [], "map": {}})
            for k, q in enumerate(P):
                if g:
                    n = np.zeros(3)
                    for fn2, ar2 in acc[(g, pkey(q))]:
                        if float(np.dot(fn, fn2)) >= cos_lim:
                            n += fn2 * ar2
                    ln = np.linalg.norm(n)
                    n = fn if ln < 1e-12 else n / ln
                else:
                    n = fn
                uvv = atlas.uv(cell, None if tt is None else tt[k])
                key = (pkey(q), round(float(n[0]), 4), round(float(n[1]), 4), round(float(n[2]), 4),
                       round(uvv[0], 6), round(uvv[1], 6))
                vi = s["map"].get(key)
                if vi is None:
                    vi = len(s["pos"])
                    s["map"][key] = vi
                    s["pos"].append(q)
                    s["nrm"].append(n)
                    s["uv"].append(uvv)
                s["idx"].append(vi)
        out = {}
        for mat in sorted(res):
            s = res[mat]
            out[mat] = {
                "positions": np.asarray(s["pos"], dtype=np.float32),
                "normals": np.asarray(s["nrm"], dtype=np.float32),
                "uvs": np.asarray(s["uv"], dtype=np.float32),
                "indices": np.asarray(s["idx"], dtype=np.uint32),
            }
        return out

    def tri_count(self) -> int:
        return len(self.triangles())
