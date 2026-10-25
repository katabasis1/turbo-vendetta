"""Оболочка контура (S-19, D-018, STYLE_GUIDE v1.1 §3): отдельный узел `<имя>_outline` в .glb.

Зачем отдельный узел: у моделей MeshForge жёсткие рёбра (вершины разрезаны по граням), и вывернутая оболочка
по обычным нормалям рвётся на каждом ребре. Здесь вершины свариваются по позиции, а нормаль вершины —
сумма нормалей всех прилегающих треугольников с весом по углу при вершине (сглаженная нормаль). Оболочка
закрыта там, где закрыт кузов, и сдвигается шейдером `shaders/cel_outline.gdshader` по этой нормали.

Почему не второй канал (COLOR_0 / TEXCOORD_1) в том же меше: COLOR занят под AO (`cel_lit.use_vertex_color`),
а UV2 импортёр Godot может пересобрать под лайтмапы; обычная NORMAL отдельного меша читается без догадок.
Материал узла в .glb — `mf_outline` (alphaMode MASK, альфа 0): в превью редактора оболочка невидима,
в игре её материал заменяет `CarModelComponent` на cel_outline (ARCHITECTURE §8.5).

Берутся только поверхности материала 'atlas' (огни — эмиссия внутри силуэта, контур им не нужен).
"""
from __future__ import annotations

import numpy as np

WELD = 1e-4      # м: шаг сварки вершин по позиции


def hull(surfaces: dict, weld: float = WELD) -> tuple[dict, dict]:
    """surfaces — из Mesh.surfaces(). → ({'outline': буферы}, сводка {verts, tris, fallback})."""
    s = surfaces.get("atlas")
    if s is None:
        raise ValueError("оболочка контура: у узла нет поверхности 'atlas'")
    pos = s["positions"].astype(np.float64)
    nrm = s["normals"].astype(np.float64)
    idx = s["indices"].astype(np.int64).reshape(-1, 3)
    key = np.round(pos / weld).astype(np.int64)
    # порядок вершин — по первому появлению (детерминированно, без зависимости от хешей)
    _u, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    order = np.argsort(first, kind="stable")
    remap = np.empty_like(order)
    remap[order] = np.arange(len(order))
    vid = remap[inv]                       # исходная вершина → сваренная
    P = pos[first[order]]
    T = vid[idx]
    keep = (T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])
    T = T[keep]
    a, b, c = P[T[:, 0]], P[T[:, 1]], P[T[:, 2]]
    fn = np.cross(b - a, c - a)
    ln = np.linalg.norm(fn, axis=1, keepdims=True)
    good = ln[:, 0] > 1e-12
    T, a, b, c, fn = T[good], a[good], b[good], c[good], fn[good] / ln[good]

    def ang(p, q, r):  # угол при p
        u, v = q - p, r - p
        cu = np.einsum("ij,ij->i", u, v) / np.maximum(np.linalg.norm(u, axis=1) * np.linalg.norm(v, axis=1), 1e-12)
        return np.arccos(np.clip(cu, -1, 1))

    acc = np.zeros_like(P)
    for k, w in ((0, ang(a, b, c)), (1, ang(b, c, a)), (2, ang(c, a, b))):
        np.add.at(acc, T[:, k], fn * w[:, None])
    n_len = np.linalg.norm(acc, axis=1)
    # вырожденный случай (тонкая пластина без толщины: нормали гасят друг друга) — средняя исходная нормаль
    src = np.zeros_like(P)
    np.add.at(src, vid, nrm)
    fb = n_len < 1e-6
    acc[fb] = src[fb]
    n_len = np.linalg.norm(acc, axis=1)
    fb2 = n_len < 1e-6
    acc[fb2] = (0.0, 1.0, 0.0)
    N = acc / np.linalg.norm(acc, axis=1, keepdims=True)
    used = np.zeros(len(P), dtype=bool)
    used[T.ravel()] = True
    if not used.all():                      # вершины только вырожденных треугольников — выбросить
        new = np.cumsum(used) - 1
        P, N, T = P[used], N[used], new[T]
    out = {"outline": {
        "positions": P.astype(np.float32),
        "normals": N.astype(np.float32),
        "uvs": np.zeros((len(P), 2), dtype=np.float32),
        "indices": T.reshape(-1).astype(np.uint32),
    }}
    return out, {"verts": int(len(P)), "tris": int(len(T)), "fallback": int(fb.sum())}
