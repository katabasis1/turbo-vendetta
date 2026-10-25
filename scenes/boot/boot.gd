extends Node
## Точка входа: SDK → язык → переход дальше.
## v0.0.1: в гонку (scenes/race/race.tscn, появится на 1.7). Сборка «Web (спайки)» (признак spikes)
## и запуск, пока гонки ещё нет, — в меню спайков scenes/dev/spikes/spike_menu.tscn. С этапа 5.2 переходы — SceneRouter.

const RACE_SCENE: String = "res://scenes/race/race.tscn"
const SPIKES_MENU: String = "res://scenes/dev/spikes/spike_menu.tscn"
const RU_LANGS: Array[String] = ["ru"]

func _ready() -> void:
	print("Turbo Vendetta · копия проекта: чекпоинт %s" % BuildInfo.STAMP)
	YandexSDK.init()
	TranslationServer.set_locale("ru" if RU_LANGS.has(YandexSDK.get_lang()) else "en")
	YandexSDK.loading_ready()
	get_tree().change_scene_to_file.call_deferred(_pick_target())

func _pick_target() -> String:
	if OS.has_feature("spikes") or not ResourceLoader.exists(RACE_SCENE):
		return SPIKES_MENU
	return RACE_SCENE
