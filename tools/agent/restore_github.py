#!/usr/bin/env python3
"""Восстановление рабочей копии из GitHub (D-017). Сети в Computer нет, поэтому файлы качает
инструмент веб-браузера через `dsbx` и каждый файл сверяется с git-хешем блоба из дерева репозитория.

usage (из любой папки; dsbx живёт только пока идёт команда bash — укладываемся в бюджет и перезапускаем):
  python3 restore_github.py                 # → эталон /tmp/gh_base (+ /tmp/gh_base_tree.json) → /tmp/work
  python3 restore_github.py --with-art      # + картинки docs/art/** (≈55 запросов к API, лимит GitHub 60/час)
  python3 restore_github.py --budget 100    # секунд на запуск (по умолчанию 100), дальше — запустить ещё раз
Повторный запуск докачивает только то, что ещё не сошлось по хешу. Код выхода 0 — всё нужное на месте.
Качает только в эталон /tmp/gh_base (= состояние GitHub, с ним checkpoint.sh сравнивает изменения). В /tmp/work
копирует лишь файлы, которых там нет: локальные правки не трогает (2026-10-25: первая версия их затёрла).

Как качается: дерево — api.github.com/.../git/trees/main?recursive=1; текст — raw.githubusercontent.com пачками по 16;
бинарное и всё, что не сошлось (браузер обрезает большие .tscn), — api.github.com/.../git/blobs/<sha> (base64);
если и так не сошлось — сцены спайков пересобираются генератором tools/agent/gen_spike_scenes.py и тоже сверяются.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

REPO = "katabasis1/turbo-vendetta"
BRANCH = "main"
WORK = "/tmp/work"
BASE = "/tmp/gh_base"
TREE = "/tmp/gh_base_tree.json"
BIN = (".png", ".jpg", ".jpeg", ".ogg", ".wav", ".glb", ".zip", ".ttf", ".otf", ".woff2")
ART = "docs/art/"
GENERATED = {  # файл → аргумент генератора (если браузер обрезал, а API не дал)
    "scenes/dev/spikes/props/dummy_car.tscn": "car", "scenes/dev/spikes/spike_render.tscn": "render",
    "scenes/dev/spikes/spike_vfx.tscn": "vfx", "scenes/dev/spikes/spike_audio.tscn": "audio",
}
T0 = time.time()


def blobsha(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def browse(urls: list[str]) -> dict[str, str]:
    r = subprocess.run(["dsbx", "tools", "--json", "--args-json", "-", "web_search_&_browse", "webbrowser"],
                       input=json.dumps({"urls": urls}), capture_output=True, text=True, timeout=110)
    out: dict[str, str] = {}
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        print("dsbx: не JSON —", (r.stderr or r.stdout)[:300]); return out
    for c in d.get("content", []):
        res = c.get("resource") or {}
        if "text" in res and res.get("requestedUrl") and res["requestedUrl"] not in out:
            out[res["requestedUrl"]] = res["text"]
    return out


def ok(x: dict) -> bool:
    p = os.path.join(BASE, x["path"])
    return os.path.isfile(p) and blobsha(open(p, "rb").read()) == x["sha"]


def save(x: dict, b: bytes) -> bool:
    if blobsha(b) != x["sha"]:
        for alt in (b + b"\n", b.rstrip(b"\n") + b"\n", b.rstrip(b"\n")):
            if blobsha(alt) == x["sha"]:
                b = alt; break
        else:
            return False
    p = os.path.join(BASE, x["path"]); os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    open(p, "wb").write(b)
    return True


def main() -> int:
    a = sys.argv[1:]
    budget = float(a[a.index("--budget") + 1]) if "--budget" in a else 100.0
    with_art = "--with-art" in a
    left = lambda: budget - (time.time() - T0)  # noqa: E731
    if not os.path.exists(TREE):
        url = f"https://api.github.com/repos/{REPO}/git/trees/{BRANCH}?recursive=1"
        t = browse([url]).get(url, "")
        d = json.loads(t[t.index("{"): t.rindex("}") + 1])
        assert not d.get("truncated"), "дерево обрезано API — качать по папкам"
        json.dump([x for x in d["tree"] if x["type"] == "blob"], open(TREE, "w"), ensure_ascii=False)
        print("дерево:", d["sha"])
    tree = json.load(open(TREE))
    want = [x for x in tree if with_art or not (x["path"].startswith(ART) and x["path"].lower().endswith(BIN))]
    skipped = len(tree) - len(want)
    todo = [x for x in want if not ok(x)]
    print(f"файлов в репо {len(tree)}, нужно {len(want)}, уже сошлось {len(want) - len(todo)}, пропущено картинок docs/art {skipped}")
    raw = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/"
    text = [x for x in todo if not x["path"].lower().endswith(BIN)]
    for i in range(0, len(text), 16):
        if left() < 20: break
        batch = text[i:i + 16]
        got = browse([raw + x["path"] for x in batch])
        for x in batch:
            t = got.get(raw + x["path"])
            if t is not None:
                save(x, b"" if x["size"] == 0 else t.encode("utf-8"))
    for x in [x for x in want if not ok(x)]:  # бинарное и не сошедшееся — через API (base64)
        if left() < 15: break
        t = browse([x["url"]]).get(x["url"], "")
        try:
            j = json.loads(t[t.index("{"): t.rindex("}") + 1]); save(x, base64.b64decode(j["content"]))
        except (ValueError, KeyError) as e:
            print("API:", x["path"], "—", str(e)[:80], "(лимит 60 запросов/час?)")
    bad = [x for x in want if not ok(x)]
    if bad and any(x["path"] in GENERATED for x in bad) and os.path.exists(os.path.join(BASE, "tools/agent/gen_spike_scenes.py")):
        tmp = "/tmp/gh_regen"; shutil.rmtree(tmp, ignore_errors=True); shutil.copytree(BASE, tmp)
        for x in [x for x in bad if x["path"] in GENERATED]:
            subprocess.run([sys.executable, "tools/agent/gen_spike_scenes.py", GENERATED[x["path"]]], cwd=tmp, capture_output=True)
            if save(x, open(os.path.join(tmp, x["path"]), "rb").read()):
                print("сцена из генератора, хеш сошёлся:", x["path"])
        bad = [x for x in want if not ok(x)]
    if bad:
        print(f"НЕ СОШЛОСЬ {len(bad)} (запустить ещё раз):", *[x["path"] for x in bad[:20]], sep="\n  ")
        return 1
    added = 0
    for x in want:  # в рабочую копию — только недостающее, правки не трогаем
        dst = os.path.join(WORK, x["path"])
        if not os.path.exists(dst):
            os.makedirs(os.path.dirname(dst) or ".", exist_ok=True); shutil.copy2(os.path.join(BASE, x["path"]), dst); added += 1
    print(f"restore ok: эталон {BASE} = GitHub ({len(want)} файлов), в {WORK} добавлено {added}, локальные правки не тронуты" + (f"; картинки docs/art ({skipped}) не скачаны — они в GitHub" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
