// glow_billboard — ореолы огней, фонарей и солнца: аддитивный спрайт к камере (вместо bloom, STYLE_GUIDE §3)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-02, S-12)
shader_type spatial;
render_mode unshaded, blend_add, depth_draw_never, cull_disabled, fog_disabled;

global uniform vec4 fog_color;
global uniform float fog_start;
global uniform float fog_end;

uniform vec4 glow_color : source_color = vec4(1.0, 0.784, 0.439, 1.0);   // #FFC870
uniform float intensity = 0.8;
uniform float core = 0.18;         // радиус яркого ядра (доля от радиуса спрайта)
uniform float fog_amount : hint_range(0.0, 1.0) = 0.5;

void vertex() {
	// поворот к камере (как BILLBOARD_ENABLED у BaseMaterial3D), масштаб узла сохраняется
	mat4 mat_world = mat4(normalize(INV_VIEW_MATRIX[0]), normalize(INV_VIEW_MATRIX[1]), normalize(INV_VIEW_MATRIX[2]), MODEL_MATRIX[3]);
	MODELVIEW_MATRIX = VIEW_MATRIX * mat_world;
	MODELVIEW_MATRIX = MODELVIEW_MATRIX * mat4(vec4(length(MODEL_MATRIX[0].xyz), 0.0, 0.0, 0.0), vec4(0.0, length(MODEL_MATRIX[1].xyz), 0.0, 0.0), vec4(0.0, 0.0, length(MODEL_MATRIX[2].xyz), 0.0), vec4(0.0, 0.0, 0.0, 1.0));
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	float d = length(UV * 2.0 - 1.0);
	float a = 1.0 - smoothstep(core, 1.0, d);
	a = a * a + (1.0 - smoothstep(core * 0.6, core, d)) * 0.5;
	float f = clamp((length(VERTEX) - fog_start) / max(fog_end - fog_start, 0.001), 0.0, 1.0) * fog_amount;
	ALBEDO = glow_color.rgb * intensity * a * (1.0 - f);
}
