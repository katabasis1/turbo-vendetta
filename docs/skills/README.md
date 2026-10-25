# docs/skills — навыки, которыми пользуется агент

Копии сделаны, чтобы не зависеть от сети: в Computer GitHub недоступен напрямую, файлы забраны через веб-браузер агента (2026-10-25).
Порядок работы с текстами — `docs/TEXT_PIPELINE.md`.

| Папка | Источник | Версия | Дата копии | Лицензия | Что внутри |
|---|---|---|---|---|---|
| `humanizer-ru/` | https://github.com/Vladimir-Human/humanizer-ru (`skills/humanizer-ru/`, ветка main, коммит 1f3960e / merge 89a1c92) | 4.1.5 | 2026-10-25 | MIT © 2026 Vladimir | `SKILL.md`, `references/patterns.md`, `references/examples.md`, `scripts/check_facts.py`, `scripts/clean_paste.py`, `LICENSE` |
| `humanizer-en/` | https://github.com/blader/humanizer (корень репозитория, ветка main, коммит 8c307f3) | 3.1.0 | 2026-10-25 | MIT © 2025 Siqi Chen | `SKILL.md`, `LICENSE` |
| `game-design/` | загружен пользователем в Pod (источник не записан) | — | до 2026-10-25 | не указана | `SKILL.md`, `references/5-component-rubric.md`, `domain-guide.md`, `templates.md`; **нет `references/patterns.md`**, на который ссылается `SKILL.md` |

Файлы не правились. Обновлять — новой копией целиком с записью в `docs/PROGRESS.md` и сменой строки в этой таблице.
Проверка скриптов (2026-10-25): `check_facts.py` ловит изменённые числа, `clean_paste.py` снимает невидимые символы, `contentReference` и `utm_source=chatgpt.com`.

## Проверка DoD 0.2 (2026-10-25 15:25 МСК) — очеловечивание без GitHub
Пробная строка (не игровая, в `strings.csv` не идёт; D-008 про нитро ещё открыт):
- черновик: «Важно отметить, что удержание кнопки дрифта в повороте позволяет осуществлять заполнение шкалы нитро на 25%.»
- после humanizer-ru (признаки №1 «пустая подводка», №4 «канцелярит»; обращение на «ты» по `TEXT_PIPELINE.md`): «Держи дрифт в повороте: шкала нитро заполнится на 25%.»
- `check_facts.py до.txt после.txt` → «ошибок не найдено»; 54 символа ≤ 70 (лимит строки обучения).
- en по humanizer: "Hold drift through the corner to fill 25% of the nitro bar."
