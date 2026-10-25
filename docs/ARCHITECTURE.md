# ARCHITECTURE.md — как устроена «Турбовендетта»

> Этап 0.5. Статус: **v1 от 2026-10-25**, готов к сборке v0.0.1. Меняется вместе с кодом: новый компонент или контракт = строка в этом документе в том же чекпоинте. Решения: D-014 (контракт управления), D-015 (колонка `_status`).
> Основа — правила из `AGENTS.md` (композиция, никакой генерации объектов кодом, тексты по ключам, шейдеры с лицензией, Яндекс через `YandexSDK`).
> Цель документа (DoD 0.5): по нему можно собрать машину и трассу **без импровизаций**. Если при сборке приходится что-то придумывать, значит, документ неполон: дописываем сюда, а не в код.
> Любое число — стартовое значение: рядом стоит, как его проверить и куда крутить.

## 0. Коротко
- Каждая сущность — сцена `.tscn`. Корень — узел движка с тонким скриптом-**фасадом** (только ссылки на компоненты и `setup()`), под ним узлы-**компоненты** по одной ответственности.
- Компоненты связаны через `@export`-ссылки, назначенные в сцене. Вниз (от фасада и директора) идут вызовы методов, вверх — сигналы. Между сценами и автозагрузками события идут через `EventBus`.
- Все числа машины, камеры, трассы и «сока» лежат в ресурсах `.tres` (`CarSpec`, `ChaseCameraSpec`, `TrackSpec`, `TrackCondition`, `RaceRules`, `FeedbackSpec`). В рантайме ресурсы не меняются.
- Машина — `RigidBody3D` + 4 луча-колеса (`RayCast3D`). Силы подвески, мотора и сцепления прикладывают компоненты в `_physics_process` в строгом порядке (§8.4).
- Управление машиной пишет **один активный источник** (`PlayerInput`, `BotInput` или `GhostPlayback`) в общий узел `CarControlsComponent`. Остальные компоненты читают только его (D-014).
- Объекты в рантайме появляются только через `PackedScene.instantiate()` в шести разрешённых местах (§13).

## 1. Правила, уточнённые этим документом
| Правило AGENTS.md | Как применяем | Почему |
|---|---|---|
| «Корневой узел движка + компоненты» | у корня может быть **фасад**: `class_name Car extends RigidBody3D`. В фасаде только `@export` на компоненты, `setup()` и `reset_to()`, логики нет | спаунеру и UI нужен типизированный доступ к частям сущности без `get_node("…")` строкой |
| «Наследование напрямую от типа движка» | так же для фасадов, компонентов, источников управления. Никаких `extends Car`, `extends SomeComponent` | — |
| «Контракт управления: `throttle`, `brake`, `steer`, `drift` + 2 сигнала» | контракт живёт в узле `CarControlsComponent`. Источник пишет в него, читатели читают из него (D-014) | в GDScript нет интерфейсов, а базовые классы запрещены. Общий узел даёт статическую типизацию без утиной типизации через `get("throttle")` |
| «Никаких узлов через `.new()`» | `.new()` можно только для `RefCounted`/`Resource`-данных (`RaceEntry`, `RaceResult`), таймеры — через `get_tree().create_timer()`, анимации — `create_tween()` | это данные, а не объекты сцены |
| «Тексты — ключи в `strings.csv` (`keys,ru,en,status`)» | служебная колонка называется **`_status`**: Godot пропускает колонки, чьё имя начинается с `_`, а колонку `status` принял бы за язык (D-015) | документация `ResourceImporterCSVTranslation` (Godot 4.7) |

## 2. Папки `res://`
```
res://
├─ project.godot · export_presets.cfg · icon.svg · README.md · CHANGELOG.md · CREDITS.md · .gitignore
├─ autoload/            event_bus.gd · settings.gd · yandex_sdk.gd · pause_service.gd   (5.1: save_service.gd, 5.2: scene_router.gd)
├─ components/          скрипты компонентов, по доменам
│  ├─ car/              car_controls_component.gd · player_input.gd · bot_input.gd · ghost_playback.gd
│  │                    wheel_component.gd · suspension_component.gd · steering_component.gd · engine_component.gd
│  │                    grip_component.gd · stability_component.gd · impact_sensor_component.gd
│  │                    car_visual_component.gd · car_audio_component.gd · car_vfx_component.gd
│  ├─ track/            centerline_component.gd · checkpoint_component.gd · start_grid_component.gd
│  │                    fall_zone_component.gd · track_lighting_component.gd
│  ├─ race/             race_director.gd · car_spawner_component.gd · time_scale_component.gd
│  │                    feedback_director_component.gd · vfx_pool_component.gd
│  ├─ camera/           chase_camera_component.gd · camera_impulse_component.gd
│  └─ ui/               race_hud_component.gd · finish_screen_component.gd · touch_steer_component.gd
│                       touch_action_button_component.gd · speed_lines_component.gd · button_juice_component.gd
├─ data/
│  ├─ specs/            скрипты ресурсов: car_spec.gd · chase_camera_spec.gd · track_spec.gd · track_condition.gd
│  │                    race_rules.gd · feedback_spec.gd   (2.x: bot_profile.gd, 3.1: ability_spec.gd, 5.x: league_spec.gd, boss_spec.gd)
│  ├─ runtime/          RefCounted-данные заезда: race_entry.gd · race_result.gd
│  ├─ cars/             car_01.tres …
│  ├─ tracks/           track_01.tres …
│  ├─ conditions/       sunset.tres · night.tres · fog.tres · rain.tres · snow.tres · dust.tres
│  ├─ rules/            race_default.tres
│  ├─ camera/           chase_default.tres
│  └─ feedback/         wall_hit.tres · ram_dealt.tres · ram_taken.tres · takedown.tres · drift_scored.tres …
├─ scenes/
│  ├─ boot/             boot.tscn (+ boot.gd) — старт SDK, затем переход в гонку (v0.0.1) или в меню (5.2)
│  │                    build_info.gd (`BuildInfo.STAMP` — метка чекпоинта; пишет tools/agent/checkpoint.sh, руками не править)
│  ├─ car/              car.tscn + car.gd (фасад Car) · models/car_01_model.tscn · car_model.gd (фасад CarModel)
│  ├─ tracks/           track.gd (фасад Track) · track_01/track_01.tscn · modules/*.tscn (прямая, развязка, фонарь…)
│  ├─ race/             race.tscn
│  ├─ camera/           chase_camera.tscn
│  ├─ vfx/              one_shot_effect.gd (фасад OneShotEffect) · impact_flash.tscn · sparks_burst.tscn · …
│  ├─ ui/               hud.tscn · touch_controls.tscn · finish_screen.tscn · pause_menu.tscn · widgets/*.tscn
│  └─ dev/              dev_car_flat.tscn · dev_track_drive.tscn — тестовые сцены, **не входят в экспорт**
├─ assets/
│  ├─ models/           cars/car_01/car_01.glb · wheels/wheel_a.glb · track/*.glb   (результат tools/meshforge)
│  ├─ textures/         palette_atlas.png (256²) · windows_atlas.png (512²) · fx/*.png
│  └─ audio/            sfx/*.ogg · music/*.ogg · bus_layout.tres
├─ ui/                  fonts/ (подмножества Noto, STYLE_GUIDE §7.2) · theme/main_theme.tres · icons/*.svg
├─ shaders/             *.gdshader (шапка с лицензией, правило 4)
├─ localization/        strings.csv (keys,ru,en,_status) → strings.ru.translation · strings.en.translation
├─ platform/web/        shell.html · yandex_bridge.js (этап 2.6)
└─ tools/               validate.py · meshforge/ · audio_synth/ — с файлом .gdignore, Godot их не импортирует
```
Правило папок: скрипт компонента лежит в `components/<домен>/`, фасад — рядом со своей сценой в `scenes/…`, ресурс-класс — в `data/specs/`, экземпляры ресурсов — в `data/<вид>/`.

## 3. Настройки проекта (`project.godot`)
| Раздел | Ключ | Значение | Зачем / как проверить |
|---|---|---|---|
| application | `run/main_scene` | `res://scenes/boot/boot.tscn` | — |
| application | `config/features` | `"4.7", "GL Compatibility"` | Godot 4.7.2, WebGL 2 |
| rendering | `renderer/rendering_method` и `.mobile` | `gl_compatibility` | веб = только Compatibility |
| rendering | `textures/vram_compression/import_etc2_astc` | `true` | текстуры для мобильного веба; размер сборки — в спайке 0.6 |
| rendering | `anti_aliasing/quality/msaa_3d` | 0 (низкое) / 2× («Высокое качество») | FPS на телефоне ≥ 30 |
| display | `window/size/viewport_width/height` | 1280 × 720 | база UI (STYLE_GUIDE §7.3) |
| display | `window/stretch/mode`, `aspect` | `canvas_items`, `expand` | — |
| physics | `3d/physics_engine` | `Jolt Physics` (явно, не «по умолчанию») | Jolt — движок по умолчанию для новых проектов с Godot 4.6; рукописный `project.godot` должен указать его сам. Проверка — спайк S-03 |
| physics | `common/physics_ticks_per_second` | 60 | на слабом телефоне — 30 (спайк S-03) |
| physics | `common/physics_interpolation` | `true` | плавная картинка при 60 Гц физики и любом FPS; камера читает `get_global_transform_interpolated()` |
| physics | `common/max_physics_steps_per_frame` | 4 | не уходить в «спираль смерти» на слабом телефоне |
| debug | `gdscript/warnings/untyped_declaration` | 2 (ошибка) | правило 6 |
| debug | `gdscript/warnings/unsafe_property_access`, `unsafe_method_access`, `unsafe_cast`, `unsafe_call_argument` | 1 (предупреждение) | валидатор считает их, цель — 0 |
| input_devices | `pointing/emulate_touch_from_mouse` | `true` | тач-управление можно проверить мышью в редакторе |
| internationalization | `locale/translations` | `strings.ru.translation`, `strings.en.translation` | — |
| internationalization | `locale/fallback` | `en` | язык берём из SDK; всё, что не ru, — английский |
| audio | `buses/default_bus_layout` | `res://assets/audio/bus_layout.tres` | шины ниже |
| autoload | порядок | `EventBus`, `Settings`, `YandexSDK`, `PauseService` | каждый следующий может опираться на предыдущие |

**Формат файла — как у редактора (S-08, 2026-10-25).** Редактор 4.7.2 при импорте переписал `project.godot`: ни одна наша настройка не потерялась, но значения, **равные умолчаниям движка**, он не хранит — `msaa_3d=0`, `physics_ticks_per_second=60`, `locale/fallback="en"` в файле отсутствуют, и это значит «умолчание» (= значения из таблицы). Чтобы задать другое (2× MSAA, 30 Гц), ключ просто дописывается. Генератор `tools/agent/gen_project_godot.py` пишет файл побайтно как редактор (шапка, `\n, Object(` между событиями ввода, порядок ключей), `checkpoint.sh` сверяет. Файлы `*.uid` (скрипты, шейдеры) и `*.import` создаёт редактор — храним в git, `validate.py` проверяет формат и уникальность UID.

**Аудиошины:** `Master` → `Music`, `Sfx` (→ `Engines`), `Ui`. Пауза (потеря фокуса, реклама) глушит `Master`.

**Глобальные uniform шейдеров** (`[shader_globals]`, их пишет `TrackLightingComponent` из `TrackCondition`): `sun_dir: vec3`, `sun_color: color`, `shadow_tint: color` (`#402A69`), `rim_color: color` (`#F3A0A8`), `horizon_color: color`, `fog_color: color`, `fog_start: float` (60), `fog_end: float` (400). Запасной путь, если global uniforms в Compatibility подведут (S-01): uniform в каждом материале, значения раздаёт тот же компонент.

**Действия ввода** (только `physical_keycode`, правило 5):
| Действие | Клавиши | Тач (через `Input.action_press`) |
|---|---|---|
| `throttle` | W, ↑ | автогаз (`Settings.auto_throttle`) |
| `brake` | S, ↓ | свайп вниз / кнопка тормоза |
| `steer_left` / `steer_right` | A, ← / D, → | перетаскивание пальца (§11.3) |
| `drift` | Shift (левый), Space | авто-дрифт при резком руле (§8.3) |
| `ability_attack` / `ability_defense` | Q / E | кнопки 150×150 px справа |
| `pause` | Esc, P | кнопка паузы |
| `restart` | R | кнопка «Ещё раз» на итогах |

## 4. Слои коллизий
| № | Имя | Кто на слое | Маска (с кем сталкивается / кого видит) |
|---|---|---|---|
| 1 | `world` | дорога, отбойники, стены тоннелей (статические тела, CSG с `use_collision`) | — |
| 2 | `cars` | корень машины `RigidBody3D` | 1, 2, 5 |
| 3 | `triggers` | чекпоинты (`Area3D`) | 2 |
| 4 | `fall` | зоны падения (`Area3D`) | 2 |
| 5 | `projectiles` | снаряды способностей (этап 3.1) | 1, 2 |
| — | лучи колёс (`RayCast3D`) | — | **только 1**: колесо не должно «наступать» на соседнюю машину |

`Area3D` триггеров: `monitoring = true`, `monitorable = false`. Имена слоёв пишутся в `[layer_names]` → `3d_physics/layer_N`.

## 5. Автозагрузки
Все — скрипты `autoload/*.gd`, `extends Node`, движок сам создаёт узел. В автозагрузках нет игровой логики заезда: только платформа, настройки и глобальные события.

### 5.1 `EventBus`
Только сигналы, без состояния и методов. Сигнал попадает сюда, только если его слушают **в другой сцене или в автозагрузке**. Всё, что связано внутри одной сцены, соединяется через `@export`.

| Сигнал | Параметры | Кто шлёт | Кто слушает | С этапа |
|---|---|---|---|---|
| `race_started` | `track_id: StringName` | `RaceDirector` | `PauseService` (→ `gameplay_start`), музыка | 1.6 |
| `race_finished` | `result: RaceResult` | `RaceDirector` | `PauseService` (→ `gameplay_stop`), реклама 2.6, сохранение 5.1 | 1.6 |
| `race_left` | — | экран итогов / пауза | `PauseService` | 1.6 |

В каркасе 1.1 объявлены `race_started` и `race_left`. `race_finished` появится на 1.7: его тип `RaceResult` ссылается на `Car` (1.3).
| `car_rammed` | `attacker: Car, victim: Car, strength: float, point: Vector3` | `RamResolverComponent` | стиль 2.4, задания 5.x, статистика | 2.3 |
| `car_eliminated` | `victim: Car, by: Car` (`by` может быть `null`) | `RaceDirector` | итоги, задания, статистика | 2.3 |
| `style_scored` | `car: Car, kind: StringName, points: int` | `StyleScoreComponent` | HUD-счётчик, задания | 2.4 |
| `currency_changed` | `kind: StringName, total: int` | `SaveService` | гараж, магазин | 5.5 |

### 5.2 `Settings`
| Поле | Тип | Старт | Где используется |
|---|---|---|---|
| `volume_master / music / sfx` | `float` 0–1 | 0,8 / 0,6 / 0,9 | громкость шин |
| `vibration` | `bool` | `true` | `vibrate(ms)` |
| `reduce_flashes` | `bool` | `false` | вспышка ≤ 50 %, без негатив-кадра (STYLE_GUIDE §6) |
| `quality` | `enum Quality { LOW, HIGH }` | LOW на мобильных, HIGH на ПК | MSAA, Glow, частицы |
| `control_scheme` | `enum ControlScheme { AUTO, KEYBOARD, TOUCH }` | AUTO | показ тач-управления |
| `auto_throttle` | `bool` | `true` на тач | `PlayerInput` |
| `steer_sensitivity` | `float` 0,5–1,5 | 1,0 | `PlayerInput`, `TouchSteerComponent` |

Методы: `get_effective_scheme() -> ControlScheme` (AUTO решается по `YandexSDK.get_device_type()` и `DisplayServer.is_touchscreen_available()`), `vibrate(ms: int)` (уважает `vibration`, внутри — `Input.vibrate_handheld`, проверка в S-11), `save_settings()` / `load_settings()` (`ConfigFile`, `user://settings.cfg`; с этапа 5.1 — через `SaveService`; имя не `load()`, чтобы не перекрывать встроенную функцию GDScript), `set_value(key, value)` — меняет поле, применяет звук, сохраняет и шлёт сигнал `changed(key: StringName)`. Список полей — константа `KEYS`.

### 5.3 `YandexSDK`
Единственная точка общения с SDK Яндекса (правило 5). В редакторе и не-веб сборках работает **мок** (`OS.has_feature("web") == false`): те же методы и сигналы, реклама «показывается» за 1 с, награда выдаётся.

| Член | Что делает |
|---|---|
| `signal initialized` | SDK готов |
| `signal pause_requested(reason: StringName)` / `resume_requested(reason)` | вкладка скрыта/показана (`&"focus"`), реклама началась/закончилась (`&"ad"`) |
| `signal ad_closed(kind: StringName, shown: bool)` | конец рекламы |
| `signal reward_granted(reward_id: StringName)` | rewarded досмотрен |
| `func init() -> void` | вызывает `boot.tscn` |
| `func loading_ready() -> void` | `LoadingAPI.ready()`, когда игра готова к вводу |
| `func gameplay_start() / gameplay_stop() -> void` | `GameplayAPI`; вызывает только `PauseService` |
| `func show_interstitial() -> void` | только в паузе между заездами (2.6) |
| `func show_rewarded(reward_id: StringName) -> void` | награда — только бонус |
| `func get_lang() -> String` | `"ru"`, `"en"`… |
| `func get_device_type() -> StringName` | `&"desktop"`, `&"mobile"`, `&"tablet"`, `&"tv"` |

Мост к JS — `JavaScriptBridge` + `platform/web/yandex_bridge.js` (этап 2.6). До 2.6 работает только мок.

### 5.4 `PauseService`
Держит набор причин паузы: `&"focus"`, `&"ad"`, `&"menu"`. Пока набор не пуст, `get_tree().paused = true`. При `focus` и `ad` ещё и глушится шина `Master`.
- `request_pause(reason: StringName)`, `release_pause(reason: StringName)`, `is_paused() -> bool`, `has_reason(reason) -> bool`. Сигналы `paused(reason)`, `resumed(reason)`.
- Слушает `YandexSDK.pause_requested/resume_requested`, `NOTIFICATION_APPLICATION_FOCUS_OUT/IN`, `EventBus.race_started/race_finished/race_left`, сам вызывает `YandexSDK.gameplay_start/stop`.
- `process_mode = ALWAYS`. Меню паузы тоже `ALWAYS`, всё игровое — `PAUSABLE` (по умолчанию).

### 5.5 Позже
- `SaveService` (5.1): гостевой прогресс, облако Яндекса, `currency_changed`. Схема — в 5.1.
- `SceneRouter` (5.2): переходы между экранами через `change_scene_to_packed()`, экран загрузки, возврат «в одно касание».

## 6. Ресурсы данных (`data/specs/*.gd`, экземпляры `.tres`)
Все — `extends Resource`, `class_name XxxSpec`, поля только `@export` с типами и `@export_range`. В рантайме **не меняются**: если нужно изменяемое состояние, его держит компонент или объект из §7.
Единицы: в коде — метры, секунды, радианы, м/с. Поля в `км/ч` и градусах (так удобнее настраивать) имеют суффикс `_kmh` / `_deg` и переводятся при `configure()`.

### 6.1 `CarSpec` — машина
| Поле | Тип | Старт | Как проверить | Куда крутить |
|---|---|---|---|---|
| `id` | `StringName` | `&"car_01"` | — | — |
| `name_key`, `tagline_key` | `String` | `CAR_01_NAME`, `CAR_01_TAGLINE` | ключи есть в CSV (валидатор) | — |
| `visual_scene` | `PackedScene` | `car_01_model.tscn` | корень — `CarModel` | — |
| `mass_kg` | `float` | 1200 | — | не трогать: масса одна на всех, разница — в ощущении, а не в силе |
| `center_of_mass` | `Vector3` | (0, −0,35, 0,05) | на повороте 120 км/ч машина не опрокидывается | ниже, если кренится |
| `top_speed_kmh` | `float` | 250 | на главной прямой трассы 1 достигается за ~9 с | ±20 |
| `engine_force_n` | `float` | 11 000 | 0→100 км/ч ≈ 3,0 с (лог `EngineComponent`) | ±2 000 |
| `power_curve` | `Curve` | (0; 1) (0,6; 0,8) (1; 0) по доле от макс. скорости | разгон не «упирается» раньше 90 % | средняя точка |
| `brake_force_n` | `float` | 16 000 | 250→0 ≈ 5,5 с | ±3 000 |
| `reverse_force_n`, `reverse_top_kmh` | `float` | 5 000; 40 | задний ход из стены за ~1 с | — |
| `drag_coef` | `float` | 0,4 (Н на (м/с)²) | отпустил газ на 200 км/ч → −30 км/ч за 2 с | ±0,15 |
| `rolling_resist` | `float` | 30 (Н на м/с) | машина катится, а не встаёт | — |
| `wheel_radius_m` | `float` | 0,33 | колесо касается асфальта в покое | под модель |
| `suspension_rest_m` | `float` | 0,35 | — | 0,25–0,45 |
| `spring_n_per_m` | `float` | 21 000 | в покое сжатие ≈ 40 % хода | ±5 000 |
| `damper_ns_per_m` | `float` | 2 000 | после прыжка ≤ 1 колебание | ±600 |
| `anti_roll_n_per_m` | `float` | 8 000 | крен в повороте ≤ 4° | ±3 000 |
| `drive_split_rear` | `float` 0–1 | 0,6 | дрифт заходит, но машина не «крутится» на выходе | 0,5–0,8 |
| `steer_max_deg` / `steer_min_deg` | `float` | 32 / 7 (на макс. скорости) | шпилька на 60 км/ч проходится, прямая на 240 не виляет | ±4 |
| `steer_rate_deg_s` | `float` | 180 | руль на клавиатуре не дёргается | 120–260 |
| `grip_front` / `grip_rear` | `float` (μ) | 1,7 / 1,6 | поворот 90° на 120 км/ч без дрифта проходится | ±0,2 |
| `grip_response` | `float` 0–1 | 0,5 | доля боковой скорости, гасимая за такт | 0,3–0,8 |
| `drift_rear_grip_mult` | `float` | 0,55 | дрифт держится 1–3 с на руле | 0,4–0,7 |
| `drift_entry_slip_deg` / `drift_exit_slip_deg` | `float` | 8 / 4 | вход по кнопке без задержки, выход не «дребезжит» | — |
| `drift_exit_hold_s` | `float` | 0,25 | — | 0,15–0,4 |
| `drift_min_speed_kmh` | `float` | 50 | — | — |
| `drift_yaw_assist` | `float` | 1,5 | рулём можно «доворачивать» в заносе | 0,8–2,5 |
| `downforce_coef` | `float` | 1,6 (Н на (м/с)²) | на 220 км/ч прижим ≈ +50 % веса | ±0,6 |
| `air_level_torque` | `float` | 0,6 | после трамплина машина приземляется на колёса | 0,3–1,0 |
| `engine_loop` | `AudioStream` | `sfx/engine_01_loop.ogg` | — | — |
| `engine_pitch_min/max` | `float` | 0,7 / 1,8 | звук не «пищит» на максимуме | — |
| `gears` | `int` | 5 | слышны переключения | 4–6 |
| `trail_color` | `Color` | `#FF5FA2` | STYLE_GUIDE §6 | — |
| `attack`, `defense` | `AbilitySpec` | — (этап 3.1) | — | — |

### 6.2 `ChaseCameraSpec` — камера (STYLE_GUIDE §8)
`distance_m` 5,2 · `height_m` 1,6 · `look_height_m` 0,9 · `look_ahead_s` 0,15 (смещение точки взгляда по скорости) · `fov_min_deg` 68 · `fov_max_deg` 82 · `pos_half_life_s` 0,08 · `rot_half_life_s` 0,12 · `roll_max_deg` 2,5 · `trauma_decay_per_s` 1,6 · `shake_max_offset_m` 0,25 · `shake_max_angle_deg` 3.
Проверка: машина занимает ~25 % ширины кадра 1. Куда крутить — таблица §8 STYLE_GUIDE.

### 6.3 `TrackSpec` — трасса
`id: StringName` · `name_key: String` · `scene: PackedScene` (корень — `Track`) · `laps: int` (3) · `par_time_s: float` (для звезды «финиш», этап 2.4) · `condition: TrackCondition` · `preview: Texture2D` · `length_m: float` (справочно, валидатор сверяет с `Centerline`).
Ссылка идёт только от `TrackSpec` к сцене, сцена на `TrackSpec` не ссылается (иначе цикл ресурсов). Сцена знает только свой `track_id`.

### 6.4 `TrackCondition` — время суток и погода
Только палитра и мелкие числа (STYLE_GUIDE §2.6, стартовые цвета шести условий там же).
`id` · `name_key` · `sky_stops: PackedColorArray` (5) · `sun_dir: Vector3` · `sun_color` · `sun_size_deg` · `shadow_tint` · `rim_color` · `horizon_color` · `fog_color` · `fog_start_m` · `fog_end_m` · `ambient_mult: float` · `grip_mult: float` (закат/ночь 1,0, туман 1,0, дождь 0,85, пыль 0,9, снег 0,7) · `weather_vfx: PackedScene` (дождь/снег/пыль, иначе `null`).

### 6.5 `RaceRules` — правила заезда
`laps_override: int` (0 = из `TrackSpec`) · `countdown_s: int` (3) · `fall_policy: FallPolicy { RESPAWN, ELIMINATE }` (RESPAWN) · `respawn_penalty_s: float` (2,0) · `stuck_respawn_after_s: float` (2,0) · `finish_timeout_s: float` (30: после финиша игрока остальным даётся столько времени) · `max_cars: int` (8) · `player_grid_slot: int` (0 в v0.0.1) · `armor_segments: int` (3, этап 2.3).

### 6.6 `FeedbackSpec` — «сок» одного события (STYLE_GUIDE §9)
`flash_scale: float` (0 = без вспышки) · `hit_stop_s: float` · `slowmo_scale: float` · `slowmo_s: float` · `trauma: float` · `fov_kick_deg: float` · `speed_lines_alpha: float` · `speed_lines_s: float` · `vibrate_ms: int` · `sound: AudioStream` · `camera_only_if_player: bool` (`true`: тряска, хит-стоп и вибро — только если участвует игрок).
Стартовые `.tres`: `wall_hit` (0; 0; —; —; 0,3; 0; 0; 0; 30), `ram_dealt` (1,0; 0,06; —; —; 0,6; 6; 0,7; 0,4; 60), `ram_taken` (0,8; 0,06; —; —; 0,8; 0; 0; 0; 90), `takedown` (1,6; 0,06; 0,35; 0,8; 0,8; 6; 0,7; 0,4; 120). Настраиваются в `.tres` без правки кода.

## 7. Данные заезда (RefCounted, `data/runtime/`)
Создаются через `.new()` — это не узлы.
- `RaceEntry`: `car: Car` · `display_name: String` · `lap: int` · `next_checkpoint: int` · `lap_started_s: float` · `last_lap_s: float` · `best_lap_s: float` · `total_s: float` · `progress_m: float` (круги × длина + смещение по осевой) · `finished: bool` · `eliminated: bool` · `place: int`.
- `RaceResult`: `track_id: StringName` · `entries: Array[RaceEntry]` (по местам) · `player: RaceEntry` · `is_new_best_lap: bool`.

## 8. Сущность «Машина» — `scenes/car/car.tscn`
### 8.1 Дерево
Ось «вперёд» — **−Z** (как у `Node3D.basis.z` в Godot). Начало координат машины — центр шасси; в покое дорога на y ≈ −0,24.
```
Car                RigidBody3D       car.gd (фасад Car)  слой 2, маска 1|2|5; continuous_cd = true; contact_monitor = true;
│                                    max_contacts_reported = 4; can_sleep = false; center_of_mass_mode = CUSTOM; angular_damp = 1,0
├─ Hull            CollisionShape3D  BoxShape3D 1,8 × 0,7 × 4,3, position (0; 0,45; 0)   — один размер для всех машин
├─ Controls        Node              CarControlsComponent
├─ PlayerInput     Node              PlayerInput      (process_mode = DISABLED; включает Controls)
├─ BotInput        Node              BotInput         (этап 2.1; до него узла нет, ссылка в Controls пустая)
├─ GhostPlayback   Node              GhostPlayback    (этап 4.2; до него узла нет)
├─ Wheels          Node3D            — просто папка
│  ├─ WheelFL      RayCast3D         WheelComponent   (−0,78; 0,30; −1,35)  is_front, side = −1
│  ├─ WheelFR      RayCast3D         WheelComponent   ( 0,78; 0,30; −1,35)  is_front, side = +1
│  ├─ WheelRL      RayCast3D         WheelComponent   (−0,78; 0,30;  1,30)  side = −1
│  └─ WheelRR      RayCast3D         WheelComponent   ( 0,78; 0,30;  1,30)  side = +1
├─ Suspension      Node              SuspensionComponent
├─ Steering        Node              SteeringComponent
├─ Engine          Node              EngineComponent
├─ Grip            Node              GripComponent
├─ Stability       Node              StabilityComponent
├─ ImpactSensor    Node              ImpactSensorComponent
├─ Visual          Node3D            CarVisualComponent   (сюда при setup() встаёт CarModel)
├─ BlobShadow      MeshInstance3D    QuadMesh 2,2 × 4,8, шейдер blob_shadow (`#1B1030`, α 0,65)
├─ Vfx             Node3D            CarVfxComponent
│  ├─ TrailL, TrailR       CPUParticles3D   шлейфы стоп-сигналов
│  ├─ SmokeRL, SmokeRR     CPUParticles3D   дым дрифта
│  ├─ SkidRL, SkidRR       CPUParticles3D   следы шин (квады на дороге, local_coords = false)
│  └─ Sparks               CPUParticles3D   one_shot
└─ Audio           Node3D            CarAudioComponent
   ├─ EngineLoop   AudioStreamPlayer3D   шина Engines
   ├─ TireLoop     AudioStreamPlayer3D   шина Sfx
   └─ Impact       AudioStreamPlayer3D   шина Sfx, AudioStreamRandomizer
```
Лучи колёс: `target_position = (0; −(suspension_rest_m + wheel_radius_m); 0)` выставляет `configure()`, `collision_mask = 1`, `exclude_parent = true`. Проверка геометрии: ступица в покое на y = 0,30 − (0,35 − 0,14) = 0,09, низ колеса 0,09 − 0,33 = −0,24 — ровно дорога.

### 8.2 Фасад `Car` (`scenes/car/car.gd`)
```gdscript
class_name Car extends RigidBody3D
## Фасад машины: ссылки на компоненты + настройка. Логики здесь нет.

enum Role { PLAYER, BOT, GHOST, BOSS }

@export var controls: CarControlsComponent
@export var wheels: Array[WheelComponent] = []  # строго FL, FR, RL, RR
@export var suspension: SuspensionComponent
@export var steering: SteeringComponent
@export var engine: EngineComponent
@export var grip: GripComponent
@export var stability: StabilityComponent
@export var impact_sensor: ImpactSensorComponent
@export var visual: CarVisualComponent
@export var vfx: CarVfxComponent
@export var audio: CarAudioComponent

var spec: CarSpec
var role: Role = Role.PLAYER
var display_name: String = ""

func setup(p_spec: CarSpec, p_role: Role, p_name: String) -> void:
	spec = p_spec
	role = p_role
	display_name = p_name
	mass = spec.mass_kg
	center_of_mass = spec.center_of_mass
	for wheel: WheelComponent in wheels:
		wheel.configure(spec)
	suspension.configure(spec)
	steering.configure(spec)
	engine.configure(spec)
	grip.configure(spec)
	stability.configure(spec)
	visual.load_model(spec.visual_scene)
	vfx.attach(visual.model, spec)
	audio.configure(spec, role == Role.PLAYER)
	controls.switch_to(CarControlsComponent.source_for_role(role))

func reset_to(xform: Transform3D) -> void:
	linear_velocity = Vector3.ZERO
	angular_velocity = Vector3.ZERO
	global_transform = xform
	suspension.reset()
	grip.reset()
	reset_physics_interpolation()
```
`setup()` нельзя вызвать до `add_child()`: компонентам нужен `_ready`. Порядок у спаунера: `instantiate()` → `add_child()` → `setup()` → `reset_to(слот)`.

### 8.3 Компоненты машины: контракты
| Компонент (тип) | `@export` | Читает | Пишет / делает | Сигналы | Методы |
|---|---|---|---|---|---|
| `CarControlsComponent` (Node) | `player_input`, `bot_input`, `ghost_playback` | — | хранит `throttle` 0–1, `brake` 0–1, `steer` −1…1 (минус — влево), `drift: bool`, `locked: bool` (при `locked` читатели видят газ 0 и тормоз 1) | `ability_attack_pressed`, `ability_defense_pressed`, `source_changed(source)` | `switch_to(source: Source)` — включает один источник (`process_mode`), остальные выключает; `press_attack()`, `press_defense()` (игнорируются при `locked`); `reset()`; `static source_for_role(role) -> Source`. `enum Source { NONE, PLAYER, BOT, GHOST }` |
| `PlayerInput` (Node) | `controls` | действия ввода, `Settings` | пишет в `controls`; клавиатурный руль нарастает за 0,10 с и спадает за 0,06 с; на таче — автогаз и авто-дрифт (|руль| > 0,85 дольше 0,15 с) | — | — |
| `BotInput` (Node, 2.1) | `controls`, `car`, `profile: BotProfile` | линия гонки трассы | пишет в `controls` | — | `bind_track(track: Track)` |
| `GhostPlayback` (Node, 4.2) | `controls`, `car` | запись призрака | двигает машину кинематически (`freeze_mode = KINEMATIC`, `freeze = true`), в `controls` пишет записанные значения для колёс и звука | `released` | `play(data)`, `release_to_bot()`: `freeze = false`, скорость из записи, `controls.switch_to(BOT)` |
| `WheelComponent` (RayCast3D) | `is_front`, `side` (−1/+1) | луч | состояние: `is_grounded`, `contact_point`, `contact_normal`, `compression_m`, `load_n` (пишет подвеска), `steer_angle` (пишет руль → `rotation.y`), `slip` 0–1 (пишет сцепление), `spin_rad_s` | — | `configure(spec)`, `forward_dir()`, `side_dir()` |
| `SuspensionComponent` (Node) | `car`, `wheels` | колёса | пружина + демпфер по нормали в точке контакта (`car.apply_force`), стабилизатор по осям; `grounded_count`, `is_airborne`, `air_time_s` | `left_ground`, `landed(air_time_s: float, impact_speed: float)` | `configure(spec)`, `reset()` |
| `SteeringComponent` (Node) | `controls`, `car`, `front_wheels`, `grip` | `controls.steer`, скорость | угол колёс: `steer × lerp(max, min, скорость/макс.)`, со скоростью `steer_rate_deg_s`; в дрифте предел +30 % | — | `configure(spec)` |
| `EngineComponent` (Node) | `controls`, `car`, `wheels` | газ, тормоз, скорость | тяга вдоль колеса в плоскости контакта (сплит перед/зад `drive_split_rear`), тормоз, задний ход (тормоз на скорости < 1 м/с), сопротивление; `speed_mps` (со знаком), `speed_kmh`, `speed_ratio`, `rpm_ratio` (пила по передачам, для звука), `gear` | `gear_changed(gear: int)` | `configure(spec)` |
| `GripComponent` (Node) | `controls`, `car`, `wheels`, `engine`, `impact_sensor` | боковая скорость колёс, `drift` | боковая сила колеса `clamp(−v_бок × m/4 / dt × grip_response, ±μ × нагрузка)`; дрифт-автомат ЦЕПКОСТЬ ⇄ ЗАНОС (вход: кнопка `drift` + скорость ≥ мин. + руль; выход: угол < `exit` дольше `exit_hold`); в заносе задний μ × `drift_rear_grip_mult`, момент `drift_yaw_assist`; `is_drifting`, `slip_angle_rad`, `drift_time_s` | `drift_started`, `drift_ended(duration_s: float, max_slip_deg: float, clean: bool)` (`clean = false`, если был удар о борт) | `configure(spec)`, `reset()` |
| `StabilityComponent` (Node) | `car`, `suspension`, `engine`, `controls` | — | прижим `downforce_coef × v²` на земле; в воздухе выравнивание по горизонту и лёгкий доворот рулём; перевёрнута дольше `stuck_respawn_after_s` → сигнал | `stuck` | `configure(spec)` |
| `ImpactSensorComponent` (Node) | `car`, `wall_min_dv` (2,0 м/с), `car_min_dv` (1,5 м/с), `cooldown_s` (0,15) | контакты тела через `PhysicsServer3D.body_get_direct_state()` (проверка — S-04) | сила удара = импульс / масса (Δv, м/с) | `hit_wall(dv: float, point: Vector3, normal: Vector3)`, `hit_car(other: Car, dv: float, point: Vector3, normal: Vector3)` | — |
| `CarVisualComponent` (Node3D) | `car`, `wheels`, `steering`, `engine`, `controls`, `impact_sensor`, `blob_shadow` | всё выше | в `_process`: колёса (подвеска, вращение, поворот), крен ≤ 3° и клевок ≤ 2° кузова, стоп-сигналы, мигание белым на ударе | — | `load_model(scene)`, свойство `model: CarModel` |
| `CarVfxComponent` (Node3D) | `car`, `engine`, `grip`, `impact_sensor` | скорость, занос, удары | шлейфы при > 40 км/ч, дым и следы в заносе или при скольжении > 0,4, искры в точке удара; бюджет частиц по `Settings.quality` (STYLE_GUIDE §6) | — | `attach(model: CarModel, spec)` — переносит точки эмиссии на маркеры модели |
| `CarAudioComponent` (Node3D) | `engine`, `grip`, `suspension`, `impact_sensor`, `controls` | обороты, скольжение, удары, приземления | высота тона мотора по `rpm_ratio`, громкость шин по скольжению, удары с громкостью по Δv; у машины игрока затухание по расстоянию выключено | — | `configure(spec, is_player)` |

### 8.4 Порядок такта физики
Godot вызывает `_physics_process` по возрастанию `process_physics_priority` во **всём** дереве, поэтому сначала все источники управления всех машин, затем все подвески и так далее.
| Приоритет | Кто | Почему здесь |
|---|---|---|
| −20 | `PlayerInput` / `BotInput` / `GhostPlayback` | ввод готов до физики |
| −15 | `WheelComponent` ×4 (`force_raycast_update()`) | свежие контакты |
| −10 | `SuspensionComponent` | нагрузка колёс нужна сцеплению |
| −5 | `SteeringComponent` | угол колёс нужен тяге и сцеплению |
| 0 | `EngineComponent` | — |
| 5 | `GripComponent` | после тяги, чтобы ограничить суммарную силу |
| 10 | `StabilityComponent` | прижим и выравнивание |
| 15 | `ImpactSensorComponent` | контакты прошлого шага |
| 20 | уровень гонки (`RaceDirector`, `RamResolverComponent`) | прогресс, места, тараны |
В `_process` (кадр отрисовки): визуал, эффекты и звук машины, затем камера (0), затем импульсы камеры (10), затем HUD.

### 8.5 Визуальная сцена модели — `scenes/car/models/car_XX_model.tscn`
Корень — `Node3D` со скриптом-фасадом `CarModel` (`scenes/car/car_model.gd`). Геометрия — экземпляр `.glb` из MeshForge, без логики.
```
Car01Model         Node3D        car_model.gd (CarModel)
├─ BodyPivot       Node3D        крен и клевок кузова
│  └─ Body         (экземпляр assets/models/cars/car_01/car_01.glb)
├─ WheelFL … WheelRR   Node3D    пивоты на месте ступиц (те же x/z, что у лучей, y = 0,09) → экземпляр wheel_a.glb
├─ TailLightL, TailLightR   Marker3D   точки шлейфов (у каждой машины своя форма огней — STYLE_GUIDE §5)
├─ RearContactL, RearContactR   Marker3D  точки дыма и следов (y = −0,24)
├─ Nameplate       Marker3D      над крышей, для плашки БОСС/ПРИЗРАК (2.x)
└─ (BrakeLights)   MeshInstance3D  отдельный меш стоп-сигналов, если модель так собрана
```
`CarModel`: `@export var body_pivot`, `wheel_pivots: Array[Node3D]` (FL, FR, RL, RR), `tail_lights: Array[Marker3D]`, `rear_contacts: Array[Marker3D]`, `nameplate: Marker3D`, `brake_lights: Array[MeshInstance3D]`; методы `set_brake(on: bool)`, `set_flash(amount: float)`. Как именно включать стоп-сигнал (instance uniform или замена материала) — решает спайк S-06.

## 9. Сущность «Трасса» — `scenes/tracks/track_XX/track_XX.tscn`
### 9.1 Дерево
```
Track01            Node3D           track.gd (фасад Track): track_id, ссылки ниже
├─ Centerline      Path3D           CenterlineComponent   замкнутая кривая, bake_interval 0,5 м, наклон (tilt) — виражи
├─ Road            Node3D           — папка
│  ├─ Asphalt      CSGPolygon3D     mode PATH, path_node → Centerline, polygon (−7; 0) (7; 0) (7; −0,6) (−7; −0,6),
│  │                                path_interval 1,5 м, path_rotation PATH_FOLLOW, path_joined = true,
│  │                                path_continuous_u = true, path_u_distance 14, use_collision = true, слой 1, материал road
│  ├─ BarrierL     CSGPolygon3D     polygon (−7,6; 0) (−7; 0) (−7; 1,1) (−7,6; 1,1), те же настройки пути, материал barrier
│  └─ BarrierR     CSGPolygon3D     зеркально
├─ Checkpoints     Node3D
│  ├─ CP00         Area3D           CheckpointComponent index 0 = старт/финиш; BoxShape3D 18 × 8 × 2; слой 3, маска 2
│  │  └─ Respawn   Marker3D         на оси дороги, 1 м над асфальтом, смотрит по ходу (−Z)
│  └─ CP01 … CPnn  то же            каждые 80–150 м и обязательно до и после мест, где можно срезать
├─ StartGrid       Node3D           StartGridComponent
│  └─ Slot1 … Slot8   Marker3D      2 в ряд: x = ±3,5; ряды через 8 м назад; второй в ряду сдвинут на 4 м назад
├─ FallZones       Node3D
│  └─ Under        Area3D           FallZoneComponent; коробка под всей трассой на 25 м ниже дороги; слой 4, маска 2
├─ Lighting        Node             TrackLightingComponent  condition = data/conditions/sunset.tres
├─ Env             WorldEnvironment фон SKY (ShaderMaterial sky_sunset), tonemap LINEAR, glow выкл. (вкл. в HIGH), fog выкл. (туман в наших шейдерах)
├─ Decor           Node3D           экземпляры модулей (modules/*.tscn) и MultiMeshInstance3D фонарей и окон
└─ RacingLine      Path3D           линия гонки для ботов (этап 2.1)
```
Ширина дороги 14 м (STYLE_GUIDE §4: 8 машин и тараны). Длина круга трассы 1 — ~1,2 км (3 круга ≈ 90 с при средней 150 км/ч). Проверка: запись круга, таймкоды «событий пейзажа» каждые 3–5 с.

### 9.2 Компоненты трассы
| Компонент (тип) | `@export` | Что делает | Сигналы | Методы |
|---|---|---|---|---|
| `Track` (фасад, Node3D) | `track_id`, `centerline`, `checkpoints: Array[CheckpointComponent]` (порядок = индекс), `grid`, `fall_zones: Array[FallZoneComponent]`, `lighting`, `racing_line: Path3D` | — | — | — |
| `CenterlineComponent` (Path3D) | — | геометрия осевой | — | `length_m()`, `progress_at(global_pos) -> float` (метры вдоль осевой), `transform_at(offset_m) -> Transform3D`, `direction_at(offset_m) -> Vector3` |
| `CheckpointComponent` (Area3D) | `index: int`, `respawn: Marker3D` | `body_entered` → если тело `Car`, шлёт сигнал | `car_entered(car: Car, index: int)` | — |
| `StartGridComponent` (Node3D) | `slots: Array[Marker3D]` | — | — | `slot_count()`, `slot_transform(i) -> Transform3D` |
| `FallZoneComponent` (Area3D) | — | `body_entered` → `Car` | `car_fell(car: Car)` | — |
| `TrackLightingComponent` (Node) | `condition: TrackCondition`, `environment: WorldEnvironment`, `sky_material: ShaderMaterial` | в `_ready` пишет global uniforms (§3) и параметры неба | — | `apply(condition: TrackCondition)` |

### 9.3 Модули декора — `scenes/tracks/modules/*.tscn`
Корень `Node3D` без скрипта, внутри экземпляры `.glb` и, если нужна коллизия, `StaticBody3D` (слой 1). Пивот — на оси дороги, «вперёд» — −Z. Модули ставятся в `Decor` вручную; их `Transform3D` считает офлайн-скрипт `tools/track_layout.py` по точкам осевой и пишет прямо в `.tscn`. Фонари и окна — `MultiMeshInstance3D` с заранее посчитанными трансформами в `.tscn`. Это статические данные, правило 2 не нарушается.

## 10. Сцена гонки — `scenes/race/race.tscn`
### 10.1 Дерево
```
Race               Node3D            без скрипта
├─ RaceDirector    Node              RaceDirector              правила, состояния, места, время
├─ CarSpawner      Node              CarSpawnerComponent       машины в слоты решётки
├─ Track           (экземпляр track_01.tscn)                   v0.0.1 — прямо в сцене; с 5.2 — из TrackSpec через спаунер трассы
├─ Cars            Node3D            контейнер для машин
├─ ChaseCamera     (экземпляр chase_camera.tscn)
├─ TimeScale       Node              TimeScaleComponent        хит-стоп и замедление, process_mode ALWAYS
├─ Feedback        Node              FeedbackDirectorComponent события → вспышка, камера, время, вибро, звук
├─ VfxPools        Node3D
│  ├─ ImpactFlashPool   Node3D       VfxPoolComponent  scene = impact_flash.tscn, size 4
│  └─ SparksPool        Node3D       VfxPoolComponent  scene = sparks_burst.tscn, size 6
├─ Overlay         CanvasLayer       layer 1
│  └─ SpeedLines   ColorRect         SpeedLinesComponent (шейдер speed_lines, на весь экран, mouse_filter IGNORE)
├─ Hud             (экземпляр hud.tscn, CanvasLayer 10)
├─ TouchControls   (экземпляр touch_controls.tscn, CanvasLayer 11, видим только при TOUCH)
├─ FinishScreen    (экземпляр finish_screen.tscn, CanvasLayer 20, скрыт)
├─ PauseMenu       (экземпляр pause_menu.tscn, CanvasLayer 30, process_mode ALWAYS, скрыт)
└─ RaceAudio       Node
   ├─ Countdown    AudioStreamPlayer  шина Ui
   └─ Music        AudioStreamPlayer  шина Music
```
Связи в сцене (все через `@export`): `RaceDirector` → `track`, `spawner`, `rules`, `car_spec` (v0.0.1: одна машина); `ChaseCamera`, `Hud`, `Feedback` → `director`; `FinishScreen` → `director`; `Feedback` → `time_scale`, `camera_impulse`, `flash_pool`, `sparks_pool`, `speed_lines`.

### 10.2 `RaceDirector` — состояния
`enum State { SETUP, COUNTDOWN, RACING, FINISHED, RESULTS }`
| Состояние | Вход | Что происходит | Выход |
|---|---|---|---|
| SETUP | `_ready` | спаунер ставит машины, у всех `controls.locked = true` | сразу → COUNTDOWN |
| COUNTDOWN | — | `countdown_ticked(3…1)`, звук и цифры (STYLE_GUIDE §9) | после «1» → RACING |
| RACING | `locked = false`, `EventBus.race_started` | время = сумма `delta` физики (хит-стоп честно замедляет всех); чекпоинты по порядку; круг засчитывается на CP00 после всех остальных; места по `progress_m` | игрок финишировал → FINISHED |
| FINISHED | игроку `locked = true` (машина катится и тормозит) | остальные досчитываются не дольше `finish_timeout_s` | → RESULTS |
| RESULTS | `EventBus.race_finished(result)` | `FinishScreen.show_result(result)` | «Ещё раз» → `restart()` |

Падение (`FallZoneComponent.car_fell`) и «застрял» (`StabilityComponent.stuck`): по `rules.fall_policy` — `car.reset_to(respawn последнего чекпоинта)` + штраф `respawn_penalty_s`, или выбывание (2.3). Неправильное направление — этап 2.x.
Сигналы `RaceDirector`: `player_car_spawned(car: Car)`, `countdown_ticked(n: int)`, `race_started`, `lap_completed(car: Car, lap: int, lap_s: float)`, `best_lap_set(car: Car, lap_s: float)`, `standings_changed`, `car_finished(car: Car, place: int, total_s: float)`, `race_finished(result: RaceResult)`.
Методы: `restart()` — v0.0.1 через `get_tree().reload_current_scene()` (≤ 1 с, проверка в S-09), `entries() -> Array[RaceEntry]`, `entry_of(car) -> RaceEntry`.

### 10.3 Остальные компоненты гонки
| Компонент (тип) | `@export` | Что делает | Сигналы / методы |
|---|---|---|---|
| `CarSpawnerComponent` (Node) | `car_scene: PackedScene` (`car.tscn`), `cars_root: Node3D`, `grid: StartGridComponent` | `spawn(spec, role, name, slot) -> Car`: `instantiate()` → `cars_root.add_child()` → `setup()` → `reset_to(slot)` | `car_spawned(car: Car)` — на него подписываются `Feedback` и `RaceDirector` |
| `ChaseCameraComponent` (Node, в `chase_camera.tscn`, корень `Camera3D`) | `camera: Camera3D`, `spec: ChaseCameraSpec`, `impulse: CameraImpulseComponent`, `director: RaceDirector` | в `_process` следует за `target.get_global_transform_interpolated()`: точка сзади по смеси «курс машины / вектор скорости», пружина с полураспадом из спеки, FOV по скорости + `impulse.fov_offset`, крен по рулю | `set_target(car: Car)`; цель берёт из `director.player_car_spawned` |
| `CameraImpulseComponent` (Node) | `camera: Camera3D`, `spec` | тряска «травмой» (смещение квадратом травмы через `h_offset`/`v_offset` и малый поворот), FOV-рывок | `add_trauma(amount: float)`, `kick_fov(deg: float)`, свойство `fov_offset` |
| `TimeScaleComponent` (Node, ALWAYS) | — | владеет `Engine.time_scale`; из всех запросов берёт минимальный; хит-стоп = 0,05, а не 0, чтобы физика не вставала; время восстановления считает по `Time.get_ticks_msec()` | `hit_stop(duration_s: float)`, `slow_motion(scale: float, duration_s: float)` |
| `FeedbackDirectorComponent` (Node) | `wall_hit`, `ram_dealt`, `ram_taken`, `takedown`, … `: FeedbackSpec`; ссылки на пулы, камеру, время, линии скорости | по событиям машин (подписка через `car_spawned`) включает каналы из `FeedbackSpec`; уважает `Settings.reduce_flashes` и `camera_only_if_player` | — |
| `VfxPoolComponent` (Node3D) | `scene: PackedScene`, `size: int` | в `_ready` заранее создаёт `size` экземпляров; дальше кольцевой буфер, без `queue_free` | `spawn(xform: Transform3D, strength: float)` |
| `OneShotEffect` (фасад сцены эффекта, Node3D) | `particles: Array[CPUParticles3D]`, `animation: AnimationPlayer`, `sound: AudioStreamPlayer3D` | перезапускает частицы, анимацию `play`, звук; масштаб по силе | `play(strength: float)` |
| `SpeedLinesComponent` (ColorRect) | — | параметры шейдера `speed_lines`: альфа по скорости игрока (от 180 км/ч) + всплески | `burst(alpha: float, duration_s: float)`, `set_speed_ratio(r: float)` |

### 10.4 Как событие становится «соком» (пример: таран, этап 2.3)
`ImpactSensorComponent.hit_car` (у обеих машин) → `RamResolverComponent` (в `Race`, 2.3) за один такт сводит пару в одно событие и решает, кто атаковал (у кого больше скорость вдоль нормали) → `EventBus.car_rammed(attacker, victim, strength, point)` + локальный сигнал → `FeedbackDirectorComponent` берёт `ram_dealt` или `ram_taken`: вспышка из пула в точке, `time_scale.hit_stop()`, `impulse.add_trauma()`, `kick_fov()`, `speed_lines.burst()`, `Settings.vibrate()`, звук. В v0.0.1 работает та же цепочка для удара о борт (`hit_wall` → `wall_hit`: только искры, тряска и звук, без вспышки — STYLE_GUIDE §6).

## 11. UI
### 11.1 Правила
- Каждый экран — сцена `scenes/ui/*.tscn`: корень `CanvasLayer`, под ним `Control` со скриптом-компонентом экрана. Тема одна: `ui/theme/main_theme.tres` (шрифты, StyleBoxFlat со `skew` для плашек-параллелограммов — STYLE_GUIDE §7).
- Тексты — только ключи: `Label.text = "HUD_LAP"` (автоперевод включён), с числами — `tr("HUD_LAP_FMT").format({"lap": 2, "laps": 3})`. Ключи — ВЕРХНИЙ_РЕГИСТР с префиксом экрана: `HUD_`, `FINISH_`, `PAUSE_`, `MENU_`, `GARAGE_`, `CAR_`, `TRACK_`, `TUTORIAL_`, `COMMON_`.
- Экран не трогает игровые объекты напрямую: подписывается на сигналы `RaceDirector` или `EventBus`, а действия отдаёт наверх сигналами (`restart_requested`, `resume_requested`), которые соединены в `race.tscn`.
- Кнопки — `Button` + `ButtonJuiceComponent` (Node): нажатие 0,92 → 1,0 за 0,12 с, звук клика (STYLE_GUIDE §9).
- Размеры: тач-цели ≥ 120 px при базе 1280 × 720, ключевые кнопки 150 px, безопасные поля 48 px, текст ≥ 22 px (STYLE_GUIDE §7.3).

### 11.2 Экраны v0.0.1
| Сцена | Компонент | `@export` | Что показывает | Сигналы наверх |
|---|---|---|---|---|
| `hud.tscn` | `RaceHudComponent` (Control) | `director`, метки | спидометр, круг, место, время, отсчёт | — |
| `finish_screen.tscn` | `FinishScreenComponent` (Control) | `director`, таблица, кнопки | место, время, лучший круг, таблица мест (строки — экземпляры `widgets/results_row.tscn`) | `restart_requested`, `next_requested` (позже) |
| `touch_controls.tscn` | `TouchSteerComponent` (Control) + `TouchActionButtonComponent` ×N | — | зона руля, кнопки способностей/тормоза/паузы | — (пишет в `Input`) |
| `pause_menu.tscn` | `PauseMenuComponent` (Control, ALWAYS) | — | продолжить, заново, звук | `resume_requested`, `restart_requested` |

### 11.3 Тач-управление
Тач не знает о машине. `TouchSteerComponent` переводит касания в действия ввода: смещение пальца по горизонтали от точки касания → `Input.action_press(&"steer_left"/&"steer_right", сила)`. Мёртвая зона 12 px, полный руль при 120 px (× `steer_sensitivity`); отпустил — `action_release`. Мультитач — по `index` события. Кнопки — `Input.action_press(&"ability_attack")` и т. п. Так `PlayerInput` читает одно и то же с клавиатуры и с экрана.
Ориентация: v0.0.1 — альбомная. Портретный режим для управления одной рукой — вопрос этапа 3.5 (см. §19).

## 12. Эффекты, звук, шейдеры
- Постоянные эффекты машины живут в `car.tscn` (`Vfx`), разовые — в пулах гонки (`VfxPools`). Погода — сцена из `TrackCondition.weather_vfx`, экземпляр которой ставится в `Track/Decor` при сборке трассы (не в рантайме).
- Частицы — только `CPUParticles3D`/`CPUParticles2D` (GPU-частицы в Compatibility на вебе — риск; проверка в S-05).
- Шейдеры (`res://shaders/`, шапка с источником и лицензией, правило 4): `cel_lit` (машины и мир: 2–3 ступени света, тень `shadow_tint`, кант на машинах), `cel_emissive` (окна, фонари), `sky_sunset` (небо, 5 цветовых ступеней), `road` (асфальт, разметка по UV), `glow_billboard` (ореолы, аддитивные спрайты), `impact_flash` (звезда удара), `speed_lines` (canvas_item), `smoke_cutoff` (дым с порогом альфы), `trail` (шлейф), `blob_shadow`.
- Звук: каждый `AudioStreamPlayer*` — на своей шине (§3). Разовые звуки удара — `AudioStreamRandomizer` (pitch ±8 %). Музыка — `AudioStreamPlayer` в `RaceAudio`. Высота тона мотора на вебе — спайк S-07.

## 13. Правила спауна (белый список)
`instantiate()` + `add_child()` разрешены **только** здесь:
| Где | Что | Когда |
|---|---|---|
| `CarSpawnerComponent` | `car.tscn` | старт заезда |
| `CarVisualComponent.load_model()` | `CarSpec.visual_scene` | `Car.setup()` |
| `VfxPoolComponent` | сцена эффекта | `_ready`, заранее |
| `FinishScreenComponent` и другие списки UI | строки-виджеты `widgets/*.tscn` | открытие экрана |
| `ProjectilePoolComponent` (3.1) | снаряды | `_ready`, заранее |
| `SceneRouter` (5.2) | экраны и трассы | переходы |
`queue_free()` — только для строк UI и при смене сцены. Во время заезда объекты не удаляются и не создаются (пулы), иначе на телефоне будут рывки.
Валидатор (§17) ищет `instantiate(` и `add_child(` вне этих файлов и любые `.new()` у классов-узлов.

## 14. Соглашения об именах
| Что | Правило | Пример |
|---|---|---|
| файлы и папки | `snake_case` | `engine_component.gd`, `track_01.tscn` |
| классы | `PascalCase`; компоненты с суффиксом `Component`; исключения — фасады (`Car`, `CarModel`, `Track`, `OneShotEffect`), источники управления (`PlayerInput`, `BotInput`, `GhostPlayback`), `RaceDirector`, данные (`…Spec`, `RaceEntry`, `RaceResult`) | `class_name GripComponent` |
| узлы в сценах | `PascalCase`, по роли, без суффикса | `Grip`, `WheelFL`, `CP03`, `Slot1` |
| сигналы | прошедшее время, `snake_case` | `drift_ended`, `car_finished` |
| методы | глагол; запросы `is_`/`has_`/`get_` | `switch_to()`, `is_airborne` |
| приватное | префикс `_` | `_prev_compression` |
| константы и члены enum | `UPPER_SNAKE` | `MAX_CARS`, `State.RACING` |
| идентификаторы, действия, причины | `StringName` | `&"car_01"`, `&"throttle"`, `&"focus"` |
| единицы в полях | суффикс, если не СИ | `top_speed_kmh`, `steer_max_deg`, `air_time_s`, `speed_mps` |
| ресурсы | `<вид>_<номер>.tres` или по смыслу | `car_01.tres`, `sunset.tres`, `ram_dealt.tres` |
| ключи текста | `ЭКРАН_СМЫСЛ` | `FINISH_RACE_AGAIN` |
| комментарии | русский, коротко; идентификаторы — английский | — |
Порядок в скрипте: `class_name` → `extends` → `##`-описание → сигналы → enum → константы → `@export` → публичные поля → приватные поля → `_ready` → `_physics_process`/`_process` → публичные методы → приватные методы.

## 15. Шаблон компонента
```gdscript
class_name EngineComponent extends Node
## Тяга, тормоз, задний ход и сопротивление. Числа — из CarSpec.

signal gear_changed(gear: int)

@export var controls: CarControlsComponent
@export var car: Car
@export var wheels: Array[WheelComponent] = []

var speed_mps: float = 0.0
var gear: int = 1

var _spec: CarSpec

func _ready() -> void:
	process_physics_priority = 0
	assert(controls != null and car != null and wheels.size() == 4, "EngineComponent: не назначены ссылки в сцене")

func configure(spec: CarSpec) -> void:
	_spec = spec

func _physics_process(delta: float) -> void:
	if _spec == null:
		return
	speed_mps = -car.global_basis.z.dot(car.linear_velocity)
	# … тяга по ведущим колёсам, тормоз, сопротивление (см. §8.3)
```
`assert` на ссылки — в каждом компоненте: забытая ссылка в `.tscn` должна падать сразу и с понятным текстом.

## 16. Рецепты
### 16.1 Собрать новую машину
1. MeshForge (`tools/meshforge/`): кузов `assets/models/cars/car_XX/car_XX.glb` по чек-листу STYLE_GUIDE §11 (силуэт, ≤ 4 000 треугольников, LOD1 ≈ 1 500, 1 атлас + 1 эмиссия); колёса — общий `wheel_a.glb` или свой.
2. `scenes/car/models/car_XX_model.tscn` по дереву §8.5. Пивоты колёс — x = ±0,78, z = −1,35 / +1,30, y = 0,09. Маркеры огней и задних контактов — по модели.
3. `data/cars/car_XX.tres` (`CarSpec`): скопировать `car_01.tres`, поменять `id`, ключи имени, `visual_scene`, `trail_color`, `engine_loop`. Физику менять только в пределах «куда крутить» из §6.1.
4. Ключи `CAR_XX_NAME`, `CAR_XX_TAGLINE` в `strings.csv` со статусом `draft` → через TEXT_PIPELINE → `humanized`.
5. `car.tscn` **не трогаем**: она общая для всех машин.
6. Проверка: `python3 tools/validate.py`; у пользователя — `scenes/dev/dev_car_flat.tscn` с новым `CarSpec` (чек-лист в логе).

### 16.2 Собрать новую трассу
1. Нарисовать осевую: точки `Curve3D` (замкнутая, шаг 20–60 м, плавные ручки), наклон на виражах ≤ 12°; офлайн-скрипт `tools/track_layout.py` проверяет радиусы (≥ 25 м на 120 км/ч) и считает длину.
2. Скопировать `track_01.tscn` как шаблон дерева §9.1, заменить кривую в `Centerline`.
3. Чекпоинты: CP00 на линии старта, далее каждые 80–150 м и вокруг возможных срезок; у каждого — `Respawn` на оси, смотрит по ходу. Массив `Track.checkpoints` — строго по порядку.
4. Решётка: 8 слотов за CP00 (схема §9.1). Зона падения — под всей трассой.
5. `TrackLightingComponent.condition` — нужное условие из `data/conditions/`.
6. Декор — модули из `scenes/tracks/modules/` по трансформам из `tools/track_layout.py`; фонари — `MultiMeshInstance3D`. Бюджет — STYLE_GUIDE §4 и S-02.
7. `data/tracks/track_XX.tres` (`TrackSpec`), ключ имени в CSV.
8. Проверка: валидатор (чекпоинты, слои, длина); у пользователя — `scenes/dev/dev_track_drive.tscn`: проехать круг, засчитывается ли круг, работает ли возврат после падения, FPS.

### 16.3 Добавить компонент
1. Одна ответственность; название — что он делает, а не что он такое.
2. Скрипт в `components/<домен>/`, шаблон §15, приоритет физики — по таблице §8.4.
3. Узел в сцене, все `@export` назначены в `.tscn`, `assert` на ссылки.
4. Если он меняет поведение машины — числа в `CarSpec` (или новом `…Spec`), не в константах.
5. Строка в таблицу §8.3 / §9.2 / §10.3 этого документа — в том же чекпоинте.

### 16.4 Добавить глобальное событие
Только если слушатель в другой сцене или автозагрузке. Сигнал с типами в `EventBus` + строка в таблицу §5.1. Внутри одной сцены — локальный сигнал компонента.

## 17. Что проверяет `tools/validate.py` (этап 1.1)
1. Нет `.new()` у классов-узлов (по списку классов Godot + наших `class_name` от узлов); нет `SurfaceTool`, `ArrayMesh`, `ImmediateMesh` в `components/`, `scenes/`, `autoload/`.
2. `instantiate(` и `add_child(` — только в файлах из белого списка §13.
3. Нет `get_node("`, `$"…/`, `get_parent()` и цепочек `../` в коде (ссылки — только `@export`).
4. Каждый `.gd` в `components/`: есть `class_name`, `extends` — тип движка (не наш класс); `untyped_declaration` — ни одного нетипизированного объявления (простой разбор `var`/`func`).
5. Каждый `.tscn`: все `ext_resource` существуют; все `NodePath` в `@export`-свойствах ведут к существующим узлам; у `RigidBody3D`, `Area3D`, `RayCast3D` слои и маски совпадают с §4.
6. `strings.csv`: заголовок `keys,ru,en,_status`; ключи уникальны; все ключи из `.tscn`/`.gd` (строки вида `[A-Z0-9_]{3,}` в `text`, `tr()`) есть в CSV; в релизной сборке нет строк со статусом `draft`.
7. Шейдеры: в шапке есть `Источник`, `Автор`, `Лицензия`; лицензия из списка CC0/MIT/своя; каждая заимствованная — в `CREDITS.md`.
8. `project.godot`: renderer Compatibility, Jolt, `untyped_declaration = 2`, все действия ввода — `physical_keycode`, автозагрузки в порядке §3.
9. Трассы: `Track.checkpoints` по индексам 0…n без пропусков, CP00 существует, 8 слотов решётки, есть зона падения.
10. Размер экспорта (после сборки у пользователя) — предупреждение при > 60 МБ, ошибка при > 100 МБ.

**Реализация (1.1, 2026-10-25):** `tools/validate.py` — разбор текста без Godot. Режимы: без ключей — проверка проекта; `--release` — строки `draft` становятся ошибкой; `--build-dir DIR` — п. 10; `--selftest` — каждое правило проверяется на своём плохом примере, плюс настоящий проект должен быть чистым. Уточнения: `scenes/dev/` не проверяется на ключи текстов (п. 6) и на слои тел/зон (п. 5, кроме `RayCast3D`) — это сцены для разработчика, в релиз не идут; переменная цикла без типа — предупреждение; белый список спауна — константа `SPAWN_WHITELIST` в начале файла (менять вместе с §13). Чекпоинт запускает валидатор, но не блокирует сохранение: ошибки печатаются, их исправляют до закрытия подэтапа.

## 18. Будущие компоненты (черновые контракты, уточняются на своих этапах)
| Этап | Компонент | Где | Суть |
|---|---|---|---|
| 2.1 | `BotInput`, `BotProfile` | машина, данные | линия гонки, ошибки, агрессия; правила «резинки» — на этапе 2.1 |
| 2.3 | `ArmorComponent` | машина | сегменты брони, `damaged(segments_left)`, `destroyed(by)` |
| 2.3 | `RamResolverComponent` | гонка | пара контактов → одно событие тарана |
| 2.4 | `StyleScoreComponent` | гонка | очки стиля за дрифт, близкий проезд, таран, полёт |
| 3.1 | `AbilitySpec`, `AbilitySlotComponent`, `ProjectilePoolComponent` | данные, машина, гонка | атака/защита, перезарядка, пул снарядов |
| 4.1 | `GhostRecorderComponent` | машина | запись трансформов 10 Гц + `controls` + нажатия способностей |
| 4.2 | `GhostPlayback` | машина | §8.3; передача «призрак → бот» |
| 5.1 | `SaveService` | автозагрузка | гостевой прогресс, облако |
| 5.2 | `SceneRouter` | автозагрузка | экраны и загрузка |
| 5.3 | `BossSpec`, `LeagueSpec` | данные | лиги и боссы |

## 19. Открытые вопросы → спайки 0.6
Полный список с порогами и запасными вариантами — `docs/SPIKES.md` (S-01…S-18). Здесь — только то, что влияет на архитектуру.
| № | Вопрос | Где решается |
|---|---|---|
| S-01 | global uniforms шейдеров работают в Compatibility на вебе? | спайк, иначе uniform в материалах |
| S-02 | бюджет кадра трассы (draw calls, треугольники) на телефоне | спайк |
| S-03 | Jolt + RigidBody3D + 4 луча при 60 Гц физики и 30 FPS отрисовки в однопоточной веб-сборке | спайк, иначе 30 Гц физики |
| S-04 | контакты тела из `_physics_process` через `PhysicsServer3D.body_get_direct_state()` с Jolt | спайк, иначе `body_entered` + скачок скорости |
| S-05 | `CPUParticles3D` в нужном количестве на телефоне | спайк |
| S-06 | стоп-сигналы: instance uniform в Compatibility или замена материала | спайк |
| S-07 | высота тона мотора (`pitch_scale`) в веб-режиме воспроизведения | спайк, иначе 3 петли с перекрёстным затуханием |
| S-08 | рукописные `.tscn` (массивы `NodePath`, без `uid`) открываются и пересохраняются редактором без потерь | спайк на 1.1 |
| S-09 | `reload_current_scene()` для «Ещё раз» ≤ 1 с | спайк |
| S-10 | CSG-трасса: время построения при загрузке на телефоне; запасной путь — «Bake Mesh Instance / Bake Collision Shape» в редакторе | спайк |
| S-11 | вибрация `Input.vibrate_handheld` в мобильном браузере | спайк |
| — | ориентация на телефоне: альбом (v0.0.1) или ещё и портрет для одной руки | решение пользователя до 3.5 |
| — | где живут `docs/` после перехода на GitHub: в репозитории с `.gdignore` (предложение) | решение на 1.1 |
