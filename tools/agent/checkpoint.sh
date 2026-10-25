#!/bin/bash
# Чекпоинт: /tmp/work → Pod. Запуск: bash tools/agent/checkpoint.sh
# 0) метка BuildInfo.STAMP 1) валидатор (если есть) 2) папки в /files/pod/project/ 3) архив builds/source_latest.zip
# (rsync и zip в Computer нет → tools/agent/sync_dir.py и make_zip.py)
# 4) копия архива в корень Pod (turbo-vendetta_latest.zip) — переживёт «сплющивание» Pod
# 5) снимок в builds/history/ (хранятся последние 15) 6) плоские копии AGENTS.md и docs/*.md в корень Pod
# 7) копия архива в файлы текущего разговора (если смонтированы): _latest + с меткой в имени 8) проверка архива
set -e
W=/tmp/work; P=/files/pod
cd "$W"
find "$W" -name __pycache__ -type d -prune -exec rm -rf {} +
STAMP=$(TZ=Europe/Moscow date '+%Y%m%d-%H%M')
# метка копии проекта (scenes/boot/build_info.gd): по ней видно, какой архив запущен у пользователя
BI=scenes/boot/build_info.gd
if [ -f "$BI" ]; then
  sed -i "s/^const STAMP: String = \".*\"$/const STAMP: String = \"$STAMP\"/" "$BI"
  grep -q "^const STAMP: String = \"$STAMP\"$" "$BI" || { echo "build_info.gd: метка не записана"; exit 1; }
fi
VAL="валидатора нет"
if [ -f tools/validate.py ]; then
  if python3 tools/validate.py > /tmp/validate.log 2>&1; then VAL="validate чисто"
  else VAL="validate: ЕСТЬ ОШИБКИ (см. /tmp/validate.log) — сохранено всё равно, исправить до закрытия подэтапа"; cat /tmp/validate.log | tail -20; fi
fi
mkdir -p "$P/project" "$P/builds/history"
python3 "$W/tools/agent/sync_dir.py" "$W" "$P/project"
rm -f /tmp/source_latest.zip
python3 "$W/tools/agent/make_zip.py" "$W" /tmp/source_latest.zip
cp /tmp/source_latest.zip "$P/builds/source_latest.zip"
cp /tmp/source_latest.zip "$P/turbo-vendetta_latest.zip"
cp /tmp/source_latest.zip "$P/builds/history/turbo-vendetta_$STAMP.zip"
# имена без пробелов; сортировка по имени = по времени (ГГГГММДД-ЧЧММ). Не `ls`: в Computer он переопределён функцией `ls -al`
find "$P/builds/history" -maxdepth 1 -name 'turbo-vendetta_*.zip' | sort -r | tail -n +16 | xargs -r rm -f
cp AGENTS.md "$P/AGENTS.md"
for f in docs/*.md docs/art/STYLE_REFERENCES.md; do cp "$f" "$P/$(basename "$f")"; done
cp tools/agent/restore.sh tools/agent/restore_flat.sh "$P/"
# в разговор — ещё и копия с меткой в имени: у одинаковых имён браузер дописывает «(1)», и распаковывают старый файл (17:12)
if [ -d /files/conversation ]; then
  cp /tmp/source_latest.zip /files/conversation/turbo-vendetta_latest.zip
  find -L /files/conversation -maxdepth 1 -name 'turbo-vendetta_2*.zip' -delete
  cp /tmp/source_latest.zip "/files/conversation/turbo-vendetta_$STAMP.zip"
fi
python3 -c "import zipfile,sys; z=zipfile.ZipFile(sys.argv[1]); assert z.testzip() is None" "$P/builds/source_latest.zip"
N_LOCAL=$(find "$W" -type f -not -path '*/.godot/*' | wc -l)
N_POD=$(find -L "$P/project" -type f | wc -l)
echo "checkpoint $STAMP ok: файлов локально $N_LOCAL, в project/ $N_POD, архив $(du -h /tmp/source_latest.zip | cut -f1); $VAL"
[ "$N_LOCAL" = "$N_POD" ] || { echo "РАСХОЖДЕНИЕ числа файлов!"; exit 1; }
