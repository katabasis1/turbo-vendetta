"""Описание модели для build.py: узлы-меши .glb + якоря (точки для сборки сцены в 1.3) + паспорт."""
from __future__ import annotations

from dataclasses import dataclass, field

from .mesh import Mesh


@dataclass
class Model:
    name: str                      # имя файла без .glb
    out: str                       # путь .glb от корня проекта (res://…)
    nodes: list[Mesh]              # узлы .glb по порядку
    anchors: dict = field(default_factory=dict)   # имя → (x, y, z): огни, колёса, контакты
    meta: dict = field(default_factory=dict)      # бюджет, размеры для проверок
    closed: list[str] = field(default_factory=list)  # узлы, которые должны быть замкнутыми (без дыр)
