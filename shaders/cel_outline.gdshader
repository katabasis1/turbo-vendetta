// cel_outline — тушевой контур силуэта (D-018, STYLE_GUIDE v1.1 §3): вывернутая оболочка, сдвиг в экранной плоскости
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, спайк S-19). Меш — узел `<имя>_outline` из MeshForge: вершины сварены,
//   нормали сглажены (tools/meshforge/mf/outline.py), иначе оболочка рвётся на жёстких рёбрах.
//   Офлайн-двойник для превью — tools/meshforge/mf/preview.py ink(): та же схема, без тумана и спада толщины.
shader_type spatial;
render_mode unshaded, cull_front, depth_draw_opaque;

global uniform vec4 fog_color;
global uniform float fog_start;
global uniform float fog_end;

uniform vec4 ink_color : source_color = vec4(0.106, 0.063, 0.188, 1.0);  // #1B1030 `deepest`, не чёрный (§2)
uniform float width_px = 2.5;            // толщина при высоте кадра 720 px: машина 2,5, мир 2,0 (§3, допуск 1,5–3)
uniform float full_width_dist = 12.0;    // до этой дистанции до камеры (м) — полная толщина
uniform float min_width_scale : hint_range(0.0, 1.0) = 0.4;  // дальше тоньше, но не тоньше этой доли (не мерцает)
uniform float fog_amount : hint_range(0.0, 1.0) = 1.0;

void vertex() {
	// Глубина не сдвигается: оболочка видна только за краем силуэта и не лезет на лицевые грани.
	vec3 vp = (MODELVIEW_MATRIX * vec4(VERTEX, 1.0)).xyz;
	vec3 vn = normalize(MODELVIEW_NORMAL_MATRIX * NORMAL);
	vec4 c0 = PROJECTION_MATRIX * vec4(vp, 1.0);
	vec4 c1 = PROJECTION_MATRIX * vec4(vp + vn * 0.01, 1.0);
	if (c0.w > 0.0 && c1.w > 0.0) {
		vec2 d = (c1.xy / c1.w - c0.xy / c0.w) * VIEWPORT_SIZE;   // куда уходит нормаль на экране, в пикселях
		float dl = length(d);
		if (dl > 1e-6) {
			float k = clamp(full_width_dist / max(-vp.z, 0.001), min_width_scale, 1.0);
			float w = width_px * VIEWPORT_SIZE.y / 720.0 * k;
			c0.xy += d / dl * (w * 2.0 / VIEWPORT_SIZE) * c0.w;
		}
	}
	POSITION = c0;
}

void fragment() {
	float f = clamp((length(VERTEX) - fog_start) / max(fog_end - fog_start, 0.001), 0.0, 1.0) * fog_amount;
	ALBEDO = mix(ink_color.rgb, fog_color.rgb, f);
}
