#!/usr/bin/env python3
"""Тест сведения restore_github.py (без сети): zip-«коммиты» → эталон → рабочая копия во временной папке.
Запуск: python3 tools/agent/test_restore_github.py  → строка «test_restore_github ok».
Появился 2026-10-25 18:45 после того, как повторный restore при том же коммите затёр локальные правки."""
import contextlib
import io
import os
import sys
import tempfile
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import restore_github as R  # noqa: E402

T = tempfile.mkdtemp(prefix="rg_test_")
for k, v in dict(WORK="work", BASE="base", TREE="tree.json", HEAD="head.txt", PREV="prev.json",
                 MODS="mods.json", CONFL="confl", PACK="pack.zip").items():
    setattr(R, k, os.path.join(T, v))


def mkzip(name: str, commit: str, files: dict) -> str:
    p = os.path.join(T, name)
    with zipfile.ZipFile(p, "w") as z:
        z.comment = commit.encode()
        for f, b in files.items():
            z.writestr("repo-main/" + f, b)
    return p


def run(zp: str) -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return R.from_zip(zp, False)


def rd(f: str) -> str:
    p = os.path.join(R.WORK, f)
    return open(p).read() if os.path.exists(p) else None


def wr(f: str, s: str) -> None:
    p = os.path.join(R.WORK, f); os.makedirs(os.path.dirname(p), exist_ok=True); open(p, "w").write(s)


c1 = {"a.txt": "a1", "b.txt": "b1", "d/c.txt": "c1", "gone.txt": "g1"}
assert run(mkzip("1.zip", "c1", c1)) == 0 and rd("a.txt") == "a1" and rd("d/c.txt") == "c1"
wr("a.txt", "a-local"); wr("new.txt", "mine")
# 1) тот же коммит ещё раз — локальная правка остаётся (баг 18:40)
assert run(mkzip("1.zip", "c1", c1)) == 0 and rd("a.txt") == "a-local", rd("a.txt")
# 2) новый коммит: b изменён в GitHub, gone удалён, a не трогали → b подтянут, gone удалён, a и new на месте
c2 = {"a.txt": "a1", "b.txt": "b2", "d/c.txt": "c1"}
assert run(mkzip("2.zip", "c2", c2)) == 0
assert (rd("a.txt"), rd("b.txt"), rd("gone.txt"), rd("new.txt")) == ("a-local", "b2", None, "mine")
# 3) правка после restore + тот же коммит → снова остаётся
wr("d/c.txt", "c-local")
assert run(mkzip("2.zip", "c2", c2)) == 0 and rd("d/c.txt") == "c-local"
# 4) в GitHub лежит наш пакет (a = версия из pack.zip), локально поверх ещё правка → не конфликт, правка остаётся
with zipfile.ZipFile(R.PACK, "w") as z:
    z.writestr("a.txt", "a-pack")
wr("a.txt", "a-pack+more")
c3 = {"a.txt": "a-pack", "b.txt": "b2", "d/c.txt": "c1"}
assert run(mkzip("3.zip", "c3", c3)) == 0 and rd("a.txt") == "a-pack+more"
# 5) c правлен и локально, и в GitHub по-разному → конфликт: правка остаётся, версия GitHub — в confl/
c4 = {"a.txt": "a-pack", "b.txt": "b2", "d/c.txt": "c-gh"}
assert run(mkzip("4.zip", "c4", c4)) == 2 and rd("d/c.txt") == "c-local"
assert open(os.path.join(R.CONFL, "d/c.txt")).read() == "c-gh"
# 6) b не правлен локально → берётся из GitHub при каждом коммите; эталон = ровно zip
c5 = {"a.txt": "a-pack", "b.txt": "b3", "d/c.txt": "c-gh"}
run(mkzip("5.zip", "c5", c5))
assert rd("b.txt") == "b3" and sorted(os.listdir(R.BASE)) == ["a.txt", "b.txt", "d"]
# 7) неизвестный аргумент не запускает восстановление
sys.argv = ["x", "--help"]
with contextlib.redirect_stdout(io.StringIO()):
    assert R.main() == 0
sys.argv = ["x", "--bogus"]
with contextlib.redirect_stdout(io.StringIO()):
    assert R.main() == 2
print("test_restore_github ok:", T)
