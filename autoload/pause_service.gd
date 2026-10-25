extends Node
## Пауза по набору причин: &"focus", &"ad", &"menu" (ARCHITECTURE §5.4).
## Пока набор не пуст — get_tree().paused = true. При focus и ad ещё и глушится шина Master (правило 5).
## Сам вызывает YandexSDK.gameplay_start/stop: заезд идёт и паузы нет → start, иначе → stop.

signal paused(reason: StringName)
signal resumed(reason: StringName)

const MUTING_REASONS: Array[StringName] = [&"focus", &"ad"]

var _reasons: Dictionary[StringName, bool] = {}
var _in_race: bool = false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	YandexSDK.pause_requested.connect(request_pause)
	YandexSDK.resume_requested.connect(release_pause)
	EventBus.race_started.connect(_on_race_started)
	EventBus.race_left.connect(_on_race_ended)
	# EventBus.race_finished → _on_race_ended подключается на этапе 1.7 вместе с сигналом.

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		request_pause(&"focus")
	elif what == NOTIFICATION_APPLICATION_FOCUS_IN:
		release_pause(&"focus")

func request_pause(reason: StringName) -> void:
	if _reasons.has(reason):
		return
	_reasons[reason] = true
	_apply()
	paused.emit(reason)

func release_pause(reason: StringName) -> void:
	if not _reasons.erase(reason):
		return
	_apply()
	resumed.emit(reason)

func is_paused() -> bool:
	return not _reasons.is_empty()

func has_reason(reason: StringName) -> bool:
	return _reasons.has(reason)

func _apply() -> void:
	get_tree().paused = is_paused()
	var mute: bool = false
	for r: StringName in MUTING_REASONS:
		if _reasons.has(r):
			mute = true
	var master: int = AudioServer.get_bus_index(&"Master")
	if master >= 0:
		AudioServer.set_bus_mute(master, mute)
	_sync_gameplay()

func _sync_gameplay() -> void:
	if _in_race and not is_paused():
		YandexSDK.gameplay_start()
	else:
		YandexSDK.gameplay_stop()

func _on_race_started(_track_id: StringName) -> void:
	_in_race = true
	_sync_gameplay()

func _on_race_ended() -> void:
	_in_race = false
	_sync_gameplay()
