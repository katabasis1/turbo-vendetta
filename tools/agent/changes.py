#!/usr/bin/env python3
"""Пакет изменений относительно GitHub (D-017): что заливать в репозиторий после чекпоинта.

usage: python3 tools/agent/changes.py BASE WORK OUTDIR STAMP
  BASE  — эталон = состояние GitHub (/tmp/gh_base, его делает restore_github.py)
  WORK  — рабочая копия (/tmp/work)
Пишет в OUTDIR:
  turbo-vendetta_changes_STAMP.zip   — изменённые и новые файлы по своим путям (распаковать поверх репозитория)
  turbo-vendetta_changes_STAMP.patch — то же для git: `git apply turbo-vendetta_changes_STAMP.patch`
  turbo-vendetta_changes_STAMP.txt   — список: M изменён / A новый / D удалить вручную + как залить
Пакет накопительный: всё, что отличается от GitHub на момент restore. Залили → следующий restore даст новый эталон.
.gitignore уважается (git add -A во временном репозитории).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile

SKIP_DIRS = {".git", ".godot", "__pycache__", "build"}


def copy_tree(src: str, dst: str) -> None:
    for d, dirs, files in os.walk(src):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
        for f in files:
            if f.endswith(".pyc"):
                continue
            s = os.path.join(d, f); r = os.path.relpath(s, src)
            os.makedirs(os.path.join(dst, os.path.dirname(r)), exist_ok=True)
            shutil.copy2(s, os.path.join(dst, r))


def git(cwd: str, *a: str) -> str:
    env = dict(os.environ, GIT_AUTHOR_NAME="agent", GIT_AUTHOR_EMAIL="agent@local",
               GIT_COMMITTER_NAME="agent", GIT_COMMITTER_EMAIL="agent@local")
    return subprocess.run(["git", "-c", "core.autocrlf=false", "-c", "core.quotepath=false", *a],
                          cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout


def main() -> int:
    base, work, out, stamp = sys.argv[1:5]
    os.makedirs(out, exist_ok=True)
    name = f"turbo-vendetta_changes_{stamp}"
    with tempfile.TemporaryDirectory() as td:
        repo = os.path.join(td, "r"); os.makedirs(repo)
        git(repo, "init", "-q")
        copy_tree(base, repo); git(repo, "add", "-A"); git(repo, "commit", "-qm", "github")
        for e in os.listdir(repo):  # рабочая копия поверх эталона: удаления тоже видны
            if e != ".git":
                p = os.path.join(repo, e); shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
        copy_tree(work, repo); git(repo, "add", "-A")
        status = [ln.split("\t") for ln in git(repo, "diff", "--cached", "--name-status", "--no-renames").splitlines()]
        patch = git(repo, "diff", "--cached", "--binary", "--no-renames")
        open(os.path.join(out, name + ".patch"), "w", encoding="utf-8").write(patch)
        zpath = os.path.join(out, name + ".zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for st, path in status:
                if st != "D":
                    z.write(os.path.join(repo, path), path)
    m = [p for s, p in status if s == "M"]; a = [p for s, p in status if s == "A"]; d = [p for s, p in status if s == "D"]
    lines = [f"Пакет изменений {stamp} относительно GitHub katabasis1/turbo-vendetta (main).",
             f"Изменено {len(m)}, новых {len(a)}, удалить {len(d)}.", "",
             "Как залить (любой способ):",
             f"  A) Сайт GitHub: распаковать {name}.zip → в репозитории «Add file → Upload files» →",
             "     перетащить ВСЁ содержимое распакованной папки (папки сохраняют пути) → Commit changes.",
             "     Файлы из списка D удалить вручную (открыть файл → … → Delete file).",
             f"  B) git: в папке репозитория `git apply {name}.patch` → `git add -A` → `git commit` → `git push`.",
             "  Не заливать поверх папку .godot/ и build/.", ""]
    lines += [f"M  {p}" for p in m] + [f"A  {p}" for p in a] + [f"D  {p}" for p in d]
    open(os.path.join(out, name + ".txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"changes {stamp}: M {len(m)}, A {len(a)}, D {len(d)} → {zpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
