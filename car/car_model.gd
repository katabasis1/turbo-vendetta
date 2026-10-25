class_name CarModel
extends Node3D
## Фасад визуальной модели машины (ARCHITECTURE §8.5): точки для эффектов, пивоты колёс и кузова, огни, материалы.
## Логики движения нет: колёса и кузов двигает CarVisualComponent, эффекты цепляет CarVfxComponent.
## Геометрия — экземпляры .glb из MeshForge. Их материалы нужны только для превью в редакторе; в игре здесь,
## в _ready(), ставится material_override: краска и колёса — cel_lit, огни — cel_emissive, оболочки `*_outline` —
## cel_outline (контур, S-19). Пути к узлам внутри .glb — обычные @export, без «редактируемых потомков».
## Сцены моделей пишет генератор tools/agent/gen_car_scenes.py.

@export var body_pivot: Node3D
@export var wheel_pivots: Array[Node3D] = []        # FL, FR, RL, RR
@export var tail_lights: Array[Marker3D] = []       # точки шлейфов
@export var rear_contacts: Array[Marker3D] = []     # точки дыма и следов
@export var nameplate: Marker3D
@export var brake_lights: Array[GeometryInstance3D] = []
@export var brake_glow: GeometryInstance3D

@export_group("Материалы")
@export var paint_material: Material
@export var paint_meshes: Array[GeometryInstance3D] = []
@export var wheel_material: Material
@export var wheel_meshes: Array[GeometryInstance3D] = []
@export var head_material: Material
@export var head_lights: Array[GeometryInstance3D] = []
@export var brake_material: Material
@export var outline_material: Material
@export var outline_meshes: Array[GeometryInstance3D] = []

var _flash := 0.0


func _ready() -> void:
	assert(body_pivot != null, "CarModel %s: не назначен body_pivot" % name)
	assert(wheel_pivots.size() == 4, "CarModel %s: нужно 4 пивота колёс (FL, FR, RL, RR)" % name)
	assert(paint_material != null and not paint_meshes.is_empty(), "CarModel %s: нет краски кузова" % name)
	_apply(paint_meshes, paint_material)
	_apply(wheel_meshes, wheel_material)
	_apply(head_lights, head_material)
	_apply(brake_lights, brake_material)
	_apply(outline_meshes, outline_material)
	set_brake(false)


func _apply(meshes: Array[GeometryInstance3D], material: Material) -> void:
	if material == null:
		assert(meshes.is_empty(), "CarModel %s: меши есть, материала нет" % name)
		return
	for m: GeometryInstance3D in meshes:
		assert(m != null, "CarModel %s: пустая ссылка в списке мешей" % name)
		m.material_override = material


## Стоп-сигнал: instance uniform `emission_on` у cel_emissive — материал общий у всех машин (S-06).
func set_brake(on: bool) -> void:
	for m: GeometryInstance3D in brake_lights:
		m.set_instance_shader_parameter(&"emission_on", 1.0 if on else 0.0)
	if brake_glow != null:
		brake_glow.visible = on


## Белое мигание кузова при ударе (0…1). Шейдерная часть — instance uniform в cel_lit после S-06 (этап 1.5);
## до неё значение только запоминается.
func set_flash(amount: float) -> void:
	_flash = clampf(amount, 0.0, 1.0)


func get_flash() -> float:
	return _flash


## Контур (оболочки `*_outline`) — вкл/выкл: настройка качества и сравнение «с контуром / без» (S-19).
func set_outline(on: bool) -> void:
	for m: GeometryInstance3D in outline_meshes:
		m.visible = on
