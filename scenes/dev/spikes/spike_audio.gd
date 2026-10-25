extends Control
## Спайк звука (docs/SPIKES.md §2): петля мотора и вибрация.
## Ползунок — обороты ×0,7…×1,8 от 3000 об/мин (S-07).
## 1 — способ: 1 петля + pitch_scale ↔ 3 петли + громкость (запасной вариант S-07, тон не трогаем);
## 2 — воспроизведение Sample ↔ Stream, только в веб-сборке. Вне браузера Sample не играет вовсе: драйвер звука
##     его не умеет, а микшер такие потоки пропускает → тишина. Поэтому вне веба всегда Stream (ошибка 17:02).
## 3 — автопрогон: пила оборотов, как при разгоне, с резким сбросом на «переключении передачи» —
##     по сбросу видно задержку: ползунок прыгает сразу, звук должен успеть за ≤ 100 мс;
## 4, 5, 6 — вибрация 30 / 60 / 120 мс (S-11).
## Генератор сцены — tools/agent/gen_spike_scenes.py, петель — scenes/dev/spikes/audio/src/gen_engine_loops.py.

const RPM_MIN: float = 0.7
const RPM_MAX: float = 1.8
const BASE_RPM: float = 3000.0                  # = BASE_RPM в gen_engine_loops.py
const LOOP_RATIOS: Array[float] = [0.7, 1.0, 1.8]   # обороты петель EngineLow / EngineBase / EngineHigh
const AUTO_RISE_PER_S: float = 0.4              # 0,7 → 1,8 за 2,75 с; быстрее — жёстче проверка плавности
const AUTO_SHIFT_TO: float = 1.05               # куда падают обороты на «переключении»
const VIBRATE_MS: Array[int] = [30, 60, 120]
const SILENT_DB: float = -80.0

@export var hud: SpikeHud
@export var engine_low: AudioStreamPlayer
@export var engine_base: AudioStreamPlayer
@export var engine_high: AudioStreamPlayer
@export var rpm_slider: HSlider
@export var rpm_label: Label
@export var info_label: Label

var _players: Array[AudioStreamPlayer] = []
var _crossfade: bool = false
var _web: bool = false
var _sample: bool = false                       # true только в вебе, см. _ready
var _auto: bool = false
var _rpm: float = 1.0
var _vibrate_count: PackedInt32Array = PackedInt32Array([0, 0, 0])
var _loop_note: String = ""


func _ready() -> void:
	assert(hud != null and engine_low != null and engine_base != null and engine_high != null, "SpikeAudio: не назначены узлы")
	assert(rpm_slider != null and rpm_label != null and info_label != null, "SpikeAudio: не назначен интерфейс")
	_players = [engine_low, engine_base, engine_high]
	_web = OS.has_feature("web")
	_sample = _web
	_loop_note = _ensure_loops()
	hud.setup("Спайк звука · S-07 S-11", PackedStringArray([
		"Способ (S-07)", "Воспроизведение (S-07)", "Автопрогон", "Вибро 30 мс (S-11)", "Вибро 60 мс (S-11)", "Вибро 120 мс (S-11)"]))
	hud.variant_pressed.connect(_on_variant)
	rpm_slider.value_changed.connect(_on_slider)
	_rpm = rpm_slider.value
	_restart_players()
	_apply_rpm()
	hud.set_state(1, "1 петля + тон")
	hud.set_state(3, "выкл")
	for i: int in VIBRATE_MS.size():
		hud.set_state(4 + i, "нажми")


func _process(delta: float) -> void:
	if not _auto:
		return
	_rpm += AUTO_RISE_PER_S * delta
	if _rpm > RPM_MAX:
		_rpm = AUTO_SHIFT_TO
	rpm_slider.set_value_no_signal(_rpm)
	_apply_rpm()


func _on_slider(value: float) -> void:
	if _auto:
		_auto = false
		hud.set_state(3, "выкл (тронут ползунок)")
	_rpm = value
	_apply_rpm()


func _on_variant(index: int) -> void:
	match index:
		1:
			_crossfade = not _crossfade
			hud.set_state(1, "3 петли + громкость" if _crossfade else "1 петля + тон")
			_apply_rpm()
			_show_info()
		2:
			if not _web:
				hud.set_state(2, "Stream · Sample только в браузере")
				return
			_sample = not _sample
			_restart_players()
		3:
			_auto = not _auto
			if _auto:
				_rpm = RPM_MIN
			hud.set_state(3, "вкл" if _auto else "выкл")
		4, 5, 6:
			var i: int = index - 4
			Input.vibrate_handheld(VIBRATE_MS[i])
			_vibrate_count[i] += 1
			hud.set_state(index, "отправлено ×%d" % _vibrate_count[i])


## Тон и громкость каждый кадр: это и есть проверка S-07 (меняется ли без щелчков в режиме Sample).
func _apply_rpm() -> void:
	if _crossfade:
		var weights: PackedFloat32Array = _crossfade_weights(_rpm)
		for i: int in _players.size():
			_players[i].pitch_scale = 1.0
			_players[i].volume_db = _gain_db(sqrt(weights[i]))   # равная мощность: петли не коррелируют
	else:
		engine_base.pitch_scale = _rpm / LOOP_RATIOS[1]
		engine_base.volume_db = 0.0
		engine_low.volume_db = SILENT_DB
		engine_high.volume_db = SILENT_DB
	rpm_label.text = "Обороты ×%.2f · %d об/мин" % [_rpm, int(_rpm * BASE_RPM)]


## Все 3 петли играют всегда (в режиме тона две — без звука): переключение способа без перезапуска.
func _restart_players() -> void:
	var playback: AudioServer.PlaybackType = AudioServer.PLAYBACK_TYPE_SAMPLE if _sample else AudioServer.PLAYBACK_TYPE_STREAM
	for p: AudioStreamPlayer in _players:
		p.stop()
		p.playback_type = playback
		p.play()
	_apply_rpm()
	var mode: String = "Sample" if _sample else "Stream"
	hud.set_state(2, mode if _web else mode + " · Sample только в браузере")
	_show_info()


func _show_info() -> void:
	info_label.text = "%s\n%s · петли: %s\nКак проверять — docs/SPIKE_CHECKLIST.md." % [
		"Веб-сборка: кнопка 2 переключает Sample ↔ Stream." if _web else "Не браузер: всегда Stream (Sample здесь молчит). Sample для S-07 — только в браузере.",
		"3 петли: громкость каждый кадр" if _crossfade else "тон: pitch_scale каждый кадр", _loop_note]


## Импорт .ogg по умолчанию без петли. Включаем у ресурса и сообщаем, был ли флаг в импорте.
func _ensure_loops() -> String:
	var fixed: int = 0
	for p: AudioStreamPlayer in _players:
		var ogg: AudioStreamOggVorbis = p.stream as AudioStreamOggVorbis
		assert(ogg != null, "SpikeAudio: петля должна быть .ogg")
		if not ogg.loop:
			ogg.loop = true
			fixed += 1
	return "флаг петли из импорта" if fixed == 0 else "петля включена скриптом у %d из 3 (в импорте выкл)" % fixed


## Веса петель для оборотов r: линейно между соседними точками LOOP_RATIOS, сумма = 1.
func _crossfade_weights(r: float) -> PackedFloat32Array:
	var w: PackedFloat32Array = PackedFloat32Array([0.0, 0.0, 0.0])
	var x: float = clampf(r, LOOP_RATIOS[0], LOOP_RATIOS[2])
	if x <= LOOP_RATIOS[1]:
		var t: float = inverse_lerp(LOOP_RATIOS[0], LOOP_RATIOS[1], x)
		w[0] = 1.0 - t
		w[1] = t
	else:
		var t: float = inverse_lerp(LOOP_RATIOS[1], LOOP_RATIOS[2], x)
		w[1] = 1.0 - t
		w[2] = t
	return w


func _gain_db(linear: float) -> float:
	return maxf(linear_to_db(linear), SILENT_DB) if linear > 0.0 else SILENT_DB
