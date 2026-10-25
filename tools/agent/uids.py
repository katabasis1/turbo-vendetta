#!/usr/bin/env python3
"""Файлы <скрипт>.uid для новых .gd / .gdshader / .gdshaderinc (S-08, 2026-10-25).
Редактор 4.7 создаёт их сам при первом открытии проекта — тогда у пользователя появляются новые файлы, а сцены
агента ссылаются на скрипт без uid и после пересохранения меняются. Агент создаёт .uid сразу, вместе со скриптом.
UID детерминированный (tscn.godot_uid от res://-пути): повторный запуск ничего не меняет. Лежащие .uid не трогаются.
  python3 tools/agent/uids.py          # показать, у кого нет .uid
  python3 tools/agent/uids.py --fix    # создать недостающие"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tscn import godot_uid  # noqa: E402

EXT = (".gd", ".gdshader", ".gdshaderinc")
SKIP = {".git", ".godot", "builds", "docs", "tools", "__pycache__"}


def missing(root: str = ".") -> list:
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP)
        for f in sorted(files):
            p = os.path.join(d, f)
            if f.endswith(EXT) and not os.path.exists(p + ".uid"):
                out.append(os.path.relpath(p, root).replace(os.sep, "/"))
    return out


if __name__ == "__main__":
    a = sys.argv[1:]
    if a not in ([], ["--fix"]):
        print(__doc__); sys.exit(0 if a in (["-h"], ["--help"]) else 2)
    m = missing()
    for f in m:
        if a:
            open(f + ".uid", "w", encoding="utf-8").write(godot_uid("res://" + f) + "\n")
        print(("создан " if a else "нет ") + f + ".uid")
    print(f"uids: без .uid {0 if a else len(m)}" + (f", создано {len(m)}" if a else ""))
