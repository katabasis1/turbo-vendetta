#!/usr/bin/env python3
"""Генератор сцен пакета спайков 1.1 (docs/SPIKES.md §4): болванка машины, spike_render, spike_vfx, spike_audio.
Сцены — обычные .tscn из узлов; генератор только раскладывает декор (буферы MultiMesh) и 8 машин.
Запуск из корня проекта: python3 tools/agent/gen_spike_scenes.py [car|render|vfx|audio|all]"""
import math
import random
import sys

sys.path.insert(0, "tools/agent")
from tscn import (Scene, IDENT, color, matmul, mm_row, num, rot_x, rot_y, rot_z, scale, shader_mat, v3, xform)

SP = "res://scenes/dev/spikes"
SH = "res://shaders"


# ---------------------------------------------------------------- болванка машины
def box_tris(w, h, d):
    return 2 * 2 * ((w + 1) * (h + 1) + (h + 1) * (d + 1) + (w + 1) * (d + 1))


def gen_car():
    s = Scene()
    script = s.ext_res("Script", f"{SP}/props/dummy_car.gd", "1_car")
    cel = s.ext_res("Shader", f"{SH}/cel_lit.gdshader", "2_cel")
    emi = s.ext_res("Shader", f"{SH}/cel_emissive.gdshader", "3_emi")
    glow = s.ext_res("Shader", f"{SH}/glow_billboard.gdshader", "4_glow")
    blob = s.ext_res("Shader", f"{SH}/blob_shadow.gdshader", "5_blob")
    # перламутр (STYLE_GUIDE §2.3): свет / полутон / тень, кант и блик — только машины
    m_body = shader_mat(s, "ShaderMaterial_body", cel, {
        "tone_light": color("#FAF2F4"), "tone_mid": color("#E5BFD0"), "tone_shadow": color("#9E6396"),
        "rim_strength": "0.35", "spec_strength": "0.6"})
    m_glass = shader_mat(s, "ShaderMaterial_glass", cel, {
        "tone_light": color("#6A4C9C"), "tone_mid": color("#46286E"), "tone_shadow": color("#24163F"),
        "rim_strength": "0.2", "spec_strength": "0.9", "spec_threshold": "0.9"})
    m_tire = shader_mat(s, "ShaderMaterial_tire", cel, {
        "tone_light": color("#4A2E66"), "tone_mid": color("#2E1D47"), "tone_shadow": color("#1B1030")})
    m_brake = shader_mat(s, "ShaderMaterial_brake", emi, {
        "color_on": color("#FF4F6E"), "color_off": color("#5C1F33"), "energy": "1.0"})
    m_glow = shader_mat(s, "ShaderMaterial_brakeglow", glow, {
        "glow_color": color("#FF4F6E"), "intensity": "0.9", "core": "0.15"})
    m_blob = shader_mat(s, "ShaderMaterial_blob", blob, {})
    bw, bh, bd = 12, 4, 28
    mesh_body = s.sub_res("BoxMesh", "BoxMesh_body", [("material", m_body), ("size", v3(1.8, 0.55, 4.4)),
                          ("subdivide_width", bw), ("subdivide_height", bh), ("subdivide_depth", bd)])
    mesh_cabin = s.sub_res("BoxMesh", "BoxMesh_cabin", [("material", m_glass), ("size", v3(1.5, 0.45, 2.0))])
    mesh_wheel = s.sub_res("CylinderMesh", "CylinderMesh_wheel", [("material", m_tire), ("top_radius", "0.33"),
                           ("bottom_radius", "0.33"), ("height", "0.26"), ("radial_segments", "20"), ("rings", "0")])
    mesh_brake = s.sub_res("BoxMesh", "BoxMesh_brake", [("material", m_brake), ("size", v3(1.5, 0.12, 0.06))])
    mesh_glow = s.sub_res("QuadMesh", "QuadMesh_brakeglow", [("material", m_glow), ("size", "Vector2(2.6, 0.9)")])
    mesh_blob = s.sub_res("PlaneMesh", "PlaneMesh_blob", [("material", m_blob), ("size", "Vector2(2.6, 5.2)")])
    s.node("DummyCar", "Node3D", node_paths=["brake_light", "brake_glow"], props=[
        ("script", script), ("brake_light", 'NodePath("BrakeLight")'), ("brake_glow", 'NodePath("BrakeGlow")')])
    s.node("Body", "MeshInstance3D", ".", props=[("transform", xform(origin=(0, 0.6, 0))), ("mesh", mesh_body)])
    s.node("Cabin", "MeshInstance3D", ".", props=[("transform", xform(origin=(0, 1.1, 0.25))), ("mesh", mesh_cabin)])
    wheel_basis = rot_z(math.pi / 2)
    for name, x, z in (("WheelFL", -0.86, -1.4), ("WheelFR", 0.86, -1.4), ("WheelRL", -0.86, 1.4), ("WheelRR", 0.86, 1.4)):
        s.node(name, "MeshInstance3D", ".", props=[("transform", xform(wheel_basis, (x, 0.33, z))), ("mesh", mesh_wheel)])
    s.node("BrakeLight", "MeshInstance3D", ".", props=[("transform", xform(origin=(0, 0.78, 2.21))), ("mesh", mesh_brake)])
    s.node("BrakeGlow", "MeshInstance3D", ".", props=[("transform", xform(origin=(0, 0.78, 2.4))), ("visible", "false"),
           ("cast_shadow", "0"), ("mesh", mesh_glow)])
    s.node("BlobShadow", "MeshInstance3D", ".", props=[("transform", xform(origin=(0, 0.03, 0))), ("cast_shadow", "0"),
           ("mesh", mesh_blob)])
    s.write("scenes/dev/spikes/props/dummy_car.tscn")
    tris = box_tris(bw, bh, bd) + 12 + 4 * (20 * 2 + 20 * 2) + 12 + 2 + 2
    print(f"  болванка: ≈ {tris} треугольников, 9 мешей")


# ---------------------------------------------------------------- общий мир (для render и vfx)
def add_environment(s: Scene, sky_mat: str, glow_threshold: str = "0.9"):
    sky = s.sub_res("Sky", "Sky_sunset", [("sky_material", sky_mat), ("process_mode", "0"), ("radiance_size", "0")])
    env = s.sub_res("Environment", "Environment_spike", [
        ("background_mode", "2"), ("background_color", color("#F6B26B")), ("sky", sky),
        ("ambient_light_source", "1"), ("reflected_light_source", "1"), ("tonemap_mode", "0"),
        ("glow_enabled", "false"), ("glow_intensity", "0.8"), ("glow_bloom", "0.0"),
        ("glow_hdr_threshold", glow_threshold)])
    return env


def ring_instances(n, radius, y, phase=0.0, yaw_tangent=True, sx=1.0, sy=1.0, sz=1.0):
    rows = []
    for i in range(n):
        a = phase + 2 * math.pi * i / n
        x, z = radius * math.sin(a), radius * math.cos(a)
        basis = rot_y(a + (math.pi / 2 if yaw_tangent else 0.0)) if yaw_tangent else IDENT
        rows.append(mm_row(scale(basis, sx, sy, sz), (x, y, z)))
    return rows


def multimesh(s: Scene, rid: str, mesh_ref: str, rows: list, visible: int | None = None) -> str:
    buf = ", ".join(num(v) for r in rows for v in r)
    props = [("transform_format", "1"), ("instance_count", str(len(rows)))]
    if visible is not None:
        props.append(("visible_instance_count", str(visible)))
    props += [("mesh", mesh_ref), ("buffer", f"PackedFloat32Array({buf})")]
    return s.sub_res("MultiMesh", rid, props)


def city_rows(rng, n, r_min, r_max):
    """Дома лицом к центру + окна на фасаде. Возвращает (дома, окна)."""
    houses, windows = [], []
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(r_min, r_max)
        w, h, d = rng.uniform(10, 24), rng.uniform(14, 70), rng.uniform(10, 22)
        x, z = r * math.sin(a), r * math.cos(a)
        yaw = math.atan2(-x, -z)  # +Z дома смотрит в центр
        b = rot_y(yaw)
        houses.append(mm_row(scale(b, w, h, d), (x, h / 2, z)))
        for _k in range(12):
            lx = rng.uniform(-w / 2 + 1.2, w / 2 - 1.2)
            ly = rng.uniform(3.0, h - 2.0)
            ox = x + b[0][0] * lx + b[0][2] * (d / 2 + 0.06)
            oz = z + b[2][0] * lx + b[2][2] * (d / 2 + 0.06)
            windows.append(mm_row(b, (ox, ly, oz)))
    return houses, windows


def add_world(s: Scene, rng, parent: str, cel: str, emi: str, glow: str, double: bool):
    """Асфальт, разметка, эстакада на опорах, фонари с ореолами, город с окнами.
    double=True: в каждом MultiMesh второй комплект (видна половина, клавиша удваивает)."""
    m_asphalt = shader_mat(s, "ShaderMaterial_asphalt", cel, {
        "tone_light": color("#6A3F7C"), "tone_mid": color("#4A2E66"), "tone_shadow": color("#2E1D47")})
    m_mark = shader_mat(s, "ShaderMaterial_mark", cel, {
        "tone_light": color("#EEC2E4"), "tone_mid": color("#C9A3D8"), "tone_shadow": color("#8F6FB0")})
    m_concrete = shader_mat(s, "ShaderMaterial_concrete", cel, {
        "tone_light": color("#A390C0"), "tone_mid": color("#715194"), "tone_shadow": color("#402A69")})
    m_city = shader_mat(s, "ShaderMaterial_city", cel, {
        "tone_light": color("#5A3A80"), "tone_mid": color("#3A2260"), "tone_shadow": color("#24163F")})
    m_windows = shader_mat(s, "ShaderMaterial_windows", emi, {
        "color_on": color("#FFC870"), "color_off": color("#3A2260"), "energy": "1.0", "fog_amount": "0.45"})
    m_lamp = shader_mat(s, "ShaderMaterial_lampglow", glow, {"glow_color": color("#FFC870"), "intensity": "0.7"})
    mesh_ground = s.sub_res("PlaneMesh", "PlaneMesh_ground", [("material", m_asphalt), ("size", "Vector2(800, 800)")])
    mesh_dash = s.sub_res("BoxMesh", "BoxMesh_dash", [("material", m_mark), ("size", v3(0.25, 0.02, 3.0))])
    mesh_pillar = s.sub_res("BoxMesh", "BoxMesh_pillar", [("material", m_concrete), ("size", v3(2.0, 8.0, 2.0))])
    mesh_deck = s.sub_res("BoxMesh", "BoxMesh_deck", [("material", m_concrete), ("size", v3(10.0, 1.2, 14.0))])
    mesh_pole = s.sub_res("CylinderMesh", "CylinderMesh_pole", [("material", m_concrete), ("top_radius", "0.12"),
                          ("bottom_radius", "0.16"), ("height", "7.0"), ("radial_segments", "8"), ("rings", "0")])
    mesh_lamp = s.sub_res("QuadMesh", "QuadMesh_lampglow", [("material", m_lamp), ("size", "Vector2(3.0, 3.0)")])
    mesh_house = s.sub_res("BoxMesh", "BoxMesh_house", [("material", m_city)])
    mesh_window = s.sub_res("QuadMesh", "QuadMesh_window", [("material", m_windows), ("size", "Vector2(1.6, 1.0)")])

    k = 2 if double else 1
    sets = {}
    # разметка: 2 кольца по 60 штрихов (второй комплект — кольца 34 и 50 м)
    rows = ring_instances(60, 14, 0.01) + ring_instances(60, 26, 0.01)
    if double:
        rows += ring_instances(60, 34, 0.01, phase=0.03) + ring_instances(60, 50, 0.01, phase=0.03)
    sets["Dashes"] = (mesh_dash, rows)
    # эстакада: 30 опор и пролётов на 45 м (второй комплект — 70 м)
    pil = ring_instances(30, 45, 4.0, yaw_tangent=False)
    deck = ring_instances(30, 45, 8.6)
    if double:
        pil += ring_instances(30, 70, 4.0, phase=0.05, yaw_tangent=False)
        deck += ring_instances(30, 70, 8.6, phase=0.05)
    sets["Pillars"] = (mesh_pillar, pil)
    sets["Decks"] = (mesh_deck, deck)
    # фонари: 40 на 34 м (второй комплект — 60 м)
    pole = ring_instances(40, 34, 3.5, yaw_tangent=False)
    lamp = ring_instances(40, 34, 7.2, yaw_tangent=False)
    if double:
        pole += ring_instances(40, 60, 3.5, phase=0.04, yaw_tangent=False)
        lamp += ring_instances(40, 60, 7.2, phase=0.04, yaw_tangent=False)
    sets["Poles"] = (mesh_pole, pole)
    sets["LampGlows"] = (mesh_lamp, lamp)
    # город: 120 домов × 12 окон (второй комплект — ещё 120)
    houses, windows = city_rows(rng, 120, 110, 260)
    if double:
        h2, w2 = city_rows(rng, 120, 110, 280)
        houses += h2
        windows += w2
    sets["Houses"] = (mesh_house, houses)
    sets["Windows"] = (mesh_window, windows)

    s.node("Ground", "MeshInstance3D", parent, props=[("cast_shadow", "0"), ("mesh", mesh_ground)])
    names = []
    for name, (mesh, rows) in sets.items():
        mm = multimesh(s, f"MultiMesh_{name.lower()}", mesh, rows, visible=len(rows) // k if double else None)
        s.node(name, "MultiMeshInstance3D", parent, props=[("cast_shadow", "0"), ("multimesh", mm)])
        names.append(name)
    return names, m_windows


def sky_material(s: Scene):
    sky_sh = s.ext_res("Shader", f"{SH}/sky_sunset.gdshader", "9_sky")
    return shader_mat(s, "ShaderMaterial_sky", sky_sh, {})


# ---------------------------------------------------------------- spike_render
def gen_render():
    rng = random.Random(11)
    s = Scene()
    script = s.ext_res("Script", f"{SP}/spike_render.gd", "1_render")
    hud = s.ext_res("PackedScene", f"{SP}/spike_hud.tscn", "2_hud")
    car = s.ext_res("PackedScene", f"{SP}/props/dummy_car.tscn", "3_car")
    cel = s.ext_res("Shader", f"{SH}/cel_lit.gdshader", "4_cel")
    emi = s.ext_res("Shader", f"{SH}/cel_emissive.gdshader", "5_emi")
    glow = s.ext_res("Shader", f"{SH}/glow_billboard.gdshader", "6_glow")
    m_sky = sky_material(s)
    env = add_environment(s, m_sky)
    world_parent = "World"
    # сначала узлы-корни: порядок узлов в файле = порядок в дереве
    s.node("SpikeRender", "Node3D", node_paths=["hud", "camera_rig", "world_environment", "cars", "decor"], props=[])
    s.node("WorldEnvironment", "WorldEnvironment", ".", props=[("environment", env)])
    s.node("CameraRig", "Node3D", ".")
    pitch = -math.atan2(6.0, 30.0)
    s.node("Camera3D", "Camera3D", "CameraRig", props=[("transform", xform(rot_x(pitch), (0, 7.0, 30.0))),
           ("current", "true"), ("fov", "68.0"), ("far", "600.0")])
    s.node("World", "Node3D", ".")
    names, m_windows = add_world(s, rng, world_parent, cel, emi, glow, double=True)
    s.node("Cars", "Node3D", ".")
    car_paths = []
    for i in range(8):
        col, row = i % 2, i // 2
        x = -2.2 if col == 0 else 2.2
        z = -9.0 + row * 6.0 + (0 if col == 0 else 3.0)
        s.node(f"Car{i + 1}", None, "Cars", instance=car, props=[("transform", xform(origin=(x, 0, z)))])
        car_paths.append(f'NodePath("Cars/Car{i + 1}")')
    s.node("Hud", None, ".", instance=hud)
    # свойства корня — после того как известны пути
    root = s.nodes[0]
    decor = ", ".join(f'NodePath("World/{n}")' for n in names)
    root += "\n" + "\n".join([
        f"script = {script}", 'hud = NodePath("Hud")', 'camera_rig = NodePath("CameraRig")',
        'world_environment = NodePath("WorldEnvironment")', f"sky_material = {m_sky}", f"window_material = {m_windows}",
        f"cars = [{', '.join(car_paths)}]", f"decor = [{decor}]"])
    s.nodes[0] = root
    s.write("scenes/dev/spikes/spike_render.tscn")


# ---------------------------------------------------------------- spike_vfx
def gradient(s: Scene, rid: str, stops: list) -> str:
    """stops: [(offset, '#RRGGBB', alpha)]"""
    offs = ", ".join(num(o) for o, _, _ in stops)
    cols = []
    for _, h, a in stops:
        h = h.lstrip("#")
        cols += [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)] + [a]
    return s.sub_res("Gradient", rid, [("offsets", f"PackedFloat32Array({offs})"),
                                       ("colors", "PackedColorArray(" + ", ".join(num(c) for c in cols) + ")")])


def curve(s: Scene, rid: str, pts: list) -> str:
    data = ", ".join(f"Vector2({num(x)}, {num(y)}), 0.0, 0.0, 0, 0" for x, y in pts)
    return s.sub_res("Curve", rid, [("_data", f"[{data}]"), ("point_count", str(len(pts)))])


def pv3(points) -> str:
    return "PackedVector3Array(" + ", ".join(f"{num(x)}, {num(y)}, {num(z)}" for x, y, z in points) + ")"


VFX_RADIUS = 30.0       # = RADIUS_M в spike_vfx.gd
DRIFT_DEG = 25.0
# Длина квада шлейфа и следа ≥ шаг излучателя за кадр: 250 км/ч = 69,4 м/с, при 25 FPS («1 % худших») 2,78 м.
# CPUParticles3D не интерполирует положение излучателя внутри кадра: все частицы кадра рождаются в одной точке.
STREAK_LEN = 2.8
TIRE_HALF = 0.14        # полуширина полосы шины, м
MARK_RATE = 30.0        # следов в секунду: шаг на 250 км/ч 2,3 м < STREAK_LEN
MARK_LIFE = 4.0


def gen_vfx():
    rng = random.Random(23)
    s = Scene()
    script = s.ext_res("Script", f"{SP}/spike_vfx.gd", "1_vfx")
    hud = s.ext_res("PackedScene", f"{SP}/spike_hud.tscn", "2_hud")
    car = s.ext_res("PackedScene", f"{SP}/props/dummy_car.tscn", "3_car")
    cel = s.ext_res("Shader", f"{SH}/cel_lit.gdshader", "4_cel")
    emi = s.ext_res("Shader", f"{SH}/cel_emissive.gdshader", "5_emi")
    glow = s.ext_res("Shader", f"{SH}/glow_billboard.gdshader", "6_glow")
    sh_smoke = s.ext_res("Shader", f"{SH}/smoke_cutoff.gdshader", "7_smoke")
    sh_trail = s.ext_res("Shader", f"{SH}/trail.gdshader", "8_trail")
    sh_mark = s.ext_res("Shader", f"{SH}/tire_mark.gdshader", "10_mark")
    sh_lines = s.ext_res("Shader", f"{SH}/speed_lines.gdshader", "11_lines")
    sh_blur = s.ext_res("Shader", f"{SP}/speed_blur_dev.gdshader", "12_blur")
    m_sky = sky_material(s)
    env = add_environment(s, m_sky)

    m_smoke = shader_mat(s, "ShaderMaterial_smoke", sh_smoke, {})
    m_trail = shader_mat(s, "ShaderMaterial_trail", sh_trail, {})
    m_spark = shader_mat(s, "ShaderMaterial_spark", sh_trail, {"edge_soft": "0.5", "energy": "1.2"})
    d = math.radians(DRIFT_DEG)
    mark_lat = 0.86 * math.cos(d)          # задние колёса поперёк направления движения в заносе
    mark_half = mark_lat + TIRE_HALF
    m_mark = shader_mat(s, "ShaderMaterial_tiremark", sh_mark,
                        {"wheel_pair": "true", "stripe": num(TIRE_HALF / mark_half)}, render_priority=-1)
    m_lines = shader_mat(s, "ShaderMaterial_lines", sh_lines, {})
    m_blur = shader_mat(s, "ShaderMaterial_blur", sh_blur, {})
    q_smoke = s.sub_res("QuadMesh", "QuadMesh_smoke", [("material", m_smoke), ("size", "Vector2(1, 1)")])
    # center_offset: квад тянется от частицы назад по скорости, а не торчит вперёд в кузов
    q_trail = s.sub_res("QuadMesh", "QuadMesh_trail", [("material", m_trail), ("size", f"Vector2(0.14, {num(STREAK_LEN)})"),
                                                       ("center_offset", v3(0, STREAK_LEN / 2, 0))])
    q_spark = s.sub_res("QuadMesh", "QuadMesh_spark", [("material", m_spark), ("size", "Vector2(0.06, 0.6)")])
    q_mark = s.sub_res("PlaneMesh", "PlaneMesh_tiremark", [("material", m_mark),
                       ("size", f"Vector2({num(2 * mark_half)}, {num(STREAK_LEN)})"), ("center_offset", v3(0, 0, STREAK_LEN / 2))])
    g_smoke = gradient(s, "Gradient_smoke", [(0, "#FFFFFF", 1.0), (0.6, "#FFFFFF", 1.0), (1, "#FFFFFF", 0.15)])
    g_trail = gradient(s, "Gradient_trail", [(0, "#FF5FA2", 0.9), (1, "#B5408E", 0.0)])
    g_spark = gradient(s, "Gradient_spark", [(0, "#FFFFFF", 1.0), (0.4, "#FFC870", 1.0), (1, "#FF4F6E", 0.0)])
    g_mark = gradient(s, "Gradient_tiremark", [(0, "#FFFFFF", 1.0), (0.7, "#FFFFFF", 1.0), (1, "#FFFFFF", 0.0)])
    c_smoke = curve(s, "Curve_smoke", [(0, 0.35), (1, 1)])

    s.node("SpikeVfx", "Node3D", node_paths=["hud", "car_rig", "side_camera", "chase_camera", "smoke", "sparks",
                                            "trails", "marks", "speed_lines", "speed_blur"], props=[])
    s.node("WorldEnvironment", "WorldEnvironment", ".", props=[("environment", env)])
    s.node("SideCamera", "Camera3D", ".", props=[("transform", xform(rot_x(-math.atan2(3.5, 52.0)), (0, 4.5, 52.0))),
           ("current", "true"), ("fov", "68.0"), ("far", "600.0")])
    s.node("World", "Node3D", ".")
    add_world(s, rng, "World", cel, emi, glow, double=False)
    s.node("CarRig", "Node3D", ".")
    s.node("ChaseCamera", "Camera3D", "CarRig", props=[
        ("transform", xform(matmul(rot_y(-math.pi / 2), rot_x(-0.12)), (-7.0, 2.4, VFX_RADIUS))),
        ("fov", "74.0"), ("far", "600.0")])
    paths = {"smoke": [], "sparks": [], "trails": [], "marks": []}
    common = [("local_coords", "false")]
    for i in range(8):
        a = 2 * math.pi * i / 8
        slot = f"Slot{i + 1}"
        sp = f"CarRig/{slot}"
        s.node(slot, "Node3D", "CarRig", props=[("transform", xform(rot_y(a - math.pi / 2 + d),
               (VFX_RADIUS * math.sin(a), 0, VFX_RADIUS * math.cos(a))))])
        s.node("Car", None, sp, instance=car)
        s.node("Smoke", "CPUParticles3D", sp, props=[
            ("amount", "24"), ("lifetime", "0.9"), *common, ("mesh", q_smoke),
            ("emission_shape", "4"), ("emission_points", pv3([(-0.86, 0.3, 1.5), (0.86, 0.3, 1.5)])),
            ("direction", v3(0, 0.5, 1)), ("spread", "35.0"), ("gravity", v3(0, 0.6, 0)),
            ("initial_velocity_min", "1.0"), ("initial_velocity_max", "2.5"), ("damping_min", "1.5"), ("damping_max", "1.5"),
            ("angle_min", "0.0"), ("angle_max", "360.0"), ("scale_amount_min", "1.2"), ("scale_amount_max", "2.0"),
            ("scale_amount_curve", c_smoke), ("color_ramp", g_smoke)])
        s.node("Sparks", "CPUParticles3D", sp, props=[
            ("transform", xform(origin=(0.95, 0.45, -0.3))),
            ("emitting", "false"), ("amount", "20"), ("lifetime", "0.25"), ("one_shot", "true"), ("explosiveness", "1.0"),
            *common, ("mesh", q_spark),
            ("particle_flag_align_y", "true"), ("direction", v3(1, 0.4, 0)), ("spread", "50.0"),
            ("initial_velocity_min", "6.0"), ("initial_velocity_max", "12.0"), ("color_ramp", g_spark)])
        for side, x in (("TrailL", -0.6), ("TrailR", 0.6)):
            s.node(side, "CPUParticles3D", sp, props=[
                ("transform", xform(rot_y(-d), (x, 0.78, 2.25))),
                ("amount", "20"), ("lifetime", "0.5"), *common, ("mesh", q_trail),
                ("particle_flag_align_y", "true"), ("direction", v3(0, 0, 1)), ("spread", "0.0"),
                ("gravity", v3(0, 0, 0)), ("initial_velocity_min", "0.05"), ("initial_velocity_max", "0.05"),
                ("color_ramp", g_trail)])
            paths["trails"].append(f'NodePath("{sp}/{side}")')
        s.node("Marks", "CPUParticles3D", sp, props=[
            ("transform", xform(rot_y(-d), (0, 0.02, 1.4))),
            ("amount", str(int(MARK_RATE * MARK_LIFE))), ("lifetime", num(MARK_LIFE)), *common, ("mesh", q_mark),
            ("gravity", v3(0, 0, 0)), ("initial_velocity_min", "0.0"), ("initial_velocity_max", "0.0"),
            ("color_ramp", g_mark)])
        paths["smoke"].append(f'NodePath("{sp}/Smoke")')
        paths["sparks"].append(f'NodePath("{sp}/Sparks")')
        paths["marks"].append(f'NodePath("{sp}/Marks")')
    s.node("Overlay", "CanvasLayer", ".", props=[("layer", "10")])
    full = [("layout_mode", "3"), ("anchors_preset", "15"), ("anchor_right", "1.0"), ("anchor_bottom", "1.0"),
            ("grow_horizontal", "2"), ("grow_vertical", "2"), ("mouse_filter", "2")]
    s.node("SpeedBlur", "ColorRect", "Overlay", props=[("visible", "false"), ("material", m_blur), *full])
    s.node("SpeedLines", "ColorRect", "Overlay", props=[("visible", "false"), ("material", m_lines), *full])
    s.node("Hud", None, ".", instance=hud)
    root = s.nodes[0] + "\n" + "\n".join([
        f"script = {script}", 'hud = NodePath("Hud")', 'car_rig = NodePath("CarRig")',
        'side_camera = NodePath("SideCamera")', 'chase_camera = NodePath("CarRig/ChaseCamera")',
        *(f"{k} = [{', '.join(v)}]" for k, v in paths.items()),
        'speed_lines = NodePath("Overlay/SpeedLines")', 'speed_blur = NodePath("Overlay/SpeedBlur")'])
    s.nodes[0] = root
    s.write("scenes/dev/spikes/spike_vfx.tscn")


# ---------------------------------------------------------------- spike_audio
FULL_RECT = [("layout_mode", "3"), ("anchors_preset", "15"), ("anchor_right", "1.0"), ("anchor_bottom", "1.0"),
             ("grow_horizontal", "2"), ("grow_vertical", "2")]


def gen_audio():
    """S-07 тон мотора (1 петля + pitch_scale ↔ 3 петли + громкость, Sample ↔ Stream), S-11 вибрация.
    Петли — scenes/dev/spikes/audio/src/gen_engine_loops.py."""
    s = Scene()
    script = s.ext_res("Script", f"{SP}/spike_audio.gd", "1_audio")
    hud = s.ext_res("PackedScene", f"{SP}/spike_hud.tscn", "2_hud")
    loops = {r: s.ext_res("AudioStream", f"{SP}/audio/engine_r{r}.ogg", f"{3 + i}_r{r}") for i, r in enumerate(("070", "100", "180"))}
    s.node("SpikeAudio", "Control", node_paths=["hud", "engine_low", "engine_base", "engine_high", "rpm_slider", "rpm_label", "info_label"],
           props=FULL_RECT)
    child_full = [("layout_mode", "1")] + FULL_RECT[1:]
    s.node("Background", "ColorRect", ".", props=child_full + [("mouse_filter", "2"), ("color", "Color(0.075, 0.047, 0.153, 1)")])
    for name, r in (("EngineLow", "070"), ("EngineBase", "100"), ("EngineHigh", "180")):
        s.node(name, "AudioStreamPlayer", ".", props=[("stream", loops[r]), ("bus", '&"Engines"')])
    s.node("Center", "CenterContainer", ".", props=child_full)
    s.node("Box", "VBoxContainer", "Center", props=[("layout_mode", "2"), ("theme_override_constants/separation", "20")])
    s.node("Title", "Label", "Center/Box", props=[("layout_mode", "2"), ("theme_override_colors/font_color", "Color(0.957, 0.675, 0.353, 1)"),
           ("theme_override_font_sizes/font_size", "34"), ("text", '"Звук мотора и вибрация · S-07 S-11"'), ("horizontal_alignment", "1")])
    s.node("RpmLabel", "Label", "Center/Box", props=[("layout_mode", "2"), ("theme_override_font_sizes/font_size", "28"),
           ("text", '"…"'), ("horizontal_alignment", "1")])
    # высота 72 px — палец попадает в ползунок на телефоне; шаг 0,01 = 30 об/мин
    s.node("RpmSlider", "HSlider", "Center/Box", props=[("custom_minimum_size", "Vector2(900, 72)"), ("layout_mode", "2"),
           ("min_value", "0.7"), ("max_value", "1.8"), ("step", "0.01"), ("value", "1.0")])
    s.node("Info", "Label", "Center/Box", props=[("custom_minimum_size", "Vector2(900, 0)"), ("layout_mode", "2"),
           ("theme_override_colors/font_color", "Color(0.737, 0.643, 0.82, 1)"), ("theme_override_font_sizes/font_size", "18"),
           ("text", '"…"'), ("autowrap_mode", "3")])
    s.node("Hud", None, ".", instance=hud)
    s.nodes[0] = s.nodes[0] + "\n" + "\n".join([
        f"script = {script}", 'hud = NodePath("Hud")', 'engine_low = NodePath("EngineLow")', 'engine_base = NodePath("EngineBase")',
        'engine_high = NodePath("EngineHigh")', 'rpm_slider = NodePath("Center/Box/RpmSlider")',
        'rpm_label = NodePath("Center/Box/RpmLabel")', 'info_label = NodePath("Center/Box/Info")'])
    s.write("scenes/dev/spikes/spike_audio.tscn")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    if what in ("car", "all"):
        gen_car()
    if what in ("render", "all"):
        gen_render()
    if what in ("vfx", "all"):
        gen_vfx()
    if what in ("audio", "all"):
        gen_audio()
