#!/usr/bin/env python3
"""Замена zip (в Computer нет). usage: make_zip.py SRC_DIR OUT.zip  — исключает .godot/, проверяет архив."""
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
n = 0
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for d, dirs, files in os.walk(src):
        dirs[:] = sorted(x for x in dirs if x != '.godot')
        for f in sorted(files):
            full = os.path.join(d, f)
            z.write(full, os.path.relpath(full, src))
            n += 1
with zipfile.ZipFile(out) as z:
    bad = z.testzip()
    assert bad is None, f'битый файл в архиве: {bad}'
    assert len(z.namelist()) == n
print(f'zip: {n} файлов → {out} ({os.path.getsize(out) // 1024} КБ)')
