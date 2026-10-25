// trail — шлейф стоп-сигналов и искры: частица-квад, повёрнутый вдоль своей оси Y к камере (без рантайм-мешей, STYLE_GUIDE §6)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-05, S-15)
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, fog_disabled;

// Цвет и прозрачность — из COLOR частицы (color_ramp у CPUParticles3D: #FF5FA2 → #B5408E, α → 0).
uniform float edge_soft = 0.35;     // мягкость краёв поперёк ленты
uniform float energy = 1.0;

void vertex() {
	// ось Y частицы = направление скорости (particle_flag_align_y). Квад вращается вокруг неё к камере.
	vec3 center = MODEL_MATRIX[3].xyz;
	vec3 axis = MODEL_MATRIX[1].xyz;
	float len = max(length(axis), 0.0001);
	axis /= len;
	vec3 to_cam = normalize(INV_VIEW_MATRIX[3].xyz - center);
	vec3 side = cross(axis, to_cam);
	float side_len = length(side);
	side = mix(normalize(MODEL_MATRIX[0].xyz), side / max(side_len, 0.0001), step(0.0001, side_len));
	float wid = length(MODEL_MATRIX[0].xyz);
	vec3 nrm = cross(side, axis);
	mat4 mat_world = mat4(vec4(side * wid, 0.0), vec4(axis * len, 0.0), vec4(nrm, 0.0), vec4(center, 1.0));
	MODELVIEW_MATRIX = VIEW_MATRIX * mat_world;
	MODELVIEW_NORMAL_MATRIX = mat3(MODELVIEW_MATRIX);
}

void fragment() {
	float across = abs(UV.x * 2.0 - 1.0);
	float a = 1.0 - smoothstep(1.0 - edge_soft, 1.0, across);
	ALBEDO = COLOR.rgb * energy;
	ALPHA = COLOR.a * a;
}
