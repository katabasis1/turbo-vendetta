#!/usr/bin/env python3
"""Восстановление рабочей копии из GitHub (D-017). Сети в Computer нет, поэтому файлы качает
инструмент веб-браузера через `dsbx` и каждый файл сверяется с git-хешем блоба из дерева репозитория.

ОСНОВНОЙ ПУТЬ (с 2026-10-25 18:20) — zip всего репозитория одним файлом:
  1) агент вызывает инструмент files__upload_from_url:
       url = https://codeload.github.com/katabasis1/turbo-vendetta/zip/refs/heads/main
       path = conversation-<id>/gh_fetch/repo.zip, content_type = application/octet-stream
     (браузер тут не нужен; zip приходит целиком, с картинками; sha коммита — в комментарии zip)
  2) python3 restore_github.py --zip /files/conversation/gh_fetch/repo.zip   # эталон + сведение в /tmp/work
     Хеши всех файлов считаются из zip; с --verify дерево ещё сверяется с API GitHub (1–2 запроса).
ЗАПАСНОЙ ПУТЬ — по файлам через браузер (если codeload недоступен):
  python3 restore_github.py                 # → эталон /tmp/gh_base (+ /tmp/gh_base_tree.json) → /tmp/work
  python3 restore_github.py --with-art      # + картинки docs/art/** (≈55 запросов к API, лимит GitHub 60/час)
  python3 restore_github.py --budget 100    # секунд на запуск (по умолчанию 100), дальше — запустить ещё раз
Повторный запуск докачивает только то, что ещё не сошлось по хешу. Код выхода 0 — всё нужное на месте.
Качает в эталон /tmp/gh_base (= состояние GitHub, с ним checkpoint.sh сравнивает изменения), потом сводит /tmp/work
тремя сторонами (прошлый эталон / GitHub / рабочая копия), v3 от 2026-10-25 18:45:
  «правлен локально» = отличается от прошлого эталона (прямая сверка хешей, не только список MODS);
  файл не правили локально → берём версию GitHub (в т.ч. то, что пересохранил редактор у пользователя);
  правили локально, а в GitHub он не менялся → оставляем правку; правка уже в GitHub → совпадает, ничего не делаем;
  правили и там и тут по-разному → КОНФЛИКТ: правка остаётся, версия GitHub кладётся в /tmp/gh_conflicts/<путь>;
  файл удалён в GitHub и не правился локально → удаляем и из рабочей копии.
Дерево GitHub запрашивается при каждом запуске (1 запрос к API): сменился коммит — новый эталон.
(2026-10-25 17:40: первая версия затёрла локальные правки; v1 не подтягивала изменения GitHub в рабочую копию.)

Как качается: sha коммита — api.github.com/.../git/ref/heads/main?nocache=<время>; дерево — .../git/trees/<коммит>?recursive=1;
tекст — raw.githubusercontent.com/<репо>/<коммит>/<путь> пачками по 16;
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
TREE = "/tmp/gh_base_tree.json"      # [{path, sha, size, url}] — дерево эталона
HEAD = "/tmp/gh_base_head.txt"       # sha коммита GitHub, которому соответствует TREE
PREV = "/tmp/gh_base_tree.prev.json" # дерево прошлого эталона (для трёхстороннего сведения)
MODS = "/tmp/gh_local_mods.json"     # пути, правленные в /tmp/work относительно прошлого эталона
CONFL = "/tmp/gh_conflicts"
PACK = "/files/pod/turbo-vendetta_changes_latest.zip"  # последний отданный пакет: его версия в GitHub — не конфликт
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


def adopt(new: list, commit: str) -> None:
    """Новое дерево GitHub: запомнить прошлое (PREV) и какие файлы правлены локально против него (MODS)."""
    head = open(HEAD).read().strip() if os.path.exists(HEAD) else ""
    if commit == head:
        print("коммит GitHub:", commit[:10], "(не менялся)"); return
    prev = json.load(open(TREE)) if os.path.exists(TREE) else []
    json.dump(prev, open(PREV, "w"), ensure_ascii=False)
    pv = {x["path"]: x["sha"] for x in prev}
    mods = []
    for path in sorted(set(pv) | {x["path"] for x in new}):
        w = os.path.join(WORK, path)
        if os.path.isfile(w):
            if path not in pv or blobsha(open(w, "rb").read()) != pv[path]:
                mods.append(path)
        elif path in pv and os.path.isfile(os.path.join(BASE, path)):
            mods.append(path)  # удалён локально (картинки docs/art, которых не качали, сюда не попадают)
    json.dump(mods if prev else [], open(MODS, "w"), ensure_ascii=False)
    json.dump(new, open(TREE, "w"), ensure_ascii=False)
    open(HEAD, "w").write(commit)
    print(f"коммит GitHub: {commit[:10]} (было {head[:10] or '—'}); локальных правок против прошлого эталона: {len(mods) if prev else 0}")


def from_zip(zpath: str, verify: bool) -> int:
    """Эталон из zip codeload (= git archive): все файлы, хеши считаем сами, sha коммита — комментарий zip."""
    import zipfile
    z = zipfile.ZipFile(zpath)
    commit = z.comment.decode("ascii", "replace").strip()
    names = [n for n in z.namelist() if not n.endswith("/")]
    root = names[0].split("/")[0] + "/"
    assert all(n.startswith(root) for n in names), "в zip не одна корневая папка"
    data = {n[len(root):]: z.read(n) for n in names}
    new = [{"path": p, "sha": blobsha(b), "size": len(b), "url": ""} for p, b in sorted(data.items())]
    print(f"zip: {len(new)} файлов, коммит {commit[:10] or '?'}")
    if verify:
        url = f"https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1"
        t = browse([url]).get(url, "")
        try:
            d = json.loads(t[t.index("{"): t.rindex("}") + 1])
            api = {x["path"]: x["sha"] for x in d["tree"] if x["type"] == "blob"}
            diff = [x["path"] for x in new if api.get(x["path"]) != x["sha"]] + [p for p in api if p not in data]
            if diff:
                print("zip НЕ совпал с деревом API:", *diff[:20], sep="\n  "); return 1
            print("сверено с деревом API: совпало", len(api))
        except (ValueError, KeyError):
            print("дерево API не получено (лимит?) — сверка пропущена")
    adopt(new, commit or "zip:" + new[0]["sha"])
    shutil.rmtree(BASE, ignore_errors=True)  # эталон = ровно содержимое zip, без старых файлов
    for p, b in data.items():
        f = os.path.join(BASE, p); os.makedirs(os.path.dirname(f) or ".", exist_ok=True); open(f, "wb").write(b)
    return merge(new, new, 0)


KNOWN = {"--zip", "--verify", "--budget", "--with-art"}


def main() -> int:
    a = sys.argv[1:]
    if "-h" in a or "--help" in a:
        print(__doc__); return 0
    vals = {a[i + 1] for i, x in enumerate(a[:-1]) if x in ("--zip", "--budget")}
    bad = [x for x in a if x not in KNOWN and x not in vals]
    if bad:  # 2026-10-25 18:40: `--help` молча запускал полное восстановление
        print("неизвестные аргументы:", *bad, "\n", __doc__); return 2
    if "--zip" in a:
        return from_zip(a[a.index("--zip") + 1], "--verify" in a)
    budget = float(a[a.index("--budget") + 1]) if "--budget" in a else 100.0
    with_art = "--with-art" in a
    left = lambda: budget - (time.time() - T0)  # noqa: E731
    # Инструмент браузера кэширует ответы (2026-10-25 18:12 отдал дерево прошлого коммита) → ссылку на ветку
    # берём с меткой времени в адресе, а дерево и файлы — по sha коммита (неизменяемые адреса, кэш не мешает).
    ref = f"https://api.github.com/repos/{REPO}/git/ref/heads/{BRANCH}?nocache={int(time.time())}"
    t = browse([ref]).get(ref, "")
    try:
        commit = json.loads(t[t.index("{"): t.rindex("}") + 1])["object"]["sha"]
        url = f"https://api.github.com/repos/{REPO}/git/trees/{commit}?recursive=1"
        t = browse([url]).get(url, "")
        d = json.loads(t[t.index("{"): t.rindex("}") + 1])
        d["commit"] = commit
    except (ValueError, KeyError):
        if not os.path.exists(TREE):
            print("дерево GitHub не получено:", t[:200]); return 1
        print("дерево GitHub не получено (лимит API?) — работаю с сохранённым", open(HEAD).read().strip() if os.path.exists(HEAD) else "")
        d = None
    if d is not None:
        assert not d.get("truncated"), "дерево обрезано API — качать по папкам"
        adopt([x for x in d["tree"] if x["type"] == "blob"], d["commit"])
    tree = json.load(open(TREE))
    want = [x for x in tree if with_art or not (x["path"].startswith(ART) and x["path"].lower().endswith(BIN))]
    skipped = len(tree) - len(want)
    todo = [x for x in want if not ok(x)]
    print(f"файлов в репо {len(tree)}, нужно {len(want)}, уже сошлось {len(want) - len(todo)}, пропущено картинок docs/art {skipped}")
    head = open(HEAD).read().strip() if os.path.exists(HEAD) else BRANCH
    raw = f"https://raw.githubusercontent.com/{REPO}/{head}/"
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
    return merge(tree, want, skipped)


def merge(tree: list, want: list, skipped: int) -> int:
    """Трёхстороннее сведение эталона (= GitHub) в рабочую копию. Повторный запуск безопасен."""
    prev = {x["path"]: x["sha"] for x in json.load(open(PREV))} if os.path.exists(PREV) else {}
    mods = set(json.load(open(MODS))) if os.path.exists(MODS) else set()
    pack: dict[str, str] = {}  # путь → git-хеш версии из последнего пакета (её залил пользователь)
    if os.path.exists(PACK):
        import zipfile
        with zipfile.ZipFile(PACK) as z:
            pack = {n: blobsha(z.read(n)) for n in z.namelist() if not n.endswith("/")}
    now = {x["path"]: x["sha"] for x in tree}
    for path in [p for p in prev if p not in now]:  # удалено в GitHub
        b = os.path.join(BASE, path)
        if os.path.isfile(b): os.remove(b)
    upd, add, keep, same, conf, deleted = [], [], [], [], [], []
    for x in want:
        path = x["path"]; src = os.path.join(BASE, path); dst = os.path.join(WORK, path)
        cur = blobsha(open(dst, "rb").read()) if os.path.isfile(dst) else None
        if cur == x["sha"]:
            if path in mods: same.append(path)
            continue
        # Правлен локально = есть в списке правок ИЛИ отличается от прошлого эталона (с которым рабочая копия была сведена).
        # 2026-10-25 18:40: раньше смотрели только MODS, а его считали лишь при смене коммита → повторный restore при том же
        # коммите затёр 5 файлов, правленных после прошлого restore (пакет 1819 + генераторы сцен). Теперь сверка прямая.
        local = path in mods or (bool(prev) and cur is not None and cur != prev.get(path))
        if local:
            if prev.get(path) == x["sha"] or pack.get(path) == x["sha"]:
                keep.append(path); continue  # в GitHub не менялся или там наш же пакет — правка поверх остаётся
            c = os.path.join(CONFL, path); os.makedirs(os.path.dirname(c), exist_ok=True); shutil.copy2(src, c)
            conf.append(path); continue
        os.makedirs(os.path.dirname(dst) or ".", exist_ok=True); shutil.copy2(src, dst)
        (upd if cur is not None else add).append(path)
    kept_gone = []
    for path in [p for p in prev if p not in now]:
        dst = os.path.join(WORK, path)
        if path in mods:
            kept_gone.append(path)  # удалён в GitHub, локально правился — оставлен
        elif os.path.isfile(dst):
            os.remove(dst); deleted.append(path)
    keep += [p + " (удалён в GitHub)" for p in kept_gone]
    json.dump(sorted({k for k in keep if not k.endswith(" (удалён в GitHub)")} | set(conf) | set(kept_gone)),
              open(MODS, "w"), ensure_ascii=False)
    open(PREV, "w").write(json.dumps(tree, ensure_ascii=False))  # сведено: следующий новый коммит сравниваем с этим
    for name, lst in (("обновлено из GitHub", upd), ("добавлено", add), ("удалено (нет в GitHub)", deleted),
                      ("локальные правки оставлены", keep), ("правка уже в GitHub", same), ("КОНФЛИКТ", conf)):
        if lst:
            print(f"{name}: {len(lst)}", *lst[:40], sep="\n  ")
    if conf:
        print(f"конфликты: версия GitHub — в {CONFL}/<путь>, в рабочей копии — локальная правка; свести руками")
    print(f"restore ok: эталон {BASE} = GitHub ({len(want)} файлов); {WORK}: обновлено {len(upd)}, добавлено {len(add)}, "
          f"удалено {len(deleted)}, правок оставлено {len(keep)}, конфликтов {len(conf)}"
          + (f"; картинки docs/art ({skipped}) не скачаны — они в GitHub" if skipped else ""))
    return 2 if conf else 0


if __name__ == "__main__":
    sys.exit(main())
