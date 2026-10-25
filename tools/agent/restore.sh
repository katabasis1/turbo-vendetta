#!/bin/bash
# Восстановление рабочей копии в /tmp/work. Порядок источников:
# 1) /files/pod/builds/source_latest.zip  2) /files/pod/turbo-vendetta_latest.zip
# 3) /files/pod/project/  4) «сплющенный» Pod (файлы в корне) → restore_flat.sh
set -e
P=/files/pod; W=/tmp/work
rm -rf "$W"; mkdir -p "$W"
if [ -f "$P/builds/source_latest.zip" ]; then unzip -q "$P/builds/source_latest.zip" -d "$W"; echo "из builds/source_latest.zip"
elif [ -f "$P/turbo-vendetta_latest.zip" ]; then unzip -q "$P/turbo-vendetta_latest.zip" -d "$W"; echo "из turbo-vendetta_latest.zip"
elif [ -d "$P/project" ]; then cp -r "$P/project/." "$W/"; echo "из project/"
else echo "архивов нет — запусти restore_flat.sh (Pod сплющен)"; exit 1; fi
head -12 "$W/docs/PROGRESS.md"
