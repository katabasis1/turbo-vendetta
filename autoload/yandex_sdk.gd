extends Node
## Единственная точка общения с SDK Яндекс Игр (AGENTS.md правило 5, ARCHITECTURE §5.3).
## До этапа 2.6 работает только МОК (и в редакторе, и в веб-сборке): те же методы и сигналы,
## реклама «показывается» за MOCK_AD_SECONDS, награда выдаётся. Мост к JS — platform/web/yandex_bridge.js (2.6).

signal initialized
signal pause_requested(reason: StringName)
signal resume_requested(reason: StringName)
signal ad_closed(kind: StringName, shown: bool)
signal reward_granted(reward_id: StringName)

## Сколько длится «реклама» мока. Проверка: пауза и звук возвращаются через 1 с. Крутить — только для тестов пауз.
const MOCK_AD_SECONDS: float = 1.0

var is_mock: bool = true
var is_initialized: bool = false
var is_gameplay_active: bool = false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS

## Вызывает boot.tscn один раз при запуске.
func init() -> void:
	if is_initialized:
		return
	is_initialized = true
	print_verbose("YandexSDK(mock): init")
	initialized.emit()

## LoadingAPI.ready(): игра загружена и готова к вводу.
func loading_ready() -> void:
	print_verbose("YandexSDK(mock): LoadingAPI.ready")

## GameplayAPI.start(). Вызывает только PauseService.
func gameplay_start() -> void:
	if is_gameplay_active:
		return
	is_gameplay_active = true
	print_verbose("YandexSDK(mock): GameplayAPI.start")

## GameplayAPI.stop(). Вызывает только PauseService.
func gameplay_stop() -> void:
	if not is_gameplay_active:
		return
	is_gameplay_active = false
	print_verbose("YandexSDK(mock): GameplayAPI.stop")

## Межстраничная реклама — только в паузе между заездами (этап 2.6).
func show_interstitial() -> void:
	await _mock_ad(&"interstitial")

## Реклама за награду. Награда — только бонус (правило 5).
func show_rewarded(reward_id: StringName) -> void:
	await _mock_ad(&"rewarded")
	reward_granted.emit(reward_id)

## "ru", "en" и т. д. Мок берёт язык системы.
func get_lang() -> String:
	return OS.get_locale_language()

## &"desktop", &"mobile", &"tablet", &"tv". Мок определяет по признакам сборки.
func get_device_type() -> StringName:
	if OS.has_feature("mobile") or OS.has_feature("web_android") or OS.has_feature("web_ios"):
		return &"mobile"
	return &"desktop"

func _mock_ad(kind: StringName) -> void:
	pause_requested.emit(&"ad")
	await get_tree().create_timer(MOCK_AD_SECONDS, true).timeout
	resume_requested.emit(&"ad")
	ad_closed.emit(kind, true)
