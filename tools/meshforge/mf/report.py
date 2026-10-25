"""Паспорт модели: треугольники против бюджета (STYLE_GUIDE §11), размеры против §5, замкнутость,
вырожденные грани, материалы. Ошибки — то, что ломает бюджет или сборку сцены; замечания — посмотреть глазами."""
from __future__ import annotations

import math
from collections import Counter

import numpy as np

from .mesh import Mesh


def edge_report(mesh: Mesh) -> tuple[int, int]:
    """(рёбер с одним треугольником, рёбер с > 2) по позициям вершин. 0, 0 — замкнутое тело без «плавников»."""
    cnt = Counter()
    def k(p):
        return (round(float(p[0]), 5), round(float(p[1]), 5), round(float(p[2]), 5))
    for _m, _c, _g, P, _t, _n, _a in mesh.triangles():
        ks = [k(p) for p in P]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            cnt[tuple(sorted((ks[a], ks[b])))] += 1
    return sum(1 for v in cnt.values() if v == 1), sum(1 for v in cnt.values() if v > 2)


def thin_triangles(mesh: Mesh, min_angle_deg: float = 2.0) -> int:
    n = 0
    for _m, _c, _g, P, _t, _n, _a in mesh.triangles():
        for i in range(3):
            a, b, c = P[i], P[(i + 1) % 3], P[(i + 2) % 3]
            u, v = b - a, c - a
            cs = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v) + 1e-12))
            if math.degrees(math.acos(max(-1.0, min(1.0, cs)))) < min_angle_deg:
                n += 1
                break
    return n


def bbox(meshes) -> tuple[np.ndarray, np.ndarray]:
    pts = np.array([p for m in meshes for poly in m.polys for p in poly.pts])
    return pts.min(axis=0), pts.max(axis=0)


def build_report(model, extra_tris: int = 0, hull: Mesh | None = None) -> dict:
    errors, notes = [], []
    tris = {n.name: n.tri_count() for n in model.nodes}
    total = sum(tris.values()) + extra_tris
    budget = model.meta.get("budget_tris")
    if budget and total > budget:
        errors.append(f"треугольников {total} > бюджета {budget}")
    mats = sorted({p.mat for n in model.nodes for p in n.polys})
    if len(mats) > 2:
        errors.append(f"материалов {len(mats)} > 2 (атлас + эмиссия, STYLE_GUIDE §11)")
    lo, hi = bbox(model.nodes)
    size = hi - lo
    rep = {"model": model.name, "out": model.out, "tris": tris, "tris_total": total, "budget": budget,
           "materials": mats, "bbox_min": [round(float(v), 4) for v in lo], "bbox_max": [round(float(v), 4) for v in hi],
           "size": [round(float(v), 4) for v in size], "anchors": {k: [round(float(c), 4) for c in v] for k, v in model.anchors.items()}}
    if model.meta.get("kind") == "car":
        L, W, H = model.meta["dims"]
        body = next(n for n in model.nodes if n.name == "body")
        blo, bhi = bbox([body])
        bs = bhi - blo
        g = model.meta["ground_y"]
        height = float(bhi[1] - g)
        length = float(bs[2])
        # ширина без зеркал: по точкам кузова ниже пояса
        w_body = 2 * max(abs(p[0]) for poly in (hull or body).polys for p in poly.pts)
        rep.update({"length": round(length, 3), "width_body": round(w_body, 3), "width_mirrors": round(float(bs[0]), 3),
                    "height": round(height, 3), "ground_clearance": round(float(blo[1] - g), 3)})
        for name, got, want in (("длина", length, L), ("ширина", w_body, W), ("высота", height, H)):
            if abs(got - want) / want > 0.03:
                errors.append(f"{name} {got:.3f} м ≠ {want} ±3% (STYLE_GUIDE §5)")
        # колёса в арках: шина внутри от X_INNER до края кузова
        r, wdt = model.meta["wheel_r"], model.meta["wheel_w"]
        tx = model.meta["track_x"]
        if tx - wdt / 2 < model.meta["x_inner"]:
            errors.append("шина задевает внутреннюю стенку арки")
        if tx + wdt / 2 > w_body / 2 + 0.01:
            notes.append(f"шина выступает за кузов на {tx + wdt / 2 - w_body / 2:.3f} м")
        a0 = model.anchors["wheel_fl"][1]
        if abs((a0 - r) - g) > 1e-3:
            errors.append(f"колесо не стоит на земле: низ шины {a0 - r:.3f}, земля {g}")
        rep["wheelbase"] = round(model.anchors["wheel_rl"][2] - model.anchors["wheel_fl"][2], 3)
    if hull is not None:
        open_e, fins = edge_report(hull)
        rep["hull_open_edges"], rep["hull_fins"] = open_e, fins
        if open_e or fins:
            errors.append(f"корпус не замкнут: открытых рёбер {open_e}, рёбер на > 2 гранях {fins}")
    for n in model.nodes:
        if n.name in model.closed:
            open_e, fins = edge_report(n)
            if open_e or fins:
                errors.append(f"{n.name}: не замкнут (открытых рёбер {open_e}, «плавников» {fins})")
        th = thin_triangles(n)
        if th:
            notes.append(f"{n.name}: тонких треугольников (угол < 2°) — {th}")
    rep["errors"], rep["notes"] = errors, notes
    return rep


def format_report(rep: dict) -> str:
    lines = [f"# {rep['model']} → {rep['out']}",
             f"треугольники: {rep['tris_total']} из {rep['budget']} ({', '.join(f'{k} {v}' for k, v in rep['tris'].items())}"
             + (f", колёса {rep['tris_total'] - sum(rep['tris'].values())}" if rep['tris_total'] != sum(rep['tris'].values()) else "") + ")",
             f"материалы: {', '.join(rep['materials'])}",
             f"габарит: {rep['size'][0]:.3f} × {rep['size'][1]:.3f} × {rep['size'][2]:.3f} м (X × Y × Z)"]
    if "length" in rep:
        lines.append(f"длина {rep['length']} · ширина кузова {rep['width_body']} (с зеркалами {rep['width_mirrors']}) · "
                     f"высота {rep['height']} · просвет {rep['ground_clearance']} · база {rep['wheelbase']}")
    if "hull_open_edges" in rep:
        lines.append(f"корпус: открытых рёбер {rep['hull_open_edges']}, «плавников» {rep['hull_fins']}")
    for e in rep["errors"]:
        lines.append(f"ОШИБКА: {e}")
    for n in rep["notes"]:
        lines.append(f"замечание: {n}")
    return "\n".join(lines)
