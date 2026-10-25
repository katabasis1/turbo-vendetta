# Концепт-арты для выбора стиля (этап 0.3, решение D-006)

> **Статус 2026-10-25 (D-006):** основа — A «Неон-синтвейв» как жанр (синтвейв / аутран), но не в этом очевидном исполнении: прочтение выбрано в D-012 — **2 «Аниме-аутран 90-х»** (`docs/art/STYLE_REFERENCES.md`, `docs/STYLE_GUIDE.md`). Эти арты — история выбора, ориентиром для ассетов не служат. **B — отклонён полностью** (мультяшный, игрушечный). **D «Неон-поп» — отклонён** (каша). Из **C** берём только комиксовую вспышку и линии скорости в момент тарана.


Сгенерированы 2026-10-25 как ориентир настроения, а не как готовые ассеты. Машины на артах — заглушки: финальные модели делает MeshForge по STYLE_GUIDE, без сходства с реальными авто. Сцена одинаковая для честного сравнения: камера за машиной, занос, таран соперника, петля на фоне.

| Файл | Вариант | Сильное | Риски для WebGL 2 / телефона |
|---|---|---|---|
| `concept_A_neon_synthwave.png` | A «Неон-синтвейв» | Самый эффектный кадр, простая геометрия, свечение «продаёт» скорость | Держится на bloom/glow — проверить стоимость в Compatibility (спайк 0.6). Тёмная картинка хуже читается на телефоне на улице. Синтвейв в браузерных гонках частый |
| `concept_B_pop_daylight.png` | B «Поп-день» | Лучшая читаемость на маленьком экране, широкая аудитория, яркая плитка в каталоге, дешёвый рендер (toon-освещение без тяжёлой постобработки) | Может выглядеть «детским» и менее соревновательным |
| `concept_D_neon_pop_hybrid.png` | D «Неон-поп» (гибрид, рекомендация) | Основа B (день, конфетная палитра, toon-тени), неон A только акцентами (канты трассы, подсветка и шлейфы машины), комикс-вспышка C только на такдауне. Читается на телефоне, при этом выглядит «дороже» B | Bloom нужен только на неоновых частях — проверить выборочное свечение в Compatibility (спайк 0.6); вспышку такдауна делать спрайтом/billboard, а не постэффектом |
| `concept_C_anime_manga.png` | C «Аниме-манга» | Самый узнаваемый, такдауны как кадры комикса | Обводка = доп. проход (inverted hull, ×2 вершин) или пост-эффект по глубине; халфтон — экранный шейдер. Самый дорогой в производстве и производительности |

Рекомендация агента без изменений: «Неон-поп» = B как основа, неоновые канты и шлейфы из A, ночные трассы как условие, комикс-вспышки такдаунов из C. 4-й арт гибрида сделан 2026-10-25 (`concept_D_neon_pop_hybrid.png`). Следующий шаг после выбора — `docs/STYLE_GUIDE.md`.

## Промпты (для повторной генерации)
- A: stylized 3D game screenshot, chase cam, neon synthwave night, floating track with magenta/cyan neon edges, retro striped sun, wireframe grid, neon loop; wedge racer with pink trim, cyan underglow, light trails, drifting; rival with orange trim rammed into barrier, sparks; strong bloom; low-poly; no text/UI.
- B: same scene, pop daylight, candy palette (coral, mint, lemon, sky blue), cel-shaded; chunky toy-like racer lemon yellow with coral stripe, toon smoke puffs; mint rival spins with star sparks and confetti; seaside canyon, colorful loop; no text/UI.
- D: same scene, NEON-POP hybrid: bright candy cel-shaded daytime base, warm late-afternoon peach-to-blue sky; track edges/curbs with hot pink and cyan neon strips; coral-red chunky racer with lemon stripe, cyan emissive trim, underglow, neon light trails, toon smoke; mint rival rammed inside a comic impact burst with ink outline (no letters), manga speed lines at screen edges, star sparks, confetti; bloom only on neon; no text/UI.
- C: same scene, anime/manga cel-shading, thick ink outlines, halftone, speed lines; mountain pass at dusk; white racer with red stripe drifting, ink smoke; blue rival rammed into guardrail, comic impact burst without letters; no text/UI.
