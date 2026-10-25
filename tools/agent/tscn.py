"""Мини-сборщик .tscn для генераторов агента (tools/agent/gen_*.py). Формат Godot 4 (format=3).
Transform3D пишется построчно: строки базиса r0, r1, r2, затем origin — так же, как пишет редактор.

С 2026-10-25 (S-08) Scene.write() пишет сцену В ФОРМАТЕ РЕДАКТОРА Godot 4.7 — побайтно как «Сохранить сцену»
(сверено с 7 сценами, пересохранёнными пользователем, коммит da1ab5b). Правила — docs/ARCHITECTURE.md §3:
  - шапка `[gd_scene format=3 uid="…"]`: uid сцены берётся из уже лежащего файла (его назначил редактор),
    у новой сцены — godot_uid(хеш пути);
  - ext_resource: `type uid path id`, uid — из `<путь>.uid` / `.import` / шапки `.tscn`; блок без пустых строк,
    порядок — по id в «естественной» сортировке;
  - sub_resource — в порядке первого использования, зависимости раньше (обход узлов сверху вниз, свойства по порядку);
    ресурс, на который никто не ссылается, редактор выкинет → здесь это ошибка;
  - узел: `name type parent unique_id node_paths instance`; unique_id — из лежащего файла по пути узла,
    новому узлу — детерминированный (хеш пути), чтобы повторная генерация давала тот же файл;
  - ShaderMaterial: пространственный шейдер → `render_priority` первым; дальше ВСЕ uniform шейдера в порядке
    объявления (не заданные — значением по умолчанию из шейдера), sampler без значения не пишется;
  - числа в Vector*/Color/Transform*/Packed*Array — кратчайшая запись float32 (`3`, `44.016644`); скалярный float
    пишет генератор сам и всегда с точкой (`4.0`); свойства, равные умолчанию движка, генератор не пишет."""
import decimal
import hashlib
import math
import os
import re
import struct


def num(x: float) -> str:
    if abs(x) < 5e-7:
        return "0"
    s = ("%.6f" % x).rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


def fnum(x: float) -> str:
    """Скалярное свойство-float так, как его пишет редактор: всегда с точкой (`4.0`, `0.25`)."""
    s = num(x)
    return s if "." in s else s + ".0"


def color(hex_or_rgb, a: float = 1.0) -> str:
    if isinstance(hex_or_rgb, str):
        h = hex_or_rgb.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    else:
        r, g, b = hex_or_rgb
    return f"Color({num(r)}, {num(g)}, {num(b)}, {num(a)})"


def v3(x, y, z) -> str:
    return f"Vector3({num(x)}, {num(y)}, {num(z)})"


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, 0, s], [0, 1, 0], [-s, 0, c]]


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return [[1, 0, 0], [0, c, -s], [0, s, c]]


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0], [s, c, 0], [0, 0, 1]]


def matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def scale(m, sx, sy, sz):
    """m · diag(sx, sy, sz): масштаб по локальным осям."""
    return [[m[i][0] * sx, m[i][1] * sy, m[i][2] * sz] for i in range(3)]


IDENT = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]


def xform(basis=IDENT, origin=(0, 0, 0)) -> str:
    vals = [basis[r][c] for r in range(3) for c in range(3)] + list(origin)
    return "Transform3D(" + ", ".join(num(v) for v in vals) + ")"


def mm_row(basis, origin):
    """12 чисел экземпляра MultiMesh (TRANSFORM_3D): r0 + ox, r1 + oy, r2 + oz."""
    return [basis[0][0], basis[0][1], basis[0][2], origin[0],
            basis[1][0], basis[1][1], basis[1][2], origin[1],
            basis[2][0], basis[2][1], basis[2][2], origin[2]]


def f32(tok: str) -> str:
    """Кратчайшая запись числа, которая читается обратно в тот же float32 (так пишет редактор): `800`, `44.016644`,
    `0.106`, `-0.5`. Без экспоненты (в сценах проекта она не встречалась; понадобится — сверить с редактором)."""
    if not re.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", tok):
        return tok
    x = struct.unpack("f", struct.pack("f", float(tok)))[0]
    if x == 0:
        return "0"  # «-0» в сценах редактора не встречается; num() тоже пишет 0
    with decimal.localcontext() as ctx:  # ничья округляется вверх по модулю, как у редактора:
        ctx.rounding = decimal.ROUND_HALF_UP  # 143.703125 → 143.70313, 22.8203125 → 22.820313 (Python дал бы …12)
        d = decimal.Decimal(x)
        for prec in range(1, 10):
            t = format(d, ".%de" % (prec - 1))
            if struct.unpack("f", struct.pack("f", float(t)))[0] == x:
                break
    t = format(decimal.Decimal(t), "f")  # 8.00e+02 → 800, 4.4016644e+01 → 44.016644 (2026-10-25: было 800 → 8)
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t


F32_TYPES = ("Vector2", "Vector3", "Vector4", "Color", "Quaternion", "Plane", "Rect2", "AABB", "Basis",
             "Transform2D", "Transform3D", "Projection", "PackedFloat32Array", "PackedVector2Array",
             "PackedVector3Array", "PackedVector4Array", "PackedColorArray")
F32_RE = re.compile(r"\b(" + "|".join(F32_TYPES) + r")\(([^()]*)\)")


def f32_value(v: str) -> str:
    return F32_RE.sub(lambda m: m.group(1) + "(" + ", ".join(f32(t.strip()) for t in m.group(2).split(",")) + ")"
                      if m.group(2).strip() else m.group(0), v)


def natural_key(s: str):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", s)]


def res_uid(res_path: str) -> str | None:
    """uid ресурса так, как его знает редактор: <файл>.uid, [remap] в .import или шапка .tscn/.tres."""
    f = res_path.replace("res://", "", 1)
    if os.path.isfile(f + ".uid"):
        return open(f + ".uid", encoding="utf-8").read().strip() or None
    if os.path.isfile(f + ".import"):
        m = re.search(r'^uid="(uid://[^"]+)"', open(f + ".import", encoding="utf-8").read(), re.M)
        return m.group(1) if m else None
    if f.endswith((".tscn", ".tres")) and os.path.isfile(f):
        m = re.match(r'\[gd_\w+ [^\]]*uid="(uid://[^"]+)"', open(f, encoding="utf-8").readline())
        return m.group(1) if m else None
    return None


# Умолчания движка, которые редактор при сохранении выкидывает (сверено со сценами da1ab5b, Godot 4.7.2).
# Генератор может их задавать для наглядности — в файл они не попадут. Новое свойство с умолчанием → дописать сюда.
DEFAULTS = {
    "Sky": {"process_mode": "0", "radiance_size": "3"},
    "Environment": {"tonemap_mode": "0", "glow_enabled": "false", "glow_bloom": "0.0", "background_mode": "0"},
    "QuadMesh": {"size": "Vector2(1, 1)"},
    "Gradient": {"offsets": "PackedFloat32Array(0, 1)"},
    "CPUParticles3D": {"local_coords": "false", "angle_min": "0.0", "initial_velocity_min": "0.0",
                       "initial_velocity_max": "0.0", "emitting": "true", "one_shot": "false", "explosiveness": "0.0"},
}


# Control, чей родитель не Control (например, CanvasLayer), по умолчанию layout_mode = 3 — редактор это не пишет.
# У корня сцены layout_mode = 3 остаётся (сверено: spike_audio, spike_hud — корень пишет, SpeedBlur/SpeedLines — нет).
CONTROL_TYPES = {"Control", "ColorRect", "Label", "Button", "TextureRect", "Panel", "PanelContainer", "CenterContainer",
                 "VBoxContainer", "HBoxContainer", "MarginContainer", "GridContainer", "HSlider", "VSlider",
                 "ProgressBar", "TextureProgressBar", "RichTextLabel", "CheckBox", "CheckButton", "OptionButton"}


def _norm(v: str) -> str:
    v = f32_value(v.strip())
    try:
        return repr(float(v))
    except ValueError:
        return v


def drop_defaults(rtype: str | None, props: list) -> list:
    d = DEFAULTS.get(rtype or "", {})
    return [(k, v) for k, v in props if k not in d or _norm(v) != _norm(d[k])]


SHADER_TYPE_RE = re.compile(r"^\s*shader_type\s+(\w+)", re.M)
UNIFORM_RE = re.compile(r"^\s*uniform\s+(\w+)\s+(\w+)\s*(?::\s*([^=;]*))?(?:=\s*([^;]+))?;", re.M)


def _glsl_args(expr: str, n: int) -> list:
    m = re.fullmatch(r"\s*\w+\s*\(([^()]*)\)\s*", expr)
    args = [a.strip() for a in m.group(1).split(",")] if m else [expr.strip()]
    return args * n if len(args) == 1 else args


def shader_uniforms(res_path: str) -> tuple:
    """(тип шейдера, [(имя, значение по умолчанию в записи редактора или None)]) в порядке объявления."""
    src = re.sub(r"//[^\n]*", "", open(res_path.replace("res://", "", 1), encoding="utf-8").read())
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    kind = SHADER_TYPE_RE.search(src).group(1)
    out = []
    for gtype, name, hints, default in UNIFORM_RE.findall(src):
        color = "source_color" in (hints or "")
        d = default.strip() if default else None
        if gtype.startswith(("sampler", "isampler", "usampler")):
            val = None
        elif gtype == "float":
            val = repr(float(d.rstrip("f"))) if d else "0.0"
        elif gtype in ("int", "uint"):
            val = str(int(d)) if d else "0"
        elif gtype == "bool":
            val = d if d else "false"
        elif gtype in ("vec2", "vec3", "vec4"):
            n = int(gtype[-1])
            args = [f32(a.rstrip("f")) for a in _glsl_args(d, n)] if d else ["0"] * n
            if color:
                val = "Color(" + ", ".join((args + ["1"])[:4]) + ")"
            else:
                val = f"Vector{n}(" + ", ".join(args) + ")"
        else:
            raise ValueError(f"{res_path}: uniform {gtype} {name} — тип не поддержан в tscn.py")
        out.append((name, val))
    return kind, out


def godot_uid(seed: str) -> str:
    """UID в записи Godot (ResourceUID::id_to_text): 63-битное число в base34, цифры a…y и 0…8.
    Редактор берёт случайное число; мы — хеш от seed, чтобы повторная генерация давала тот же файл."""
    n = int.from_bytes(hashlib.sha1(seed.encode()).digest()[:8], "big") & 0x7FFFFFFFFFFFFFFF
    out = ""
    while True:
        c = n % 34
        out = (chr(97 + c) if c < 25 else chr(48 + c - 25)) + out
        n //= 34
        if not n:
            return "uid://" + out


def stable_unique_id(scene_path: str, node_path: str, taken: set) -> int:
    h = int.from_bytes(hashlib.sha1(f"{scene_path}:{node_path}".encode()).digest()[:4], "big") & 0x7FFFFFFF
    while h == 0 or h in taken:
        h = (h * 1103515245 + 12345) & 0x7FFFFFFF
    return h


def existing_ids(path: str) -> tuple:
    """(uid сцены, {путь узла: unique_id}) из уже лежащего файла — их назначил редактор."""
    if not os.path.isfile(path):
        return None, {}
    t = open(path, encoding="utf-8").read()
    m = re.match(r'\[gd_scene [^\]]*uid="(uid://[^"]+)"', t)
    ids = {}
    for h in re.findall(r"^\[node [^\n]*\]$", t, re.M):
        name = re.search(r'name="([^"]+)"', h).group(1)
        par = re.search(r'parent="([^"]*)"', h)
        uid = re.search(r"unique_id=(\d+)", h)
        if uid:
            ids[node_path(name, par.group(1) if par else None)] = int(uid.group(1))
    return (m.group(1) if m else None), ids


def node_path(name: str, parent: str | None) -> str:
    if parent is None:
        return "."
    return name if parent == "." else f"{parent}/{name}"


class Scene:
    """Сцена собирается как данные; текст в формате редактора — в text(path)."""

    def __init__(self):
        self.ext, self.sub, self.nodes = [], [], []  # ext: (type, path, id); sub: (type, id, [(k, v)]); nodes: dict

    def ext_res(self, rtype: str, path: str, rid: str) -> str:
        self.ext.append((rtype, path, rid))
        return f'ExtResource("{rid}")'

    def sub_res(self, rtype: str, rid: str, props: list) -> str:
        self.sub.append((rtype, rid, [(k, str(v)) for k, v in props]))
        return f'SubResource("{rid}")'

    def node(self, name: str, ntype: str | None = None, parent: str | None = None,
             instance: str | None = None, node_paths: list | None = None, props: list | None = None):
        self.nodes.append({"name": name, "type": ntype, "parent": parent, "instance": instance,
                           "node_paths": node_paths or [], "props": [(k, str(v)) for k, v in (props or [])]})

    def add_props(self, name: str, props: list):
        """Дописать свойства узлу, уже добавленному в сцену (корню — когда известны пути детей)."""
        n = next(n for n in self.nodes if n["name"] == name)
        n["props"] += [(k, str(v)) for k, v in props]

    # ---- формат редактора
    def _shader_params(self, props: list) -> list:
        ext = {rid: path for _t, path, rid in self.ext}
        sh = dict(props).get("shader", "")
        m = re.fullmatch(r'ExtResource\("([^"]+)"\)', sh)
        if not m:
            return props
        kind, uniforms = shader_uniforms(ext[m.group(1)])
        given = {k[len("shader_parameter/"):]: v for k, v in props if k.startswith("shader_parameter/")}
        known = {n for n, _ in uniforms}
        stray = sorted(set(given) - known)
        assert not stray, f"параметров нет в шейдере {ext[m.group(1)]}: {stray}"
        head = [(k, v) for k, v in props if not k.startswith("shader_parameter/") and k not in ("render_priority", "shader")]
        out = []
        if kind == "spatial":
            out.append(("render_priority", dict(props).get("render_priority", "0")))
        out += head + [("shader", sh)]
        for n, default in uniforms:
            v = given.get(n, default)
            if v is not None:
                out.append((f"shader_parameter/{n}", v))
        return out

    def text(self, path: str | None = None) -> str:
        scene_uid, old_ids = existing_ids(path) if path else (None, {})
        if path and not scene_uid:  # новая сцена: uid сразу, иначе редактор допишет его при первом сохранении
            scene_uid = godot_uid("res://" + path)
        subs = {rid: (t, props) for t, rid, props in self.sub}
        order, seen = [], set()

        def visit_value(v: str):
            for rid in re.findall(r'SubResource\("([^"]+)"\)', v):
                if rid not in seen:
                    seen.add(rid)
                    for _k, vv in subs[rid][1]:
                        visit_value(vv)
                    order.append(rid)

        for n in self.nodes:
            for _k, v in n["props"]:
                visit_value(v)
        orphan = [rid for _t, rid, _p in self.sub if rid not in seen]
        assert not orphan, f"sub_resource без ссылок (редактор их выкинет): {orphan}"
        head = "[gd_scene format=3" + (f' uid="{scene_uid}"' if scene_uid else "") + "]"
        ext_lines = []
        for t, p, rid in sorted(self.ext, key=lambda e: natural_key(e[2])):
            uid = res_uid(p)
            ext_lines.append(f'[ext_resource type="{t}"' + (f' uid="{uid}"' if uid else "") + f' path="{p}" id="{rid}"]')
        parts = [head]
        if ext_lines:
            parts.append("\n".join(ext_lines))
        for rid in order:
            t, props = subs[rid]
            if t == "ShaderMaterial":
                props = self._shader_params(props)
            props = drop_defaults(t, props)
            body = "\n".join(f"{k} = {f32_value(v)}" for k, v in props)
            parts.append(f'[sub_resource type="{t}" id="{rid}"]' + ("\n" + body if body else ""))
        taken = set(old_ids.values())
        types = {node_path(n["name"], n["parent"]): n["type"] for n in self.nodes}
        for n in self.nodes:
            np_ = node_path(n["name"], n["parent"])
            uid = old_ids.get(np_)
            if uid is None:
                uid = stable_unique_id(path or "", np_, taken)
                taken.add(uid)
            h = f'[node name="{n["name"]}"'
            if n["type"]:
                h += f' type="{n["type"]}"'
            if n["parent"] is not None:
                h += f' parent="{n["parent"]}"'
            h += f" unique_id={uid}"
            if n["node_paths"]:
                h += " node_paths=PackedStringArray(" + ", ".join(f'"{x}"' for x in n["node_paths"]) + ")"
            if n["instance"]:
                h += f" instance={n['instance']}"
            h += "]"
            props = drop_defaults(n["type"], n["props"])
            ptype = types.get(n["parent"] or "", "?")
            if n["parent"] is not None and ptype is not None and ptype not in CONTROL_TYPES:
                props = [(k, v) for k, v in props if not (k == "layout_mode" and v.strip() == "3")]
            body = "\n".join(f"{k} = {f32_value(v)}" for k, v in props)
            parts.append(h + ("\n" + body if body else ""))
        return "\n\n".join(parts) + "\n"

    def write(self, path: str):
        ids = [rid for _t, _p, rid in self.ext] + [rid for _t, rid, _p in self.sub]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        assert not dup, f"повтор id ресурсов: {dup}"
        paths = [node_path(n["name"], n["parent"]) for n in self.nodes]
        dupn = sorted({p for p in paths if paths.count(p) > 1})
        assert not dupn, f"повтор путей узлов: {dupn}"
        t = self.text(path)
        uids = re.findall(r"unique_id=(\d+)", t)
        assert len(uids) == len(set(uids)), "повтор unique_id"
        old = open(path, encoding="utf-8").read() if os.path.isfile(path) else None
        open(path, "w", encoding="utf-8").write(t)
        print("written", path, len(t) // 1024, "KB", "(без изменений)" if old == t else "(изменён)" if old else "(новый)")


def shader_mat(scene: Scene, rid: str, shader_ref: str, params: dict, render_priority: int | None = None) -> str:
    props = []
    if render_priority is not None:
        props.append(("render_priority", str(render_priority)))
    props.append(("shader", shader_ref))
    props += [(f"shader_parameter/{k}", v) for k, v in params.items()]
    return scene.sub_res("ShaderMaterial", rid, props)
