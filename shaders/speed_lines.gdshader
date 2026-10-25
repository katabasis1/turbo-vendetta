// speed_lines — манга-линии скорости: canvas_item по UV и времени, без чтения экрана, центр 35 % чистый (STYLE_GUIDE §6)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-13)
shader_type canvas_item;

uniform float intensity : hint_range(0.0, 1.0) = 0.25;   // скорость 0,25; таран 1,0 (α линий 0,7)
uniform vec4 line_color : source_color = vec4(1.0, 1.0, 1.0, 0.7);
uniform float clear_radius = 0.35;     // чистый центр (доля высоты экрана)
uniform float line_count = 96.0;
uniform float flicker_hz = 12.0;

float hash(float n) {
	return fract(sin(n * 12.9898) * 43758.5453);
}

void fragment() {
	vec2 px = 1.0 / SCREEN_PIXEL_SIZE;
	vec2 p = UV - 0.5;
	p.x *= px.x / px.y;
	float r = length(p);
	float cell = (atan(p.y, p.x) / 6.2831853 + 0.5) * line_count;
	float id = floor(cell);
	float frame = floor(TIME * flicker_hz);
	float h = hash(id + frame * 0.731);
	float local = abs(fract(cell) - 0.5);
	float thick = mix(0.06, 0.3, h) * smoothstep(clear_radius * 0.5, 0.9, r);
	float line = 1.0 - smoothstep(thick * 0.5, thick, local);
	float start = clear_radius * 0.5 + h * 0.22;
	float radial = smoothstep(start, start + 0.06, r);
	float on = step(0.45, hash(id * 3.17 + frame));
	COLOR = vec4(line_color.rgb, line_color.a * intensity * line * radial * on);
}
