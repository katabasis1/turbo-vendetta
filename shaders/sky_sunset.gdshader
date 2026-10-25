// sky_sunset — небо «Закат»: 5 стопов градиента, диск солнца и ореол, статичное (без TIME) (STYLE_GUIDE §2.1, §3)
// Источник: свой (агент проекта «Турбовендетта»), 2026-10-25
// Автор: агент проекта
// Лицензия: своя (код проекта)
// Изменено: — (первая версия, этап 1.1, проверка в спайке S-14)
shader_type sky;
render_mode disable_fog;

global uniform vec3 sun_dir;
global uniform vec4 sun_color;
global uniform vec4 horizon_color;

// Стопы снизу вверх. Значения по умолчанию — «Закат», другие условия пишет TrackLightingComponent.
uniform vec4 coral : source_color = vec4(0.922, 0.482, 0.576, 1.0);   // #EB7B93
uniform vec4 middle : source_color = vec4(0.616, 0.267, 0.533, 1.0);  // #9D4488
uniform vec4 upper : source_color = vec4(0.275, 0.157, 0.431, 1.0);   // #46286E
uniform vec4 zenith : source_color = vec4(0.141, 0.086, 0.247, 1.0);  // #24163F
uniform vec4 below : source_color = vec4(0.478, 0.29, 0.525, 1.0);    // под горизонтом: #7A4A86
uniform float h_coral = 0.05;
uniform float h_middle = 0.16;
uniform float h_upper = 0.36;
uniform float h_zenith = 0.75;
uniform float sun_radius_deg = 3.2;
uniform float halo_radius_deg = 16.0;
uniform float halo_strength : hint_range(0.0, 1.0) = 0.35;

void sky() {
	float y = EYEDIR.y;
	vec3 c = horizon_color.rgb;
	c = mix(c, coral.rgb, smoothstep(0.0, h_coral, y));
	c = mix(c, middle.rgb, smoothstep(h_coral, h_middle, y));
	c = mix(c, upper.rgb, smoothstep(h_middle, h_upper, y));
	c = mix(c, zenith.rgb, smoothstep(h_upper, h_zenith, y));
	c = mix(c, below.rgb, 1.0 - smoothstep(-0.08, 0.0, y));
	float cos_a = dot(EYEDIR, normalize(sun_dir));
	float disc = smoothstep(cos(radians(sun_radius_deg + 0.15)), cos(radians(sun_radius_deg)), cos_a);
	float halo = smoothstep(cos(radians(halo_radius_deg)), 1.0, cos_a) * halo_strength;
	c = mix(c, sun_color.rgb, clamp(halo, 0.0, 1.0));
	c = mix(c, sun_color.rgb, disc * step(-0.02, y));
	COLOR = c;
}
