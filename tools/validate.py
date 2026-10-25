#!/usr/bin/env python3
"""Валидатор правил проекта «Турбовендетта» (docs/ARCHITECTURE.md §17, AGENTS.md «Жёсткие правила»).

usage:
  python3 tools/validate.py                 # проверка проекта (корень = родитель tools/)
  python3 tools/validate.py --release       # + строки со статусом draft = ошибка
  python3 tools/validate.py --build-dir DIR # + размер веб-сборки (п. 10)
  python3 tools/validate.py --selftest      # проверка самого валидатора на плохих примерах

Код выхода: 0 — ошибок нет (предупреждения допустимы), 1 — есть ошибки.
Godot у агента нет, поэтому проверки — разбором текста. Если правило ложно срабатывает —
чинить валидатор (и записать в PROGRESS), а не обходить правило в коде.
"""
from __future__ import annotations

import csv
import os
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------- настройки правил
# §13: где разрешены instantiate( и add_child( (имена файлов .gd)
SPAWN_WHITELIST = {
    "car_spawner_component.gd",       # машины в слоты решётки
    "car_visual_component.gd",        # модель из CarSpec.visual_scene
    "vfx_pool_component.gd",          # пул эффектов, заранее
    "finish_screen_component.gd",     # строки таблицы итогов
    "projectile_pool_component.gd",   # 3.1
    "scene_router.gd",                # 5.2
}
# папки, где лежит игровой код и сцены (tools/ и docs/ не проверяются: у них .gdignore)
CODE_DIRS = ("autoload", "components", "scenes", "data", "ui", "platform")
NO_PROCEDURAL_DIRS = ("components", "scenes", "autoload")
PROCEDURAL_CLASSES = ("SurfaceTool", "ArrayMesh", "ImmediateMesh", "MeshDataTool")
# §4: слои = битовые значения
LAYER = {"world": 1, "cars": 2, "triggers": 4, "fall": 8, "projectiles": 16}
EXPECT_PHYS = {
    "RigidBody3D": [(LAYER["cars"], LAYER["world"] | LAYER["cars"] | LAYER["projectiles"])],
    "Area3D": [(LAYER["triggers"], LAYER["cars"]), (LAYER["fall"], LAYER["cars"])],
    "RayCast3D": [(None, LAYER["world"])],   # у луча важна только маска
}
DEFAULT_LAYER, DEFAULT_MASK = 1, 1
AUTOLOAD_ORDER = ["EventBus", "Settings", "YandexSDK", "PauseService"]
ALLOWED_LICENSES = ("CC0", "MIT", "СВОЯ", "OWN")
TEXT_KEY_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,}$")
SIZE_WARN_MB, SIZE_ERR_MB = 60, 100

# Классы-узлы Godot 4.x (их .new() запрещён). Неизвестный класс с .new() — предупреждение.
NODE_CLASSES = set("""
Node Node2D Node3D CanvasItem CanvasLayer Control Viewport SubViewport Window Timer HTTPRequest
AnimationPlayer AnimationTree AnimationMixer Tween AudioStreamPlayer AudioStreamPlayer2D AudioStreamPlayer3D
AudioListener2D AudioListener3D Camera2D Camera3D MeshInstance3D MultiMeshInstance3D MeshInstance2D MultiMeshInstance2D
CSGShape3D CSGPrimitive3D CSGBox3D CSGCombiner3D CSGCylinder3D CSGMesh3D CSGPolygon3D CSGSphere3D CSGTorus3D
Path3D PathFollow3D Path2D PathFollow2D CollisionObject3D CollisionObject2D PhysicsBody3D PhysicsBody2D
RigidBody3D RigidBody2D StaticBody3D StaticBody2D CharacterBody3D CharacterBody2D AnimatableBody3D AnimatableBody2D
Area3D Area2D CollisionShape3D CollisionShape2D CollisionPolygon3D CollisionPolygon2D RayCast3D RayCast2D
ShapeCast3D ShapeCast2D VehicleBody3D VehicleWheel3D SoftBody3D SpringArm3D PhysicalBone3D Joint3D
Generic6DOFJoint3D HingeJoint3D PinJoint3D SliderJoint3D ConeTwistJoint3D GPUParticles3D CPUParticles3D
GPUParticles2D CPUParticles2D GPUParticlesAttractor3D GPUParticlesCollision3D Light3D DirectionalLight3D
OmniLight3D SpotLight3D WorldEnvironment Marker3D Marker2D Sprite2D Sprite3D SpriteBase3D AnimatedSprite2D
AnimatedSprite3D Label3D Decal FogVolume ReflectionProbe VoxelGI LightmapGI LightmapProbe GeometryInstance3D
VisualInstance3D VisibleOnScreenNotifier3D VisibleOnScreenEnabler3D VisibleOnScreenNotifier2D
VisibleOnScreenEnabler2D RemoteTransform3D RemoteTransform2D BoneAttachment3D Skeleton3D SkeletonModifier3D
NavigationAgent3D NavigationAgent2D NavigationRegion3D NavigationRegion2D NavigationLink3D NavigationObstacle3D
GridMap OccluderInstance3D ImporterMeshInstance3D XRCamera3D XROrigin3D XRNode3D XRController3D
Label RichTextLabel BaseButton Button TextureButton CheckBox CheckButton OptionButton MenuButton LinkButton
ColorPickerButton LineEdit TextEdit CodeEdit Range ProgressBar TextureProgressBar Slider HSlider VSlider
SpinBox ScrollBar HScrollBar VScrollBar Panel PanelContainer ColorRect TextureRect NinePatchRect
ReferenceRect Container BoxContainer HBoxContainer VBoxContainer GridContainer MarginContainer
CenterContainer AspectRatioContainer ScrollContainer SplitContainer HSplitContainer VSplitContainer
FlowContainer HFlowContainer VFlowContainer TabContainer TabBar ItemList Tree Popup PopupMenu PopupPanel
AcceptDialog ConfirmationDialog FileDialog SubViewportContainer VideoStreamPlayer GraphEdit GraphNode
MenuBar Separator HSeparator VSeparator ParallaxBackground ParallaxLayer Parallax2D TileMap TileMapLayer
Line2D Polygon2D Light2D PointLight2D DirectionalLight2D LightOccluder2D CanvasModulate BackBufferCopy
ResourcePreloader MultiplayerSpawner MultiplayerSynchronizer ShaderGlobalsOverride StatusIndicator
Bone2D Skeleton2D InstancePlaceholder MissingNode
""".split())

# ---------------------------------------------------------------- вспомогательное
@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def err(self, where: str, msg: str) -> None:
        self.errors.append(f"ОШИБКА  {where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"ВНИМАНИЕ {where}: {msg}")


def strip_comment(line: str) -> str:
    """Убирает комментарий # с учётом строк в кавычках."""
    out, quote, i = [], "", 0
    while i < len(line):
        c = line[i]
        if quote:
            out.append(c)
            if c == "\\" and i + 1 < len(line):
                out.append(line[i + 1]); i += 2; continue
            if c == quote:
                quote = ""
        elif c in "\"'":
            quote = c; out.append(c)
        elif c == "#":
            break
        else:
            out.append(c)
        i += 1
    return "".join(out)


def strip_strings(line: str) -> str:
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', '""', line)


def iter_files(root: Path, suffix: str) -> list[Path]:
    """Файлы с расширением suffix, кроме папок с .gdignore, .godot/ и build/."""
    res: list[Path] = []
    for d, dirs, files in os.walk(root):
        dp = Path(d)
        if (dp / ".gdignore").exists():
            dirs[:] = []
            continue
        dirs[:] = sorted(x for x in dirs if x not in (".godot", "build", ".git"))
        res += [dp / f for f in sorted(files) if f.endswith(suffix)]
    return res


def rel(root: Path, p: Path) -> str:
    return str(p.relative_to(root))


def res_to_path(root: Path, res: str) -> Path:
    return root / res.replace("res://", "", 1)

# ---------------------------------------------------------------- GDScript
CLASS_RE = re.compile(r"^\s*class_name\s+(\w+)(?:\s+extends\s+(\S+))?")
EXTENDS_RE = re.compile(r"^\s*extends\s+(\S+)")
VAR_RE = re.compile(r"^\s*(?:@\w+(?:\([^)]*\))?\s+)*(?:static\s+)?(var|const)\s+(\w+)\s*(.*)$")
FUNC_RE = re.compile(r"^\s*(?:static\s+)?func\s+(\w+)\s*\((.*)\)\s*(->\s*[\w\[\], .]+)?\s*:")


def gd_info(path: Path) -> tuple[str | None, str | None]:
    cls = ext = None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = strip_comment(line)
        m = CLASS_RE.match(line)
        if m:
            cls = m.group(1)
            if m.group(2):
                ext = m.group(2)
        m = EXTENDS_RE.match(line)
        if m:
            ext = m.group(1)
    return cls, ext


def split_params(s: str) -> list[str]:
    parts, depth, cur = [], 0, ""
    for c in s:
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        if c == "," and depth == 0:
            parts.append(cur); cur = ""
        else:
            cur += c
    if cur.strip():
        parts.append(cur)
    return [p.strip() for p in parts]


def check_gd(root: Path, rep: Report, classes: dict[str, str | None]) -> None:
    node_like = set(NODE_CLASSES)
    # наши классы, унаследованные от узлов, тоже узлы
    changed = True
    while changed:
        changed = False
        for c, e in classes.items():
            if c not in node_like and e in node_like:
                node_like.add(c); changed = True
    for path in iter_files(root, ".gd"):
        r = rel(root, path)
        top = r.split(os.sep)[0]
        if top not in CODE_DIRS:
            continue
        name = path.name
        lines = path.read_text(encoding="utf-8").splitlines()
        cls, ext = gd_info(path)
        # п. 4: наследование только от типа движка
        if ext is None:
            rep.err(r, "нет extends")
        elif ext.startswith('"') or ext in classes:
            rep.err(r, f"extends {ext}: наследоваться можно только от типа движка (AGENTS.md правило 1)")
        if top == "components" and cls is None:
            rep.err(r, "компонент без class_name")
        in_multiline_str = False
        for i, raw in enumerate(lines, 1):
            if raw.count('"""') % 2 == 1:
                in_multiline_str = not in_multiline_str
                continue
            if in_multiline_str:
                continue
            code = strip_comment(raw)
            bare = strip_strings(code)
            where = f"{r}:{i}"
            # п. 1: .new() у узлов, процедурная геометрия
            for m in re.finditer(r"\b(\w+)\s*\.\s*new\s*\(", bare):
                c = m.group(1)
                if c in node_like:
                    rep.err(where, f"{c}.new() — узлы кодом не создаются (правило 2)")
            if "ClassDB.instantiate" in bare:
                rep.err(where, "ClassDB.instantiate — создание объектов по имени запрещено")
            if top in NO_PROCEDURAL_DIRS:
                for c in PROCEDURAL_CLASSES:
                    if re.search(rf"\b{c}\b", bare):
                        rep.err(where, f"{c} — процедурная геометрия в игровом коде запрещена (правило 2)")
            # п. 2: спаун только в белом списке
            if name not in SPAWN_WHITELIST:
                for word in ("instantiate(", "add_child("):
                    if word in bare.replace(" (", "("):
                        rep.err(where, f"{word[:-1]} вне белого списка §13")
            # п. 3: связи только через @export
            if re.search(r"\bget_node(_or_null)?\s*\(", bare) or re.search(r"\bget_parent\s*\(", bare):
                rep.err(where, "get_node/get_parent — ссылки только через @export (правило 1)")
            if re.search(r"\$\"?[^\s\"]*\.\./", code) or re.search(r'\$"[^"]*/', code) or '"../' in code:
                rep.err(where, "путь к узлу строкой ($\"…/\", \"../\") — ссылки только через @export")
            # п. 4: типизация
            m = VAR_RE.match(code)
            if m and not re.match(r"^\s*for\b", code):
                rest = m.group(3).strip()
                if not (rest.startswith(":")):
                    rep.err(where, f"{m.group(1)} {m.group(2)} без типа (untyped_declaration)")
            m = FUNC_RE.match(code)
            if m:
                fname, params, ret = m.group(1), m.group(2), m.group(3)
                if ret is None:
                    rep.err(where, f"func {fname}() без типа результата (-> …)")
                for p in split_params(params):
                    pn = p.split("=")[0].strip()
                    if ":" not in pn:
                        rep.err(where, f"параметр «{pn}» в {fname}() без типа")
            for lm in re.finditer(r"\bfunc\s*\(([^)]*)\)", bare):
                for p in split_params(lm.group(1)):
                    if ":" not in p.split("=")[0]:
                        rep.err(where, f"параметр лямбды «{p}» без типа")
            for fm in re.finditer(r"^\s*for\s+(\w+)\s+in\b", bare):
                rep.warn(where, f"переменная цикла «{fm.group(1)}» без типа (пиши for x: T in …)")
            # тексты по ключам: tr("KEY")
            for tm in re.finditer(r'\btr\(\s*"([^"]+)"', code):
                KEY_USES.append((where, tm.group(1), r.startswith("scenes" + os.sep + "dev")))


KEY_USES: list[tuple[str, str, bool]] = []

# ---------------------------------------------------------------- сцены .tscn
HEADER_RE = re.compile(r"^\[(\w+)(.*)\]\s*$")
ATTR_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


def parse_attrs(s: str) -> dict[str, str]:
    return {k: v.strip('"') for k, v in ATTR_RE.findall(s)}


def check_tscn(root: Path, rep: Report) -> None:
    for path in iter_files(root, ".tscn"):
        r = rel(root, path)
        is_dev = r.startswith("scenes" + os.sep + "dev")
        ext_ids: set[str] = set()
        sub_ids: set[str] = set()
        nodes: dict[str, dict[str, str]] = {}   # путь узла → атрибуты + свойства
        instanced: set[str] = set()
        cur: str | None = None
        props_paths: list[tuple[str, str, str, int]] = []
        root_name: str | None = None
        lines = path.read_text(encoding="utf-8").splitlines()
        for i, line in enumerate(lines, 1):
            where = f"{r}:{i}"
            m = HEADER_RE.match(line)
            if m:
                kind, attrs = m.group(1), parse_attrs(m.group(2))
                cur = None
                if kind == "ext_resource":
                    rid = attrs.get("id", "")
                    if rid in ext_ids:
                        rep.err(where, f"повтор id ext_resource «{rid}»")
                    ext_ids.add(rid)
                    p = attrs.get("path", "")
                    if p and not res_to_path(root, p).exists():
                        rep.err(where, f"ext_resource не найден: {p}")
                elif kind == "sub_resource":
                    rid = attrs.get("id", "")
                    if rid in sub_ids:
                        rep.err(where, f"повтор id sub_resource «{rid}»")
                    sub_ids.add(rid)
                elif kind == "node":
                    name, parent = attrs.get("name", ""), attrs.get("parent")
                    if parent is None:
                        if root_name is not None:
                            rep.err(where, "второй корневой узел (без parent)")
                        root_name = name
                        npath = "."
                    else:
                        if parent != "." and parent not in nodes:
                            rep.err(where, f"родитель «{parent}» узла «{name}» не найден выше по файлу")
                        npath = name if parent == "." else f"{parent}/{name}"
                    if npath in nodes:
                        rep.err(where, f"два узла с одним путём «{npath}»")
                    nodes[npath] = dict(attrs)
                    nodes[npath]["__line"] = str(i)
                    if "instance" in m.group(2):
                        instanced.add(npath)
                    cur = npath
                continue
            if cur is not None and "=" in line:
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip()
                nodes[cur][k] = v
                for pm in re.finditer(r'NodePath\("([^"]*)"\)', v):
                    props_paths.append((cur, k, pm.group(1), i))
                if k == "text" and not is_dev:
                    t = v.strip('"')
                    if TEXT_KEY_RE.match(t):
                        KEY_USES.append((f"{r}:{i}", t, False))
                    elif t and re.search(r"[A-Za-zА-Яа-яЁё]{2,}", t):
                        rep.err(f"{r}:{i}", f"текст «{t[:30]}» не ключ — тексты только ключами strings.csv (правило 3)")
        # NodePath из свойств ведут к существующим узлам
        for owner, key, target, i in props_paths:
            if target == "":
                continue
            base = [] if owner == "." else owner.split("/")
            parts = base[:]
            ok = True
            for seg in target.split("/"):
                if seg == "..":
                    if not parts:
                        ok = False; break
                    parts.pop()
                elif seg not in (".", ""):
                    parts.append(seg)
            full = "/".join(parts) if parts else "."
            if not ok:
                rep.err(f"{r}:{i}", f"{key}: путь {target} выходит за корень сцены")
                continue
            if full not in nodes:
                inside_instance = any(full.startswith(x + "/") for x in instanced)
                (rep.warn if inside_instance else rep.err)(f"{r}:{i}", f"{key}: узел «{target}» (от «{owner}») не найден")
        # слои и маски §4
        for npath, a in nodes.items():
            t = a.get("type")
            if t not in EXPECT_PHYS or is_dev and t != "RayCast3D":
                continue
            layer = int(a.get("collision_layer", DEFAULT_LAYER))
            mask = int(a.get("collision_mask", DEFAULT_MASK))
            okk = any((el is None or el == layer) and em == mask for el, em in EXPECT_PHYS[t])
            if not okk:
                rep.err(f"{r}:{a['__line']}", f"{t} «{npath}»: слой {layer} / маска {mask} не по таблице §4")
        # п. 9: трассы
        if re.match(r"scenes/tracks/track_\d+/track_\d+\.tscn$", r.replace(os.sep, "/")):
            cps = sorted(int(n[-2:]) for n in (p.split("/")[-1] for p in nodes) if re.fullmatch(r"CP\d\d", n))
            if not cps or cps[0] != 0 or cps != list(range(len(cps))):
                rep.err(r, f"чекпоинты должны идти CP00…CPnn без пропусков, есть: {cps}")
            slots = [p for p in nodes if re.fullmatch(r"Slot[1-8]", p.split("/")[-1])]
            if len(slots) != 8:
                rep.err(r, f"слотов стартовой решётки {len(slots)}, нужно 8 (Slot1…Slot8)")
            if not any(p.split("/")[-1].startswith("FallZone") for p in nodes):
                rep.err(r, "нет зоны падения (узел FallZone…)")

# ---------------------------------------------------------------- strings.csv
def check_strings(root: Path, rep: Report, release: bool) -> None:
    p = root / "localization" / "strings.csv"
    if not p.exists():
        rep.err("localization/strings.csv", "файла нет")
        return
    with p.open(encoding="utf-8", newline="") as f:
        rows = list(csv.reader(f))
    if not rows or rows[0] != ["keys", "ru", "en", "_status"]:
        rep.err("strings.csv:1", f"заголовок должен быть keys,ru,en,_status (D-015), сейчас: {rows[0] if rows else '—'}")
        return
    keys: dict[str, str] = {}
    for n, row in enumerate(rows[1:], 2):
        if not row or not row[0].strip():
            continue
        if len(row) != 4:
            rep.err(f"strings.csv:{n}", f"в строке {len(row)} колонок, нужно 4")
            continue
        k, ru, en, st = row
        if k in keys:
            rep.err(f"strings.csv:{n}", f"повтор ключа {k}")
        keys[k] = st
        if not TEXT_KEY_RE.match(k):
            rep.err(f"strings.csv:{n}", f"ключ «{k}» не в формате ЭКРАН_СМЫСЛ")
        if st not in ("draft", "humanized"):
            rep.err(f"strings.csv:{n}", f"статус «{st}»: допустимы draft / humanized")
        if not ru.strip() or not en.strip():
            rep.err(f"strings.csv:{n}", f"у {k} пустой перевод")
        if st == "draft":
            (rep.err if release else rep.warn)(f"strings.csv:{n}", f"{k} ещё draft — в релиз нельзя")
    for where, k, is_dev in KEY_USES:
        if not is_dev and k not in keys:
            rep.err(where, f"ключа {k} нет в strings.csv")

# ---------------------------------------------------------------- шейдеры
def check_shaders(root: Path, rep: Report) -> None:
    credits = (root / "CREDITS.md").read_text(encoding="utf-8") if (root / "CREDITS.md").exists() else ""
    for p in iter_files(root, ".gdshader"):
        r = rel(root, p)
        head = "\n".join(p.read_text(encoding="utf-8").splitlines()[:15])
        fields = {}
        for name in ("Источник", "Автор", "Лицензия"):
            m = re.search(rf"{name}\s*:\s*(.+)", head)
            if not m:
                rep.err(r, f"в шапке нет поля «{name}:» (правило 4)")
            else:
                fields[name] = m.group(1).strip()
        lic = fields.get("Лицензия", "").upper()
        if lic and not any(lic.startswith(a) for a in ALLOWED_LICENSES):
            rep.err(r, f"лицензия «{fields['Лицензия']}» не из CC0 / MIT / своя")
        src = fields.get("Источник", "").lower()
        if src and not src.startswith(("свой", "своя", "own", "агент")) and p.name not in credits:
            rep.err(r, "заимствованный шейдер не указан в CREDITS.md")

# ---------------------------------------------------------------- project.godot
def check_project(root: Path, rep: Report) -> None:
    p = root / "project.godot"
    if not p.exists():
        rep.err("project.godot", "файла нет")
        return
    t = p.read_text(encoding="utf-8")
    need = {
        'renderer/rendering_method="gl_compatibility"': "рендерер должен быть Compatibility",
        'renderer/rendering_method.mobile="gl_compatibility"': "рендерер mobile должен быть Compatibility",
        '3d/physics_engine="Jolt Physics"': "физика должна быть Jolt (явно)",
        "gdscript/warnings/untyped_declaration=2": "untyped_declaration должен быть ошибкой (2)",
    }
    for k, msg in need.items():
        if k not in t:
            rep.err("project.godot", msg)
    sec = re.search(r"^\[input\]\s*$(.*?)(?=^\[|\Z)", t, re.S | re.M)
    if sec:
        for m in re.finditer(r"Object\(InputEventKey,(.*?)\)", sec.group(1), re.S):
            body = m.group(1)
            kc = re.search(r'"keycode":(\d+)', body)
            pk = re.search(r'"physical_keycode":(\d+)', body)
            if not pk or pk.group(1) == "0" or (kc and kc.group(1) != "0"):
                rep.err("project.godot [input]", "клавиша не по physical_keycode (правило 5)")
    al = re.search(r"^\[autoload\]\s*$(.*?)(?=^\[|\Z)", t, re.S | re.M)
    names = re.findall(r"^(\w+)=", al.group(1), re.M) if al else []
    if names[: len(AUTOLOAD_ORDER)] != AUTOLOAD_ORDER:
        rep.err("project.godot [autoload]", f"порядок {names}, нужен {AUTOLOAD_ORDER} (§3)")
    for n, path in re.findall(r'^(\w+)="\*?(res://[^"]+)"', al.group(1) if al else "", re.M):
        if not res_to_path(root, path).exists():
            rep.err("project.godot [autoload]", f"{n}: нет файла {path}")
    ms = re.search(r'run/main_scene="(res://[^"]+)"', t)
    if not ms or not res_to_path(root, ms.group(1)).exists():
        rep.err("project.godot", "главная сцена не найдена")

# ---------------------------------------------------------------- UID редактора (*.uid, *.import)
UID_RE = re.compile(r"^uid://[0-9a-z]+$")


def check_uids(root: Path, rep: Report) -> None:
    """S-08 (2026-10-25): редактор создаёт *.gd.uid / *.gdshader.uid и *.import с uid=.
    Их храним в git. Проверяем: формат, исходник на месте, UID не повторяется, uid= в сценах известен."""
    seen: dict[str, str] = {}

    def add(uid: str, where: str) -> None:
        if uid in seen:
            rep.err(where, f"UID {uid} повторяется (уже в {seen[uid]}) — удалить один файл .uid и переоткрыть проект")
        else:
            seen[uid] = where

    for f in iter_files(root, ".uid"):
        where = rel(root, f)
        uid = f.read_text(encoding="utf-8").strip()
        if not UID_RE.match(uid):
            rep.err(where, f"неверный формат UID «{uid[:40]}»")
            continue
        if not f.with_suffix("").exists():
            rep.warn(where, "исходника нет — .uid остался от удалённого файла, удалить вместе с ним")
        add(uid, where)
    for f in iter_files(root, ".import"):
        where = rel(root, f)
        t = f.read_text(encoding="utf-8")
        m = re.search(r'^uid="(uid://[0-9a-z]+)"', t, re.M)
        if m:
            add(m.group(1), where)
        src = re.search(r'^source_file="(res://[^"]+)"', t, re.M)
        if src and not res_to_path(root, src.group(1)).exists():
            rep.warn(where, f"исходника {src.group(1)} нет — удалить .import вместе с файлом")
    for f in iter_files(root, ".tscn") + iter_files(root, ".tres"):
        for m in re.finditer(r'^\[ext_resource [^\n]*?uid="(uid://[0-9a-z]+)"', f.read_text(encoding="utf-8"), re.M):
            if m.group(1) not in seen:
                rep.warn(rel(root, f), f"ext_resource {m.group(1)}: такого UID нет в *.uid / *.import — Godot возьмёт path=")

# ---------------------------------------------------------------- размер сборки
def check_build(build: Path, rep: Report) -> None:
    total = sum(f.stat().st_size for f in build.rglob("*") if f.is_file())
    mb = total / 1024 / 1024
    msg = f"размер сборки {mb:.1f} МБ"
    if mb > SIZE_ERR_MB:
        rep.err(str(build), msg + f" > {SIZE_ERR_MB} МБ (лимит Яндекс Игр)")
    elif mb > SIZE_WARN_MB:
        rep.warn(str(build), msg + f" > {SIZE_WARN_MB} МБ (бюджет PLAN)")
    else:
        print(f"OK {msg}")

# ---------------------------------------------------------------- запуск
def validate(root: Path, release: bool = False, build: Path | None = None) -> Report:
    KEY_USES.clear()
    rep = Report()
    classes: dict[str, str | None] = {}
    for path in iter_files(root, ".gd"):
        c, e = gd_info(path)
        if c:
            classes[c] = e
    check_project(root, rep)
    check_gd(root, rep, classes)
    check_tscn(root, rep)
    check_strings(root, rep, release)
    check_shaders(root, rep)
    check_uids(root, rep)
    if build:
        check_build(build, rep)
    return rep


def selftest() -> int:
    """Каждое правило должно сработать на своём плохом примере."""
    good_root = Path(__file__).resolve().parent.parent
    cases = {
        "components/bad_new.gd": ("class_name BadNewComponent extends Node\nfunc _ready() -> void:\n\tvar m: MeshInstance3D = MeshInstance3D.new()\n", "MeshInstance3D.new()"),
        "components/bad_spawn.gd": ("class_name BadSpawnComponent extends Node\n@export var s: PackedScene\nfunc _ready() -> void:\n\tadd_child(s.instantiate())\n", "вне белого списка"),
        "components/bad_path.gd": ('class_name BadPathComponent extends Node\nfunc _ready() -> void:\n\tvar n: Node = get_node("../X")\n', "get_node/get_parent"),
        "components/bad_type.gd": ("class_name BadTypeComponent extends Node\nvar speed = 1.0\nfunc go(a) -> void:\n\tpass\nfunc f():\n\tpass\n", "без типа"),
        "components/bad_ext.gd": ("class_name BadExtComponent extends BadNewComponent\n", "наследоваться можно только"),
        "components/bad_mesh.gd": ("class_name BadMeshComponent extends Node\nfunc _ready() -> void:\n\tvar st: SurfaceTool = SurfaceTool.new()\n", "SurfaceTool"),
        "scenes/bad.tscn": ('[gd_scene format=3]\n\n[ext_resource type="Script" path="res://nope.gd" id="1"]\n\n[node name="Car" type="RigidBody3D"]\nengine = NodePath("Engine")\n\n[node name="L" type="Label" parent="Missing"]\ntext = "Привет, мир"\n', "ext_resource не найден"),
        "scenes/dup_a.gd.uid": ("uid://dupdupdup0\n", "повторяется"),
        "scenes/dup_b.gd.uid": ("uid://dupdupdup0\n", "исходника нет"),
        "shaders/bad.gdshader": ("// Источник: https://www.shadertoy.com/view/xxx\n// Автор: кто-то\n// Лицензия: CC BY-NC-SA 3.0\nshader_type spatial;\n", "лицензия"),
    }
    expect_extra = ["не найден выше", "«Engine»", "не ключ", "слой 1 / маска 1", "CREDITS", "func f() без типа", "параметр «a»"]
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for item in ("project.godot", "localization", "autoload", "scenes", "assets", "icon.svg", "CREDITS.md"):
            src = good_root / item
            if src.is_dir():
                import shutil; shutil.copytree(src, tmp / item)
            elif src.exists():
                (tmp / item).write_bytes(src.read_bytes())
        for f, (body, _) in cases.items():
            (tmp / f).parent.mkdir(parents=True, exist_ok=True)
            (tmp / f).write_text(body, encoding="utf-8")
        rep = validate(tmp)
        text = "\n".join(rep.errors + rep.warnings)
        fails = [needle for _, (_, needle) in cases.items() if needle not in text]
        fails += [n for n in expect_extra if n not in text]
    clean = validate(good_root)
    if clean.errors:
        fails.append("на настоящем проекте есть ошибки:\n  " + "\n  ".join(clean.errors))
    if fails:
        print("SELFTEST FAIL, не сработали:", *fails, sep="\n  ")
        print("--- вывод валидатора на плохих примерах ---\n" + text)
        return 1
    print(f"selftest ok: {len(cases) + len(expect_extra)} правил ловят нарушения, настоящий проект чистый")
    return 0


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        return selftest()
    root = Path(__file__).resolve().parent.parent
    build = Path(args[args.index("--build-dir") + 1]) if "--build-dir" in args else None
    rep = validate(root, release="--release" in args, build=build)
    for line in rep.warnings + rep.errors:
        print(line)
    print(f"validate: ошибок {len(rep.errors)}, предупреждений {len(rep.warnings)}")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
