// cel_emissive — окна, фонари, стоп-сигналы, фары: ровный свет без затенения; вкл/выкл через instance uniform (S-06)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-02, S-06)
shader_type spatial;
render_mode unshaded, cull_back, depth_draw_opaque;

global uniform vec4 fog_color;
global uniform float fog_start;
global uniform float fog_end;

uniform vec4 color_on : source_color = vec4(1.0, 0.31, 0.43, 1.0);   // #FF4F6E стоп-сигнал
uniform vec4 color_off : source_color = vec4(0.36, 0.12, 0.2, 1.0);  // погашенный огонь
uniform sampler2D emission_tex : source_color, hint_default_white, filter_linear_mipmap;
uniform float energy = 1.0;          // ночью окна ×1,5 (STYLE_GUIDE §2.6)
uniform float fog_amount : hint_range(0.0, 1.0) = 0.6;   // огни тонут в тумане слабее мира

// 1 — горит, 0 — погашен. Своё значение у каждого экземпляра, материал общий (S-06).
instance uniform float emission_on = 1.0;

void fragment() {
	float on = clamp(emission_on, 0.0, 1.0);
	vec3 c = mix(color_off.rgb, color_on.rgb * energy, on) * texture(emission_tex, UV).rgb;
	float f = clamp((length(VERTEX) - fog_start) / max(fog_end - fog_start, 0.001), 0.0, 1.0) * fog_amount;
	ALBEDO = mix(c, fog_color.rgb, f);
}
