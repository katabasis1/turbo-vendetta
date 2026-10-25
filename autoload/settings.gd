extends Node
## Настройки игрока (ARCHITECTURE §5.2). Хранятся в ConfigFile user://settings.cfg (с этапа 5.1 — через SaveService).

signal changed(key: StringName)

enum Quality { LOW, HIGH }
enum ControlScheme { AUTO, KEYBOARD, TOUCH }

const PATH: String = "user://settings.cfg"
const SECTION: String = "settings"
const KEYS: Array[StringName] = [
	&"volume_master", &"volume_music", &"volume_sfx", &"vibration", &"reduce_flashes",
	&"quality", &"control_scheme", &"auto_throttle", &"steer_sensitivity",
]

var volume_master: float = 0.8
var volume_music: float = 0.6
var volume_sfx: float = 0.9
var vibration: bool = true
var reduce_flashes: bool = false
var quality: Quality = Quality.HIGH
var control_scheme: ControlScheme = ControlScheme.AUTO
var auto_throttle: bool = true
var steer_sensitivity: float = 1.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	if _is_mobile_device():
		quality = Quality.LOW
	load_settings()
	apply_audio()

## Меняет одно поле, применяет и сразу сохраняет.
func set_value(key: StringName, value: Variant) -> void:
	assert(KEYS.has(key), "Settings: неизвестный ключ %s" % key)
	set(key, value)
	if String(key).begins_with("volume_"):
		apply_audio()
	save_settings()
	changed.emit(key)

## AUTO решается по типу устройства из SDK и наличию тач-экрана.
func get_effective_scheme() -> ControlScheme:
	if control_scheme != ControlScheme.AUTO:
		return control_scheme
	var device: StringName = YandexSDK.get_device_type()
	if device == &"mobile" or device == &"tablet":
		return ControlScheme.TOUCH
	if device != &"desktop" and DisplayServer.is_touchscreen_available():
		return ControlScheme.TOUCH
	return ControlScheme.KEYBOARD

## Вибрация с учётом настройки. Работает ли в мобильном браузере — спайк S-11.
func vibrate(ms: int) -> void:
	if vibration:
		Input.vibrate_handheld(ms)

func apply_audio() -> void:
	_set_bus_volume(&"Master", volume_master)
	_set_bus_volume(&"Music", volume_music)
	_set_bus_volume(&"Sfx", volume_sfx)
	_set_bus_volume(&"Ui", volume_sfx)

func save_settings() -> void:
	var cfg: ConfigFile = ConfigFile.new()
	for key: StringName in KEYS:
		cfg.set_value(SECTION, key, get(key))
	var err: Error = cfg.save(PATH)
	if err != OK:
		push_warning("Settings: не удалось сохранить (%s)" % error_string(err))

func load_settings() -> void:
	var cfg: ConfigFile = ConfigFile.new()
	if cfg.load(PATH) != OK:
		return
	for key: StringName in KEYS:
		set(key, cfg.get_value(SECTION, key, get(key)))

func _set_bus_volume(bus: StringName, linear: float) -> void:
	var idx: int = AudioServer.get_bus_index(bus)
	if idx >= 0:
		AudioServer.set_bus_volume_db(idx, linear_to_db(clampf(linear, 0.0, 1.0)))

func _is_mobile_device() -> bool:
	return OS.has_feature("mobile") or OS.has_feature("web_android") or OS.has_feature("web_ios")
