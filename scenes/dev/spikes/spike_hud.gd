class_name SpikeHud
extends CanvasLayer
## Оверлей замера спайков (docs/SPIKES.md §1). Только scenes/dev/ — в релизную сборку не попадает.
## Цифры: FPS средний и «1 % худших» за 10 с, draw calls, треугольники, время физики и процесса,
## статическая память, время до первого кадра сцены. Клавиши 1–6 — варианты спайка, F — заморозить цифры.
## Те же действия — кнопками на экране (телефон).

signal variant_pressed(index: int)

const WINDOW_S: float = 10.0
const REFRESH_S: float = 0.5
const MAX_SAMPLES: int = 2400                 # 10 с при 240 FPS
const MENU_SCENE: String = "res://scenes/dev/spikes/spike_menu.tscn"
const VARIANT_KEYS: Array[int] = [KEY_1, KEY_2, KEY_3, KEY_4, KEY_5, KEY_6]

## Когда запросили смену сцены (мс от старта движка). Ставят меню и кнопка «Меню».
static var scene_requested_ms: int = -1

@export var title_label: Label
@export var stats_label: Label
@export var variants_label: Label
@export var variant_buttons: Array[Button] = []
@export var freeze_button: Button
@export var menu_button: Button

var _dt: PackedFloat32Array = PackedFloat32Array()
var _head: int = 0
var _count: int = 0
var _window_sum: float = 0.0
var _last_us: int = 0
var _refresh_left: float = 0.0
var _frozen: bool = false
var _title: String = ""
var _first_frame_text: String = "…"
var _names: PackedStringArray = PackedStringArray()
var _states: PackedStringArray = PackedStringArray()


func _ready() -> void:
	assert(title_label != null and stats_label != null and variants_label != null, "SpikeHud: не назначены подписи")
	assert(variant_buttons.size() == 6 and freeze_button != null and menu_button != null, "SpikeHud: не назначены кнопки")
	layer = 100
	process_mode = Node.PROCESS_MODE_ALWAYS
	_dt.resize(MAX_SAMPLES)
	_names.resize(6)
	_states.resize(6)
	for i: int in variant_buttons.size():
		variant_buttons[i].pressed.connect(_emit_variant.bind(i + 1))
	freeze_button.pressed.connect(_toggle_freeze)
	menu_button.pressed.connect(go_menu)
	RenderingServer.frame_post_draw.connect(_on_first_frame, CONNECT_ONE_SHOT)
	_refresh_variants()


## Заголовок и названия вариантов 1–6 (пустая строка — кнопка выключена).
func setup(title: String, names: PackedStringArray) -> void:
	_title = title
	for i: int in 6:
		_names[i] = names[i] if i < names.size() else ""
		variant_buttons[i].disabled = _names[i].is_empty()
	_refresh_variants()


## Текущее состояние варианта (index 1–6), например «ночь» или «вкл».
func set_state(index: int, state: String) -> void:
	_states[index - 1] = state
	_refresh_variants()


func go_menu() -> void:
	SpikeHud.scene_requested_ms = Time.get_ticks_msec()
	get_tree().change_scene_to_file(MENU_SCENE)


func _unhandled_input(event: InputEvent) -> void:
	var key: InputEventKey = event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return
	var idx: int = VARIANT_KEYS.find(int(key.physical_keycode))
	if idx >= 0 and not _names[idx].is_empty():
		_emit_variant(idx + 1)
	elif key.physical_keycode == KEY_F:
		_toggle_freeze()
	elif key.physical_keycode == KEY_ESCAPE:
		go_menu()


func _process(_delta: float) -> void:
	var now: int = Time.get_ticks_usec()
	if _last_us > 0:
		var dt: float = float(now - _last_us) / 1000000.0
		_push(dt)
		_refresh_left -= dt
	_last_us = now
	if _refresh_left <= 0.0:
		_refresh_left = REFRESH_S
		if not _frozen:
			stats_label.text = _stats_text()


func _push(dt: float) -> void:
	_dt[_head] = dt
	_head = (_head + 1) % MAX_SAMPLES
	_window_sum += dt
	if _count < MAX_SAMPLES:
		_count += 1
	else:
		_window_sum -= _dt[_head]
	while _count > 1 and _window_sum > WINDOW_S:
		var oldest: int = (_head - _count + MAX_SAMPLES) % MAX_SAMPLES
		_window_sum -= _dt[oldest]
		_count -= 1


func _stats_text() -> String:
	var avg_fps: float = 0.0
	var low_fps: float = 0.0
	if _count > 0 and _window_sum > 0.0:
		avg_fps = float(_count) / _window_sum
		var arr: PackedFloat32Array = PackedFloat32Array()
		arr.resize(_count)
		for i: int in _count:
			arr[i] = _dt[(_head - _count + i + MAX_SAMPLES) % MAX_SAMPLES]
		arr.sort()
		var worst: int = maxi(1, int(_count * 0.01))
		var s: float = 0.0
		for i: int in worst:
			s += arr[_count - 1 - i]
		low_fps = float(worst) / s
	var calls: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME))
	var prims: int = int(Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME))
	var t_phys: float = Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0
	var t_proc: float = Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0
	var mem: float = Performance.get_monitor(Performance.MEMORY_STATIC) / 1048576.0
	var mem_text: String = "%.1f МБ" % mem if mem > 0.0 else "— (только debug-сборка)"
	var vp: Vector2 = get_viewport().get_visible_rect().size
	var lines: PackedStringArray = PackedStringArray([
		"FPS %.1f ср · %.1f «1 %% худших» · окно %.0f с" % [avg_fps, low_fps, minf(_window_sum, WINDOW_S)],
		"Draw calls %d · треугольников %d" % [calls, prims],
		"Физика %.2f мс · процесс %.2f мс" % [t_phys, t_proc],
		"Память %s" % mem_text,
		"Первый кадр: %s" % _first_frame_text,
		"Экран %d×%d · физика %d Гц" % [int(vp.x), int(vp.y), Engine.physics_ticks_per_second],
	])
	return "\n".join(lines)


func _refresh_variants() -> void:
	title_label.text = _title + ("   [F] ЗАМОРОЖЕНО" if _frozen else "")
	var lines: PackedStringArray = PackedStringArray()
	for i: int in 6:
		if _names[i].is_empty():
			continue
		var st: String = _states[i]
		lines.append("%d · %s%s" % [i + 1, _names[i], (": " + st) if not st.is_empty() else ""])
	lines.append("F · заморозить цифры · Esc · меню")
	variants_label.text = "\n".join(lines)


func _emit_variant(index: int) -> void:
	variant_pressed.emit(index)


func _toggle_freeze() -> void:
	_frozen = not _frozen
	if not _frozen:
		stats_label.text = _stats_text()
	_refresh_variants()


func _on_first_frame() -> void:
	var now: int = Time.get_ticks_msec()
	_first_frame_text = "%d мс от старта движка" % now
	if scene_requested_ms >= 0:
		_first_frame_text += " · %d мс от смены сцены" % (now - scene_requested_ms)
		scene_requested_ms = -1
