// cel_lit — мир и машины: ручной cel-свет по глобальному sun_dir, 3 ступени, тень к shadow_tint, кант, блик-полоса, туман (STYLE_GUIDE §3)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-01, S-02)
shader_type spatial;
render_mode unshaded, cull_back, depth_draw_opaque;

// Глобальные uniform — [shader_globals] в project.godot, пишет TrackLightingComponent (S-01).
global uniform vec3 sun_dir;
global uniform vec4 sun_color;
global uniform vec4 shadow_tint;
global uniform vec4 rim_color;
global uniform vec4 fog_color;
global uniform float fog_start;
global uniform float fog_end;

// Три тона одного цвета (STYLE_GUIDE §2.2–2.3): свет / полутон / тень. Атлас умножается на тон.
uniform vec4 tone_light : source_color = vec4(1.0);
uniform vec4 tone_mid : source_color = vec4(0.72, 0.72, 0.72, 1.0);
uniform vec4 tone_shadow : source_color = vec4(0.45, 0.45, 0.45, 1.0);
uniform sampler2D albedo_tex : source_color, hint_default_white, filter_linear_mipmap;
uniform bool use_vertex_color = false;          // AO в цветах вершин (MeshForge)
uniform float shadow_tint_mix : hint_range(0.0, 1.0) = 0.35;
uniform float th_light = 0.55;                  // порог «свет»
uniform float th_mid = 0.05;                    // порог «полутон»
uniform float edge_soft = 0.03;                 // мягкость края ступени (0,06 на телефоне — если «лесенка»)
uniform float rim_strength : hint_range(0.0, 1.0) = 0.0;   // 0,35 — только машины
uniform float rim_threshold = 0.6;
uniform float spec_strength : hint_range(0.0, 1.0) = 0.0;  // аниме-блик, только машины
uniform float spec_threshold = 0.93;
uniform float fog_amount : hint_range(0.0, 1.0) = 1.0;

// Белое мигание при ударе — instance uniform, но только после S-06 (если он провалится, сломался бы весь мир).

varying vec3 v_world_normal;

void vertex() {
	v_world_normal = (MODEL_MATRIX * vec4(NORMAL, 0.0)).xyz;
}

void fragment() {
	vec3 n = normalize(v_world_normal);
	vec3 l = normalize(sun_dir);
	float ndl = dot(n, l);
	float to_light = smoothstep(th_light - edge_soft, th_light + edge_soft, ndl);
	float to_mid = smoothstep(th_mid - edge_soft, th_mid + edge_soft, ndl);
	vec3 c_light = tone_light.rgb * sun_color.rgb;
	vec3 c_mid = tone_mid.rgb * mix(vec3(1.0), sun_color.rgb, 0.5);
	vec3 c_shadow = mix(tone_shadow.rgb, shadow_tint.rgb, shadow_tint_mix);
	vec3 c = mix(c_shadow, mix(c_mid, c_light, to_light), to_mid);
	c *= texture(albedo_tex, UV).rgb;
	if (use_vertex_color) {
		c *= COLOR.rgb;
	}
	// кант: ступенька френеля
	float fres = 1.0 - clamp(dot(normalize(NORMAL), VIEW), 0.0, 1.0);
	c = mix(c, rim_color.rgb, smoothstep(rim_threshold - 0.02, rim_threshold + 0.02, fres) * rim_strength);
	// блик: одна жёсткая полоса
	vec3 l_view = normalize((VIEW_MATRIX * vec4(l, 0.0)).xyz);
	float spec = dot(normalize(NORMAL), normalize(l_view + VIEW));
	c += vec3(smoothstep(spec_threshold - 0.005, spec_threshold + 0.005, spec) * spec_strength);
	// туман по расстоянию до камеры
	float f = clamp((length(VERTEX) - fog_start) / max(fog_end - fog_start, 0.001), 0.0, 1.0) * fog_amount;
	ALBEDO = mix(c, fog_color.rgb, f);
}
