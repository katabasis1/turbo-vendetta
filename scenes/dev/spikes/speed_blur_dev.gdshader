// speed_blur_dev — радиальное размытие экрана для сравнения цены с линиями скорости (S-13). Только спайк, в игру не идёт.
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1)
shader_type canvas_item;

uniform sampler2D screen_tex : hint_screen_texture, filter_linear_mipmap;
uniform float strength = 0.05;
uniform float clear_radius = 0.35;

void fragment() {
	vec2 dir = SCREEN_UV - vec2(0.5);
	float k = smoothstep(clear_radius * 0.5, 0.75, length(dir));
	vec3 acc = vec3(0.0);
	for (int i = 0; i < 8; i++) {
		acc += texture(screen_tex, SCREEN_UV - dir * strength * k * float(i) / 7.0).rgb;
	}
	COLOR = vec4(acc / 8.0, 1.0);
}
