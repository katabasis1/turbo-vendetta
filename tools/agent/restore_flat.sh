#!/bin/bash
# Сборка структуры из «сплющенного» Pod (все файлы в корне). Так восстанавливали 2026-10-25 15:25 МСК.
# Скрипт лежит и в архиве, и в корне Pod (restore_flat.sh). Дубликаты *-1.*, *_fil_*.*, _*.jpg игнорируются.
set -e
P=/files/pod; W=/tmp/work; rm -rf "$W"; mkdir -p "$W"; cd "$W"
mkdir -p docs/art/concepts docs/art/references/raw docs/art/style_frames/src docs/art/style_frames/wip docs/brief docs/skills/game-design/references tools/agent
cp $P/AGENTS.md .
for f in CONCEPT ARCHITECTURE PLAN PROGRESS DECISIONS STYLE_GUIDE TEXT_PIPELINE SPIKES NAMING; do [ -f $P/$f.md ] && cp $P/$f.md docs/; done
cp $P/STYLE_REFERENCES.md docs/art/; cp $P/palette.png docs/art/
cp $P/README.md docs/art/concepts/README.md
for c in concept_A_neon_synthwave concept_B_pop_daylight concept_C_anime_manga concept_D_neon_pop_hybrid; do cp $P/$c.png docs/art/concepts/; done
cp $P/README_fil_EjhZxXfFIT8BjIT.md docs/art/references/README.md
cp $P/ref_dir1_darksynth.png $P/ref_dir2_anime_outrun.png $P/ref_dir3_techno_graphic.png $P/ref_dir4_wet_neon.png $P/style_dir1_darksynth.jpg docs/art/references/
for g in ballistic distance furi ghostrunner hifi inertial katana nfsu nightrunners redout2 txr; do cp $P/${g}_0.jpg $P/${g}_1.jpg docs/art/references/raw/; done
cp $P/README_fil_bnZYn8ZgUh4cKMa.md docs/art/style_frames/README.md
cp $P/frame_01_track.jpg $P/frame_02_garage.jpg $P/frame_03_results.jpg docs/art/style_frames/
cp $P/frame_03_results.py $P/palette_sheet.py docs/art/style_frames/src/
cp $P/t1b.jpg $P/t1c.jpg $P/t1d.jpg $P/t1e.jpg $P/cars2.jpg $P/fonts.png docs/art/style_frames/wip/
cp $P/pasted-text-1_2026-10-24_16-47-27.txt docs/brief/
cp $P/SKILL.md docs/skills/game-design/
cp $P/5-component-rubric.md $P/domain-guide.md $P/templates.md docs/skills/game-design/references/
cp $P/progress.py $P/sync_docs.sh tools/agent/ 2>/dev/null || true
echo "структура собрана: $(find . -type f | wc -l) файлов"
