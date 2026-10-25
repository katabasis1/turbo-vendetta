#!/usr/bin/env python3
"""Замена rsync -a --delete (rsync в Computer нет).
usage: sync_dir.py SRC DST [--exclude .godot]
Копирует новые/изменённые файлы (сравнение по размеру и md5), удаляет лишние в DST."""
import hashlib, os, shutil, sys

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def walk(root, excl):
    out = {}
    for d, dirs, files in os.walk(root, followlinks=True):
        dirs[:] = [x for x in dirs if x not in excl]
        for f in files:
            full = os.path.join(d, f)
            out[os.path.relpath(full, root)] = full
    return out

src, dst = sys.argv[1], sys.argv[2]
excl = {'.godot'}
if '--exclude' in sys.argv:
    excl.add(sys.argv[sys.argv.index('--exclude') + 1])
os.makedirs(dst, exist_ok=True)
s, d = walk(src, excl), walk(dst, set())
copied = deleted = 0
for rel, sp in s.items():
    dp = os.path.join(dst, rel)
    if rel in d and os.path.getsize(dp) == os.path.getsize(sp) and md5(dp) == md5(sp):
        continue
    os.makedirs(os.path.dirname(dp), exist_ok=True)
    shutil.copyfile(sp, dp)
    copied += 1
for rel, dp in d.items():
    if rel not in s:
        os.remove(dp)
        deleted += 1
for dd, dirs, files in os.walk(dst, topdown=False):
    if dd != dst and not os.listdir(dd):
        os.rmdir(dd)
print(f'sync: скопировано {copied}, удалено {deleted}, всего {len(s)}')
