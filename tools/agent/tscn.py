"""Мини-сборщик .tscn для генераторов агента (tools/agent/gen_*.py). Формат Godot 4 (format=3).
Transform3D пишется построчно: строки базиса r0, r1, r2, затем origin — так же, как пишет редактор."""
import math


def num(x: float) -> str:
    if abs(x) < 5e-7:
        return "0"
    s = ("%.6f" % x).rstrip("0").rstrip(".")
    return s if s not in ("-0", "") else "0"


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


class Scene:
    def __init__(self):
        self.ext, self.sub, self.nodes = [], [], []

    def ext_res(self, rtype: str, path: str, rid: str) -> str:
        self.ext.append(f'[ext_resource type="{rtype}" path="{path}" id="{rid}"]')
        return f'ExtResource("{rid}")'

    def sub_res(self, rtype: str, rid: str, props: list) -> str:
        body = "\n".join(f"{k} = {v}" for k, v in props)
        self.sub.append(f'[sub_resource type="{rtype}" id="{rid}"]\n{body}'.rstrip())
        return f'SubResource("{rid}")'

    def node(self, name: str, ntype: str | None = None, parent: str | None = None,
             instance: str | None = None, node_paths: list | None = None, props: list | None = None):
        head = f'[node name="{name}"'
        if ntype:
            head += f' type="{ntype}"'
        if parent is not None:
            head += f' parent="{parent}"'
        if node_paths:
            head += " node_paths=PackedStringArray(" + ", ".join(f'"{p}"' for p in node_paths) + ")"
        if instance:
            head += f" instance={instance}"
        head += "]"
        body = "\n".join(f"{k} = {v}" for k, v in (props or []))
        self.nodes.append((head + "\n" + body).rstrip())

    def text(self) -> str:
        parts = ["[gd_scene format=3]"] + self.ext + self.sub + self.nodes
        return "\n\n".join(parts) + "\n"

    def write(self, path: str):
        import re
        ids = re.findall(r'^\[(?:ext|sub)_resource [^\]]*id="([^"]+)"', self.text(), re.M)
        dup = sorted({i for i in ids if ids.count(i) > 1})
        assert not dup, f"повтор id ресурсов: {dup}"
        open(path, "w", encoding="utf-8").write(self.text())
        print("written", path, len(self.text()) // 1024, "KB")


def shader_mat(scene: Scene, rid: str, shader_ref: str, params: dict, render_priority: int | None = None) -> str:
    props = []
    if render_priority is not None:
        props.append(("render_priority", str(render_priority)))
    props.append(("shader", shader_ref))
    props += [(f"shader_parameter/{k}", v) for k, v in params.items()]
    return scene.sub_res("ShaderMaterial", rid, props)
