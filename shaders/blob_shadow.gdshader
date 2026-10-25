// blob_shadow — круглая тень под машиной #1B1030 α 0,65 (динамических теней нет, STYLE_GUIDE §3)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-02)
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_back, fog_disabled;

uniform vec4 shadow_color : source_color = vec4(0.106, 0.063, 0.188, 0.65);   // #1B1030
uniform float softness = 0.35;

void fragment() {
	vec2 p = UV * 2.0 - 1.0;
	float d = length(p);
	ALBEDO = shadow_color.rgb;
	ALPHA = shadow_color.a * (1.0 - smoothstep(1.0 - softness, 1.0, d));
}
