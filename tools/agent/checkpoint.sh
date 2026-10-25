#!/bin/bash
# Чекпоинт (D-017, с 2026-10-25 источник истины — GitHub). Запуск: bash tools/agent/checkpoint.sh
# Нужен эталон /tmp/gh_base (= GitHub на момент восстановления): python3 tools/agent/restore_github.py
# 0) метка BuildInfo.STAMP 1) валидатор 2) генератор project.godot == project.godot (формат редактора, S-08)
# 3) пакет изменений относительно GitHub: zip (поверх репозитория) + .patch (git apply) + .txt (список, как залить)
# 4) в файлы разговора — только последний пакет (накопительный: старые удаляются, чтобы не распаковали не тот)
# 5) в Pod: builds/changes/ (последние 15 пакетов) + turbo-vendetta_changes_latest.zip в корне
#    + плоские копии AGENTS.md и docs/*.md (их видят инструкции Pod и поиск, D-016 п.4) + restore_github.py
# 6) проверка архива. Без строки «checkpoint … ok» шаг не сохранён.
set -e
W=/tmp/work; B=/tmp/gh_base; P=/files/pod; C=/files/conversation; O=/tmp/changes_out
[ -d "$B" ] || { echo "нет эталона $B — сначала: python3 tools/agent/restore_github.py"; exit 1; }
cd "$W"
find "$W" -name __pycache__ -type d -prune -exec rm -rf {} +
STAMP=$(TZ=Europe/Moscow date '+%Y%m%d-%H%M')
BI=scenes/boot/build_info.gd
if [ -f "$BI" ]; then
  sed -i "s/^const STAMP: String = \".*\"$/const STAMP: String = \"$STAMP\"/" "$BI"
  grep -q "^const STAMP: String = \"$STAMP\"$" "$BI" || { echo "build_info.gd: метка не записана"; exit 1; }
fi
VAL="валидатора нет"
if [ -f tools/validate.py ]; then
  if python3 tools/validate.py > /tmp/validate.log 2>&1; then VAL="validate чисто"
  else VAL="validate: ЕСТЬ ОШИБКИ (см. /tmp/validate.log) — сохранено всё равно, исправить до закрытия подэтапа"; tail -20 /tmp/validate.log; fi
fi
GEN="project.godot = генератор"
python3 tools/agent/gen_project_godot.py | cmp -s - project.godot || GEN="project.godot ОТЛИЧАЕТСЯ от генератора — свести (правка руками или редактором?)"
rm -rf "$O"; python3 tools/agent/changes.py "$B" "$W" "$O" "$STAMP" > /tmp/changes.log; cat /tmp/changes.log
N="turbo-vendetta_changes_$STAMP"
python3 -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None" "$O/$N.zip"
if [ -d "$C" ]; then
  find -L "$C" -maxdepth 1 -name 'turbo-vendetta_changes_*' -delete
  cp "$O/$N.zip" "$O/$N.patch" "$O/$N.txt" "$C/"
fi
if [ -d "$P" ]; then
  mkdir -p "$P/builds/changes"
  cp "$O/$N.zip" "$O/$N.patch" "$O/$N.txt" "$P/builds/changes/"
  cp "$O/$N.zip" "$P/turbo-vendetta_changes_latest.zip"
  # сортировка по имени = по времени (ГГГГММДД-ЧЧММ); не `ls` — в Computer он переопределён
  find -L "$P/builds/changes" -maxdepth 1 -name 'turbo-vendetta_changes_*.zip' | sort -r | tail -n +16 | sed 's/\.zip$//' | while read -r f; do rm -f "$f".zip "$f".patch "$f".txt; done
  cp AGENTS.md "$P/AGENTS.md"
  for f in docs/*.md docs/art/STYLE_REFERENCES.md; do cp "$f" "$P/$(basename "$f")"; done
  cp tools/agent/restore_github.py "$P/"
fi
echo "checkpoint $STAMP ok: $(sed 's/ → .*//' /tmp/changes.log); $VAL; $GEN"
