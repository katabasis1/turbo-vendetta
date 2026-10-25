extends Control
## Меню пакета спайков 1.1 (docs/SPIKES.md §4, чек-лист — docs/SPIKE_CHECKLIST.md).
## Только scenes/dev/ — в релизную сборку не попадает (exclude_filter в export_presets.cfg).

@export var buttons: Array[Button] = []
@export var scene_paths: PackedStringArray = PackedStringArray()
@export var info_label: Label

const WARN_COLOR: Color = Color(1.0, 0.45, 0.45, 1.0)

var _missing: PackedStringArray = PackedStringArray()   # имена файлов сцен, которых нет в этой копии проекта


func _ready() -> void:
	assert(info_label != null and buttons.size() > 0 and buttons.size() == scene_paths.size(), "SpikeMenu: не назначены ссылки в сцене")
	for i: int in buttons.size():
		buttons[i].pressed.connect(_open.bind(scene_paths[i]))
		# Нет файла = неполная или старая копия проекта (так было 17:02: архив старше 16:28, без звука).
		# Кнопку гасим и пишем причину на экран — вместо тихой ошибки загрузчика в консоли.
		if not ResourceLoader.exists(scene_paths[i]):
			_missing.append(scene_paths[i].get_file())
			buttons[i].disabled = true
			buttons[i].text += "  — НЕТ ФАЙЛА"
	if not _missing.is_empty():
		info_label.add_theme_color_override("font_color", WARN_COLOR)
		push_error("SpikeMenu: нет файлов %s. Копия проекта неполная или старая (чекпоинт %s). Нужен свежий turbo-vendetta_latest.zip, распаковать в пустую папку." % [", ".join(_missing), BuildInfo.STAMP])
	info_label.text = _info_text("…")
	RenderingServer.frame_post_draw.connect(_on_first_frame, CONNECT_ONE_SHOT)


func _unhandled_input(event: InputEvent) -> void:
	var key: InputEventKey = event as InputEventKey
	if key == null or not key.pressed or key.echo:
		return
	var idx: int = int(key.physical_keycode) - int(KEY_1)
	if idx >= 0 and idx < buttons.size():
		_open(scene_paths[idx])


func _open(path: String) -> void:
	if not ResourceLoader.exists(path):
		return   # причина уже на экране и в «Выводе» (_ready)
	SpikeHud.scene_requested_ms = Time.get_ticks_msec()
	get_tree().change_scene_to_file(path)


func _info_text(first_frame: String) -> String:
	var v: Dictionary = Engine.get_version_info()
	var build: String = "спайк-экспорт" if OS.has_feature("spikes") else ("редактор" if OS.has_feature("editor") else "обычная сборка")
	var lines: PackedStringArray = PackedStringArray([
		"Копия проекта: чекпоинт %s" % BuildInfo.STAMP,
		"Godot %s · %s · %s" % [str(v.get("string", "?")), str(ProjectSettings.get_setting("rendering/renderer/rendering_method")), OS.get_name()],
		"Видеоадаптер: %s" % RenderingServer.get_video_adapter_name(),
		"Сборка: %s, %s" % [build, "debug" if OS.is_debug_build() else "release"],
		"Физика: %s, %d Гц" % [str(ProjectSettings.get_setting("physics/3d/physics_engine")), Engine.physics_ticks_per_second],
		"Устройство по SDK: %s · тач: %s · язык: %s" % [YandexSDK.get_device_type(), "да" if DisplayServer.is_touchscreen_available() else "нет", TranslationServer.get_locale()],
		"Первый кадр меню: %s" % first_frame,
	])
	if not _missing.is_empty():
		lines.append("НЕТ ФАЙЛОВ: %s — копия проекта неполная или старая. Скачайте turbo-vendetta_latest.zip из Pod и распакуйте в пустую папку." % ", ".join(_missing))
	return "\n".join(lines)


func _on_first_frame() -> void:
	info_label.text = _info_text("%d мс от старта движка" % Time.get_ticks_msec())
