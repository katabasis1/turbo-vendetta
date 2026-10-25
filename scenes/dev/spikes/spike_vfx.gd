extends Node3D
## Спайк эффектов (docs/SPIKES.md §2): 8 болванок едут по кругу R = 30 м в заносе 25°, все эффекты включены.
## 1 — бюджет телефон ↔ ПК (S-05: дым 12 ↔ 24 на машину, искры 12 ↔ 20 за удар);
## 2 — скорость 100 ↔ 250 км/ч (S-15: шлейф линией или пунктиром; скриншот сбоку);
## 3 — следы шин вкл/выкл (S-16: мерцание на 10–30 м, цена в FPS);
## 4 — экранный эффект: нет → линии скорости (без чтения экрана) → радиальное размытие (hint_screen_texture) (S-13);
## 5 — камера сбоку ↔ за машиной; 6 — все частицы выкл/вкл (база для замера S-05).
## Удары: по кругу, каждые HIT_PERIOD_S / 8 одна машина «бьётся» правым бортом — вспышка искр.
## Вращение рига — в _process, а не AnimationPlayer: скорость меняется клавишей 2, а формат анимации без движка не проверить.
## Генератор сцены — tools/agent/gen_spike_scenes.py. Значения эффектов — STYLE_GUIDE §6.

const RADIUS_M: float = 30.0                          # = VFX_RADIUS в генераторе
const SPEEDS_KMH: Array[float] = [100.0, 250.0]
const SMOKE_PER_CAR: Array[int] = [12, 24]            # [телефон, ПК] — STYLE_GUIDE §6: ≤ 24, на телефоне ≤ 12
const SPARKS_PER_HIT: Array[int] = [12, 20]           # STYLE_GUIDE §6: 12–20 за удар
const HIT_PERIOD_S: float = 1.2                       # каждая машина бьётся раз в 1,2 с; чаще — больше искр в кадре
const SPEED_LINES_INTENSITY: float = 0.25             # STYLE_GUIDE §6: скорость — α 0,25 (таран — 1,0)
const BUDGET_NAMES: Array[String] = ["телефон", "ПК"]
const SCREEN_FX_NAMES: Array[String] = ["нет", "линии (без чтения экрана)", "размытие (чтение экрана)"]

@export var hud: SpikeHud
@export var car_rig: Node3D
@export var side_camera: Camera3D
@export var chase_camera: Camera3D
@export var smoke: Array[CPUParticles3D] = []
@export var sparks: Array[CPUParticles3D] = []
@export var trails: Array[CPUParticles3D] = []
@export var marks: Array[CPUParticles3D] = []
@export var speed_lines: ColorRect
@export var speed_blur: ColorRect

var _budget: int = 0           # 0 — телефон, 1 — ПК
var _speed: int = 1            # индекс в SPEEDS_KMH; старт на 250 — самый тяжёлый случай для шлейфов
var _marks_on: bool = true
var _screen_fx: int = 0
var _chase: bool = false
var _particles_on: bool = true
var _hit_left: float = 0.0
var _next_hit: int = 0


func _ready() -> void:
	assert(hud != null and car_rig != null and side_camera != null and chase_camera != null, "SpikeVfx: не назначены узлы")
	assert(speed_lines != null and speed_blur != null, "SpikeVfx: не назначены экранные эффекты")
	assert(smoke.size() == 8 and sparks.size() == 8 and marks.size() == 8 and trails.size() == 16, "SpikeVfx: нужны эффекты 8 машин")
	hud.setup("Спайк эффектов · S-05 S-13 S-15 S-16", PackedStringArray([
		"Бюджет (S-05)", "Скорость (S-15)", "Следы шин (S-16)", "Экранный эффект (S-13)", "Камера", "Все частицы"]))
	hud.variant_pressed.connect(_on_variant)
	(speed_lines.material as ShaderMaterial).set_shader_parameter(&"intensity", SPEED_LINES_INTENSITY)
	_apply_budget()
	_apply_speed()
	_apply_marks()
	_apply_screen_fx()
	_apply_camera()
	_apply_particles()


func _process(delta: float) -> void:
	var speed_ms: float = SPEEDS_KMH[_speed] / 3.6
	car_rig.rotation.y = wrapf(car_rig.rotation.y + speed_ms / RADIUS_M * delta, 0.0, TAU)
	if not _particles_on:
		return
	_hit_left -= delta
	if _hit_left <= 0.0:
		_hit_left += HIT_PERIOD_S / float(sparks.size())
		sparks[_next_hit].restart()
		_next_hit = (_next_hit + 1) % sparks.size()


func _on_variant(index: int) -> void:
	match index:
		1:
			_budget = 1 - _budget
			_apply_budget()
		2:
			_speed = (_speed + 1) % SPEEDS_KMH.size()
			_apply_speed()
		3:
			_marks_on = not _marks_on
			_apply_marks()
		4:
			_screen_fx = (_screen_fx + 1) % SCREEN_FX_NAMES.size()
			_apply_screen_fx()
		5:
			_chase = not _chase
			_apply_camera()
		6:
			_particles_on = not _particles_on
			_apply_particles()


## Смена amount перезапускает излучатель: дым на секунду пропадёт — это нормально.
func _apply_budget() -> void:
	for p: CPUParticles3D in smoke:
		p.amount = SMOKE_PER_CAR[_budget]
	for p: CPUParticles3D in sparks:
		p.amount = SPARKS_PER_HIT[_budget]
	_show_budget()


func _apply_speed() -> void:
	var speed_ms: float = SPEEDS_KMH[_speed] / 3.6
	hud.set_state(2, "%d км/ч · шаг за кадр при 30 FPS %.1f м" % [int(SPEEDS_KMH[_speed]), speed_ms / 30.0])


func _apply_marks() -> void:
	for p: CPUParticles3D in marks:
		_set_emitter(p, _marks_on and _particles_on)
	hud.set_state(3, "вкл" if _marks_on else "выкл")
	_show_budget()


func _apply_screen_fx() -> void:
	speed_lines.visible = _screen_fx == 1
	speed_blur.visible = _screen_fx == 2
	hud.set_state(4, SCREEN_FX_NAMES[_screen_fx])


func _apply_camera() -> void:
	if _chase:
		chase_camera.make_current()
	else:
		side_camera.make_current()
	hud.set_state(5, "за машиной" if _chase else "сбоку")


func _apply_particles() -> void:
	for p: CPUParticles3D in smoke:
		_set_emitter(p, _particles_on)
	for p: CPUParticles3D in trails:
		_set_emitter(p, _particles_on)
	for p: CPUParticles3D in sparks:
		p.visible = _particles_on
	_apply_marks()
	hud.set_state(6, "вкл" if _particles_on else "выкл (база)")


func _show_budget() -> void:
	hud.set_state(1, "%s: дым %d, искры %d · живых частиц ≈ %d" % [BUDGET_NAMES[_budget], SMOKE_PER_CAR[_budget], SPARKS_PER_HIT[_budget], _live_estimate()])


## Невидимый CPUParticles3D не считается движком — так замер «выкл» честный.
func _set_emitter(p: CPUParticles3D, on: bool) -> void:
	p.visible = on
	p.emitting = on


## Сколько частиц живёт одновременно у 8 машин (дым и шлейфы — полный amount, искры — доля удара, следы — если вкл).
func _live_estimate() -> int:
	if not _particles_on:
		return 0
	var per_car: int = SMOKE_PER_CAR[_budget] + trails[0].amount * 2
	if _marks_on:
		per_car += marks[0].amount
	var sparks_live: float = float(SPARKS_PER_HIT[_budget]) * sparks[0].lifetime / (HIT_PERIOD_S / float(sparks.size()))
	return per_car * smoke.size() + int(sparks_live)
