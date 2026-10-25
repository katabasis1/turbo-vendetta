#!/usr/bin/env python3
"""Генератор project.godot (агент пишет вручную, Godot у агента нет — S-08).
Источник чисел: docs/ARCHITECTURE.md §3–§4, цвета — docs/STYLE_GUIDE.md §2 (условие «Закат»).
usage: python3 tools/agent/gen_project_godot.py > project.godot

Формат = как пишет редактор Godot 4.7.2 (S-08, сверено 2026-10-25 по копии из GitHub после импорта у пользователя):
стандартная шапка; события ввода разделены "\n, Object("; значения по умолчанию редактор выкидывает —
locale/fallback="en", common/physics_ticks_per_second=60, anti_aliasing/quality/msaa_3d=0 здесь не пишем
(они равны умолчаниям движка, ARCHITECTURE §3 — какие значения мы на них рассчитываем); порядок ключей в [physics] — как у редактора.
Проверка: вывод генератора побайтно равен project.godot в репозитории (tools/agent/checkpoint.sh это сверяет)."""

def col(h, a=1.0):
    h = h.lstrip('#'); r, g, b = (int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    return f"Color({r:.4g}, {g:.4g}, {b:.4g}, {a:g})"

KEY = dict(W=87, S=83, A=65, D=68, Q=81, E=69, P=80, R=82, SPACE=32,
           UP=4194320, DOWN=4194322, LEFT=4194319, RIGHT=4194321, SHIFT=4194325, ESCAPE=4194305)

def key_event(code, location=0):
    return ('Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,'
            '"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,'
            f'"keycode":0,"physical_keycode":{code},"key_label":0,"unicode":0,"location":{location},"echo":false,"script":null)')

# действие → [(клавиша, location)]; location 1 = левая (Shift левый, §3)
ACTIONS = [
    ("throttle", [("W", 0), ("UP", 0)]),
    ("brake", [("S", 0), ("DOWN", 0)]),
    ("steer_left", [("A", 0), ("LEFT", 0)]),
    ("steer_right", [("D", 0), ("RIGHT", 0)]),
    ("drift", [("SHIFT", 1), ("SPACE", 0)]),
    ("ability_attack", [("Q", 0)]),
    ("ability_defense", [("E", 0)]),
    ("pause", [("ESCAPE", 0), ("P", 0)]),
    ("restart", [("R", 0)]),
]

GLOBALS = [  # имя, тип, значение — ARCHITECTURE §3, STYLE_GUIDE §2 «Закат»
    ("sun_dir", "vec3", "Vector3(-0.35, 0.25, -0.9)"),
    ("sun_color", "color", col("#FFF1D6")),
    ("shadow_tint", "color", col("#402A69")),
    ("rim_color", "color", col("#F3A0A8")),
    ("horizon_color", "color", col("#F6B26B")),
    ("fog_color", "color", col("#EB7B93")),
    ("fog_start", "float", "60.0"),
    ("fog_end", "float", "400.0"),
]

out = []
w = out.append
w("; Engine configuration file.\n; It's best edited using the editor UI and not directly,\n; since the parameters that go here are not all obvious.\n;\n; Format:\n;   [section] ; section goes between []\n;   param=value ; assign values to parameters\n")
w("config_version=5\n")
w("[application]\n")
w('config/name="Turbo Vendetta: Knockout Racing"')
w('config/name_localized={\n"en": "Turbo Vendetta: Knockout Racing",\n"ru": "Турбовендетта: гонки на выбывание"\n}')
w('config/version="0.0.0"')
w('run/main_scene="res://scenes/boot/boot.tscn"')
w('config/features=PackedStringArray("4.7", "GL Compatibility")')
w('config/icon="res://icon.svg"\n')
w("[audio]\n")
w('buses/default_bus_layout="res://assets/audio/bus_layout.tres"\n')
w("[autoload]\n")
for n, f in [("EventBus", "event_bus"), ("Settings", "settings"), ("YandexSDK", "yandex_sdk"), ("PauseService", "pause_service")]:
    w(f'{n}="*res://autoload/{f}.gd"')
w("")
w("[debug]\n")
w("gdscript/warnings/untyped_declaration=2")
for k in ("unsafe_property_access", "unsafe_method_access", "unsafe_cast", "unsafe_call_argument"):
    w(f"gdscript/warnings/{k}=1")
w("")
w("[display]\n")
w("window/size/viewport_width=1280\nwindow/size/viewport_height=720")
w('window/stretch/mode="canvas_items"\nwindow/stretch/aspect="expand"\n')
w("[input]\n")
for name, keys in ACTIONS:
    evs = "\n, ".join(key_event(KEY[k], loc) for k, loc in keys)
    w(f'{name}={{\n"deadzone": 0.2,\n"events": [{evs}\n]\n}}')
w("")
w("[input_devices]\n")
w("pointing/emulate_touch_from_mouse=true\n")
w("[internationalization]\n")
w('locale/translations=PackedStringArray("res://localization/strings.ru.translation", "res://localization/strings.en.translation")')
w("")  # locale/fallback="en" — умолчание, редактор его не пишет
w("[layer_names]\n")
for i, n in enumerate(["world", "cars", "triggers", "fall", "projectiles"], 1):
    w(f'3d_physics/layer_{i}="{n}"')
w("")
w("[physics]\n")
# physics_ticks_per_second=60 — умолчание, редактор его не пишет; порядок ключей — как у редактора
w("common/max_physics_steps_per_frame=4")
w('3d/physics_engine="Jolt Physics"')
w("common/physics_interpolation=true\n")
w("[rendering]\n")
w('renderer/rendering_method="gl_compatibility"\nrenderer/rendering_method.mobile="gl_compatibility"')
w("textures/vram_compression/import_etc2_astc=true")
w("")  # anti_aliasing/quality/msaa_3d=0 — умолчание, редактор его не пишет
w("[shader_globals]\n")
for n, t, v in GLOBALS:
    w(f'{n}={{\n"type": "{t}",\n"value": {v}\n}}')
print("\n".join(out))
