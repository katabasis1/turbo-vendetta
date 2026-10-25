class_name DummyCar
extends Node3D
## Болванка машины для спайков: кузов, стекло, 4 колеса, стоп-сигнал с ореолом, блоб-тень.
## ≈ 2,9k треугольников и 8–9 draw calls (у настоящей машины будет 1 атлас + 1 свечение + 4 колеса).
## Генератор сцены — tools/agent/gen_spike_scenes.py.

@export var brake_light: GeometryInstance3D
@export var brake_glow: GeometryInstance3D


func _ready() -> void:
	assert(brake_light != null and brake_glow != null, "DummyCar: не назначены стоп-сигнал и ореол")
	set_brake(false)


## Стоп-сигнал через instance uniform: материал общий у всех машин (S-06).
func set_brake(on: bool) -> void:
	brake_light.set_instance_shader_parameter(&"emission_on", 1.0 if on else 0.0)
	brake_glow.visible = on
