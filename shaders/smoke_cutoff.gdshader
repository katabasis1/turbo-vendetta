// smoke_cutoff — дым дрифта: клуб в 2 тона с жёсткой границей (alpha-cutoff), растёт и тает (STYLE_GUIDE §2.4, §6)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-05)
shader_type spatial;
render_mode unshaded, cull_disabled, depth_draw_opaque, fog_disabled;

uniform vec4 smoke_light : source_color = vec4(0.835, 0.694, 0.733, 1.0);   // #D5B1BB
uniform vec4 smoke_shadow : source_color = vec4(0.639, 0.565, 0.753, 1.0);  // #A390C0
uniform vec2 light_from = vec2(-0.45, 0.75);   // откуда «светит» на клуб (в плоскости спрайта)

void vertex() {
	// поворот к камере + угол частицы (INSTANCE_CUSTOM.x), как BILLBOARD_PARTICLES у BaseMaterial3D
	mat4 mat_world = mat4(normalize(INV_VIEW_MATRIX[0]), normalize(INV_VIEW_MATRIX[1]), normalize(INV_VIEW_MATRIX[2]), MODEL_MATRIX[3]);
	mat_world = mat_world * mat4(vec4(cos(INSTANCE_CUSTOM.x), -sin(INSTANCE_CUSTOM.x), 0.0, 0.0), vec4(sin(INSTANCE_CUSTOM.x), cos(INSTANCE_CUSTOM.x), 0.0, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_MATRIX = VIEW_MATRIX * mat_world;
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0), vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0), vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0), vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	// COLOR.a из color_ramp = «жизнь»: клуб сжимается к концу и исчезает жёстко, без полупрозрачности
	float r = length(p + 0.12 * vec2(sin(p.y * 5.0), cos(p.x * 4.0)));
	if (r > COLOR.a) {
		discard;
	}
	float lit = step(0.0, dot(p, normalize(light_from)) + 0.18);
	ALBEDO = mix(smoke_shadow.rgb, smoke_light.rgb, lit) * COLOR.rgb;
}
