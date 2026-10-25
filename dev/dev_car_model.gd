extends Node3D
## Dev-превью модели машины: поворотный круг под закатным светом (S-19 — контур в Godot, 1.3 — вид модели).
## Клавиши: Пробел — вращение вкл/выкл, ←/→ — повернуть вручную, 1–4 — ракурс (погоня, 3/4 спереди, бок, корма),
## O — контур вкл/выкл, B — стоп-сигнал, Esc — в меню спайков. Телефон: касание слева — контур, по центру — ракурс,
## справа — стоп-сигнал. Сцена собрана генератором tools/agent/gen_car_scenes.py.

const SPIKE_MENU: String = "res://scenes/dev/spikes/spike_menu.tscn"
const TURN_SPEED: float = 0.45           # рад/с
const VIEWS: Array[Dictionary] = [
	{&"name": "погоня", &"eye": Vector3(0.0, 2.2, 6.4), &"target": Vector3(0.0, 0.6, 0.0), &"fov": 70.0},
	{&"name": "3/4 спереди", &"eye": Vector3(-4.6, 1.6, -5.6), &"target": Vector3(0.0, 0.55, 0.0), &"fov": 36.0},
	{&"name": "бок", &"eye": Vector3(-9.0, 0.7, 0.0), &"target": Vector3(0.0, 0.55, 0.0), &"fov": 32.0},
	{&"name": "корма 3/4", &"eye": Vector3(3.6, 1.3, 5.2), &"target": Vector3(0.0, 0.5, 0.0), &"fov": 40.0},
]

@export var turntable: Node3D
@export var car: CarModel
@export var camera: Camera3D
@export var info_label: Label
@export var ground_y: float = -0.235

var _spin: bool = true
var _outline: bool = true
var _brake: bool = false
var _view: int = 0


func _ready() -> void:
	assert(turntable != null and car != null and camera != null and info_label != null, "DevCarModel: не назначены узлы")
	print("[dev_car_model] сборка ", BuildInfo.STAMP)
	_set_view(0)
	_update_info()


func _process(delta: float) -> void:
	if _spin:
		turntable.rotate_y(TURN_SPEED * delta)
	var turn: float = Input.get_axis(&"ui_left", &"ui_right")
	if turn != 0.0:
		turntable.rotate_y(-turn * TURN_SPEED * 2.0 * delta)


func _unhandled_input(event: InputEvent) -> void:
	var touch: InputEventScreenTouch = event as InputEventScreenTouch
	if touch != null and touch.pressed:
		var third: int = int(3.0 * touch.position.x / maxf(get_viewport().get_visible_rect().size.x, 1.0))
		if third <= 0:
			_toggle_outline()
		elif third == 1:
			_set_view((_view + 1) % VIEWS.size())
		else:
			_toggle_brake()
		_update_info()
		return
	var key: InputEventKey = event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return
	match key.keycode:
		KEY_SPACE:
			_spin = not _spin
		KEY_O:
			_toggle_outline()
		KEY_B:
			_toggle_brake()
		KEY_1, KEY_2, KEY_3, KEY_4:
			_set_view(key.keycode - KEY_1)
		KEY_ESCAPE:
			get_tree().change_scene_to_file(SPIKE_MENU)
			return
		_:
			return
	_update_info()


func _toggle_outline() -> void:
	_outline = not _outline
	car.set_outline(_outline)


func _toggle_brake() -> void:
	_brake = not _brake
	car.set_brake(_brake)


func _set_view(i: int) -> void:
	_view = clampi(i, 0, VIEWS.size() - 1)
	var v: Dictionary = VIEWS[_view]
	var up: Vector3 = Vector3(0.0, ground_y, 0.0)
	camera.fov = float(v[&"fov"])
	camera.look_at_from_position(Vector3(v[&"eye"]) + up, Vector3(v[&"target"]) + up)


func _update_info() -> void:
	info_label.text = "Модель машины · сборка %s\nракурс: %s (1–4) · вращение: %s (Пробел, ←/→)\nконтур: %s (O) · стоп-сигнал: %s (B) · Esc — меню\nтелефон: касание слева — контур, центр — ракурс, справа — стоп" % [
		BuildInfo.STAMP, str(VIEWS[_view][&"name"]), _on_off(_spin), _on_off(_outline), _on_off(_brake)]


func _on_off(on: bool) -> String:
	return "вкл" if on else "выкл"
