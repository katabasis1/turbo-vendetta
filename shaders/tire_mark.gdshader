// tire_mark — след шины: плоский квад на асфальте #1B1030 α 0,5, гаснет за 4 с; без Decal (STYLE_GUIDE §6)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: 2026-10-25 (1.1, D4) — режим wheel_pair: одна частица рисует обе полосы задних колёс
//   (один излучатель на машину: ровный шаг частиц без случайного выбора точки, вдвое меньше частиц и draw calls)
shader_type spatial;
render_mode unshaded, blend_mix, depth_draw_never, cull_disabled, fog_disabled;

uniform vec4 mark_color : source_color = vec4(0.106, 0.063, 0.188, 0.5);   // #1B1030
uniform float edge_soft = 0.3;
uniform bool wheel_pair = false;    // false — одна полоса во всю ширину квада; true — две полосы у краёв
uniform float stripe = 0.15;        // wheel_pair: полуширина полосы шины, доля полуширины квада

void fragment() {
	float across = abs(UV.x * 2.0 - 1.0);   // 0 — середина квада, 1 — край
	if (wheel_pair) {
		across = abs(across - (1.0 - stripe)) / stripe;   // 0 — середина полосы шины, ≥ 1 — вне полосы
	}
	ALBEDO = mark_color.rgb;
	ALPHA = mark_color.a * COLOR.a * (1.0 - smoothstep(1.0 - edge_soft, 1.0, across));
}
