extends Node3D
## Спайк рендера (docs/SPIKES.md §2): камера летит по кругу над 8 болванками машин.
## 1 — условие закат → ночь → туман (S-01: global uniforms, вся палитра меняется за кадр);
## 2 — декор ×2 (S-02: бюджет кадра); 3 — стоп-сигналы через одну (S-06: instance uniform);
## 4 — Glow (S-12); 5 — небо-шейдер ↔ однотонный фон (S-14); 6 — камера стоп/ход (для скриншота).
## Генератор сцены — tools/agent/gen_spike_scenes.py. Значения условий — STYLE_GUIDE §2.1, §2.6.

const ORBIT_PERIOD_S: float = 24.0     # круг камеры; быстрее — заметнее «лесенка» ступеней света
const GLOBAL_KEYS: Array[StringName] = [&"sun_dir", &"sun_color", &"shadow_tint", &"rim_color", &"horizon_color", &"fog_color", &"fog_start", &"fog_end"]
const SKY_KEYS: Array[StringName] = [&"coral", &"middle", &"upper", &"zenith", &"below"]

@export var hud: SpikeHud
@export var camera_rig: Node3D
@export var world_environment: WorldEnvironment
@export var sky_material: ShaderMaterial
@export var window_material: ShaderMaterial
@export var cars: Array[DummyCar] = []
@export var decor: Array[MultiMeshInstance3D] = []

var _conditions: Array[Dictionary] = []
var _condition: int = 0
var _decor_doubled: bool = false
var _brakes: bool = false
var _orbit: bool = true


func _ready() -> void:
	assert(hud != null and camera_rig != null and world_environment != null, "SpikeRender: не назначены узлы")
	assert(sky_material != null and window_material != null, "SpikeRender: не назначены материалы")
	assert(cars.size() == 8 and decor.size() > 0, "SpikeRender: нужны 8 машин и декор")
	_conditions = _make_conditions()
	hud.setup("Спайк рендера · S-01 S-02 S-06 S-12 S-14", PackedStringArray([
		"Условие (S-01)", "Декор ×2 (S-02)", "Стоп-сигналы через одну (S-06)", "Glow (S-12)", "Фон (S-14)", "Камера"]))
	hud.variant_pressed.connect(_on_variant)
	_apply_condition()
	_apply_decor()
	_apply_brakes()
	_apply_glow(false)
	_apply_sky(true)
	hud.set_state(6, "летит")


func _process(delta: float) -> void:
	if _orbit:
		camera_rig.rotation.y = wrapf(camera_rig.rotation.y + TAU / ORBIT_PERIOD_S * delta, 0.0, TAU)


func _on_variant(index: int) -> void:
	match index:
		1:
			_condition = (_condition + 1) % _conditions.size()
			_apply_condition()
		2:
			_decor_doubled = not _decor_doubled
			_apply_decor()
		3:
			_brakes = not _brakes
			_apply_brakes()
		4:
			_apply_glow(not world_environment.environment.glow_enabled)
		5:
			_apply_sky(world_environment.environment.background_mode != Environment.BG_SKY)
		6:
			_orbit = not _orbit
			hud.set_state(6, "летит" if _orbit else "стоит")


func _apply_condition() -> void:
	var c: Dictionary = _conditions[_condition]
	for key: StringName in GLOBAL_KEYS:
		RenderingServer.global_shader_parameter_set(key, c[key])
	for key: StringName in SKY_KEYS:
		sky_material.set_shader_parameter(key, c[key])
	window_material.set_shader_parameter(&"energy", c[&"windows"])
	world_environment.environment.background_color = c[&"horizon_color"] as Color
	hud.set_state(1, str(c[&"name"]))


func _apply_decor() -> void:
	var total: int = 0
	for mmi: MultiMeshInstance3D in decor:
		var mm: MultiMesh = mmi.multimesh
		mm.visible_instance_count = -1 if _decor_doubled else mm.instance_count >> 1
		total += mm.instance_count if _decor_doubled else mm.instance_count >> 1
	hud.set_state(2, "%s, экземпляров %d" % ["×2" if _decor_doubled else "×1", total])


func _apply_brakes() -> void:
	for i: int in cars.size():
		cars[i].set_brake(_brakes and i % 2 == 0)
	hud.set_state(3, "горят у 1, 3, 5, 7" if _brakes else "выкл")


func _apply_glow(on: bool) -> void:
	world_environment.environment.glow_enabled = on
	hud.set_state(4, "вкл" if on else "выкл")


func _apply_sky(use_sky: bool) -> void:
	world_environment.environment.background_mode = Environment.BG_SKY if use_sky else Environment.BG_COLOR
	hud.set_state(5, "небо-шейдер" if use_sky else "однотонный")


## Три условия: «Закат» (= [shader_globals] в project.godot), «Ночь», «Туман» (STYLE_GUIDE §2.6).
func _make_conditions() -> Array[Dictionary]:
	return [
		{
			&"name": "закат", &"windows": 1.0,
			&"sun_dir": Vector3(-0.35, 0.25, -0.9), &"sun_color": Color("#FFF1D6"), &"shadow_tint": Color("#402A69"),
			&"rim_color": Color("#F3A0A8"), &"horizon_color": Color("#F6B26B"), &"fog_color": Color("#EB7B93"),
			&"fog_start": 60.0, &"fog_end": 400.0,
			&"coral": Color("#EB7B93"), &"middle": Color("#9D4488"), &"upper": Color("#46286E"),
			&"zenith": Color("#24163F"), &"below": Color("#7A4A86"),
		},
		{
			&"name": "ночь", &"windows": 1.5,
			&"sun_dir": Vector3(0.3, 0.35, -0.88), &"sun_color": Color("#B8B2E6"), &"shadow_tint": Color("#1B1030"),
			&"rim_color": Color("#8FE8FF"), &"horizon_color": Color("#6B3F8E"), &"fog_color": Color("#3A2A6A"),
			&"fog_start": 40.0, &"fog_end": 320.0,
			&"coral": Color("#4A2F78"), &"middle": Color("#2A1F5C"), &"upper": Color("#1C1544"),
			&"zenith": Color("#0E0A24"), &"below": Color("#2A1F4A"),
		},
		{
			&"name": "туман", &"windows": 0.8,
			&"sun_dir": Vector3(-0.5, 0.18, -0.85), &"sun_color": Color("#FFF6EA"), &"shadow_tint": Color("#715194"),
			&"rim_color": Color("#FFF6EA"), &"horizon_color": Color("#FFD6B8"), &"fog_color": Color("#E7C6D2"),
			&"fog_start": 20.0, &"fog_end": 200.0,
			&"coral": Color("#EBC0C8"), &"middle": Color("#C9A3C8"), &"upper": Color("#9C8CB8"),
			&"zenith": Color("#6E6A9E"), &"below": Color("#D9B8C8"),
		},
	]
