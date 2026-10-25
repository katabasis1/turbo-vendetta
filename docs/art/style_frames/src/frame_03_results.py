"""Кадр стиля №3 «Итоги заезда» — «Турбовендетта», D-012 «Аниме-аутран 90-х».
Мокап экрана, а не ассет игры. Фон рисуется 2D-слоями в палитре STYLE_GUIDE,
машина вырезана из рендера-заготовки MeshForge (_cars2.jpg, вид сзади 3/4).
Запуск: python3 frame_03_results.py docs/art/style_frames/wip/cars2.jpg docs/art/style_frames/frame_03_results.jpg
Шрифты: Noto Sans Display / Noto Sans (OFL 1.1), лежат в системе Computer.
"""
import sys, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy import ndimage

W, H, S = 1920, 1080, 2            # итог 1920x1080, рисуем в 2x и сжимаем (сглаживание)
FD = '/usr/share/fonts/truetype/noto/'
F_DISP = FD + 'NotoSansDisplay-SemiCondensedBlackItalic.ttf'
F_DISP_B = FD + 'NotoSansDisplay-SemiCondensedBoldItalic.ttf'
F_BODY = FD + 'NotoSans-SemiCondensedSemiBold.ttf'
F_BODY_B = FD + 'NotoSans-SemiCondensedBold.ttf'

def hx(h, a=255):
    h = h.lstrip('#'); return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)

# ---- палитра (совпадает с STYLE_GUIDE §2) ----
P = dict(
    sky_zenith='#24163F', sky_high='#46286E', sky_mid='#9D4488', sky_low='#EB7B93', sky_horizon='#F6B26B',
    sun='#FFF1D6', cloud_body='#6A3A80', cloud_lit='#F3A0A8',
    city_far='#7A4A86', city_near='#3A2260', window='#FFC870', window_pink='#FF8FC8', window_cyan='#8FE8FF',
    water='#5A2F6E', concrete_lit='#A390C0', concrete_mid='#715194', concrete_shadow='#402A69',
    asphalt_near='#2E1D47', asphalt_far='#6A3F7C', lane='#EEC2E4', ink='#130C27', shadow_ink='#1B1030',
    panel='#1B1433', panel_hi='#2C2050', text='#FCF7F9', text_dim='#BCA4D1',
    coral='#F13858', cyan='#54DFFA', amber='#F4AC5A', tail='#FF4F6E', lamp='#FFC870')

def lerp(a, b, t): return a + (b - a) * t

def gradient(stops, h):
    """stops: [(t, '#hex')] -> массив h x 3 float"""
    ys = np.linspace(0, 1, h)
    out = np.zeros((h, 3), np.float32)
    for i in range(3):
        out[:, i] = np.interp(ys, [s[0] for s in stops], [hx(s[1])[i] for s in stops])
    return out

def glow(size, r, color, strength=1.0, falloff=2.2):
    """Радиальное свечение как RGBA-спрайт (свечение рисуем, а не считаем)."""
    n = int(size)
    y, x = np.mgrid[0:n, 0:n] - (n - 1) / 2
    d = np.sqrt(x * x + y * y) / r
    a = np.clip(1 - d, 0, 1) ** falloff * strength
    c = hx(color)
    arr = np.zeros((n, n, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = c[0], c[1], c[2]
    arr[..., 3] = (np.clip(a, 0, 1) * 255).astype(np.uint8)
    return Image.fromarray(arr, 'RGBA')

def skew_poly(x, y, w, h, k=math.tan(math.radians(12))):
    """Параллелограмм с наклоном 12° (язык панелей UI). Координаты 1x."""
    dx = h * k
    return [((x + dx) * S, y * S), ((x + w + dx) * S, y * S), ((x + w) * S, (y + h) * S), (x * S, (y + h) * S)]

def font(path, size): return ImageFont.truetype(path, int(size * S))

def text(d, xy, s, f, fill, anchor='la'):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)

def star(cx, cy, r, inner=0.45):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * inner
        pts.append(((cx + rr * math.cos(a)) * S, (cy + rr * math.sin(a)) * S))
    return pts

def main(cars_path, out_path):
    random.seed(7)
    HOR = 600   # линия горизонта (1x)
    # ---------- 1. небо: рисованный градиент 5 ступеней ----------
    sky = gradient([(0, P['sky_zenith']), (0.30, P['sky_high']), (0.62, P['sky_mid']), (0.86, P['sky_low']), (1.0, P['sky_horizon'])], HOR)
    bg = np.zeros((H, W, 3), np.float32)
    bg[:HOR] = sky[:, None, :]
    # вода залива под горизонтом
    wat = gradient([(0, '#C0607E'), (0.25, P['water']), (1, '#2A1840')], H - HOR)
    bg[HOR:] = wat[:, None, :]
    img = Image.fromarray(bg.clip(0, 255).astype(np.uint8), 'RGB').resize((W * S, H * S), Image.BICUBIC).convert('RGBA')
    d = ImageDraw.Draw(img)

    # ---------- 2. солнце + ореол (без полос — классический набор запрещён) ----------
    SUNX, SUNY, SUNR = 1110, 552, 92
    for r, col, st in [(520, P['sky_low'], 0.55), (300, P['sky_horizon'], 0.6), (170, P['sun'], 0.7)]:
        g = glow(r * 2 * S, r * S, col, st)
        img.alpha_composite(g, (int((SUNX - r) * S), int((SUNY - r) * S)))
    d.ellipse([(SUNX - SUNR) * S, (SUNY - SUNR) * S, (SUNX + SUNR) * S, (SUNY + SUNR) * S], fill=hx(P['sun']))

    # ---------- 3. облака-ленты: 2 тона, плоско ----------
    for (cx, cy, w, h) in [(380, 210, 620, 26), (900, 150, 520, 18), (1560, 250, 700, 30), (1180, 330, 460, 16), (240, 380, 420, 14), (1720, 420, 380, 12), (700, 440, 300, 10)]:
        d.rounded_rectangle([(cx - w / 2) * S, (cy - h / 2) * S, (cx + w / 2) * S, (cy + h / 2) * S], radius=h * S / 2, fill=hx(P['cloud_body'], 235))
        d.rounded_rectangle([(cx - w / 2 + 30) * S, (cy + h * 0.15) * S, (cx + w / 2 - 10) * S, (cy + h / 2) * S], radius=h * S / 4, fill=hx(P['cloud_lit'], 230))

    # ---------- 4. город: дальний (воздушная перспектива) и ближний слой с окнами ----------
    x = -10
    while x < W:
        w = random.randint(26, 70); h = random.randint(20, 120)
        d.rectangle([x * S, (HOR - h) * S, (x + w) * S, HOR * S], fill=hx(P['city_far']))
        x += w + random.randint(-6, 4)
    x = -10
    wins = []
    while x < W:
        w = random.randint(34, 96); h = random.randint(40, 230)
        if 960 < x < 1250: h = min(h, 64)          # оставить солнце открытым
        d.rectangle([x * S, (HOR - h) * S, (x + w) * S, HOR * S], fill=hx(P['city_near']))
        for wy in range(HOR - h + 8, HOR - 6, 12):
            for wx in range(x + 6, x + w - 6, 10):
                r = random.random()
                if r < 0.22: wins.append((wx, wy, P['window']))
                elif r < 0.25: wins.append((wx, wy, P['window_pink']))
                elif r < 0.265: wins.append((wx, wy, P['window_cyan']))
        x += w + random.randint(0, 10)
    for wx, wy, c in wins:
        d.rectangle([wx * S, wy * S, (wx + 4) * S, (wy + 6) * S], fill=hx(c))
    # отражение солнца в воде: ломаные штрихи
    for i in range(14):
        yy = HOR + 8 + i * 7
        ww = 160 - i * 9 + random.randint(-12, 12)
        d.rectangle([(SUNX - ww / 2 + random.randint(-14, 14)) * S, yy * S, (SUNX + ww / 2) * S, (yy + 2.5) * S], fill=hx('#FFD9A8', 200 - i * 10))

    # ---------- 5. эстакада: дорога в перспективе, отбойник, фонари ----------
    VPX, VPY = 1180, 640
    road = [(VPX - 30, VPY), (VPX + 70, VPY), (W + 900, H), (180, H)]
    road_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(road_img)
    rd.polygon([(px * S, py * S) for px, py in road], fill=(255, 255, 255, 255))
    rg = gradient([(0, P['asphalt_far']), (0.25, '#4A2D66'), (1, P['asphalt_near'])], H - VPY)
    rgarr = np.zeros((H * S, W * S, 3), np.uint8)
    rgfull = np.repeat(rg, S, axis=0).astype(np.uint8)
    rgarr[VPY * S:] = rgfull[:, None, :]
    road_col = Image.fromarray(rgarr, 'RGB').convert('RGBA'); road_col.putalpha(road_img.getchannel('A'))
    img.alpha_composite(road_col); del rgarr, road_col, road_img
    d = ImageDraw.Draw(img)
    # разметка
    for i in range(1, 12):
        t0 = (i / 12) ** 1.8; t1 = ((i + 0.45) / 12) ** 1.8
        def pt(t, off): return (lerp(VPX + 20, 1050 + off, t), lerp(VPY, H, t))
        a0, a1 = pt(t0, 0), pt(t1, 0)
        wdt = lerp(1, 12, t0)
        d.polygon([((a0[0] - wdt) * S, a0[1] * S), ((a0[0] + wdt) * S, a0[1] * S), ((a1[0] + wdt * 1.4) * S, a1[1] * S), ((a1[0] - wdt * 1.4) * S, a1[1] * S)], fill=hx(P['lane'], 200))
    # отбойник слева: верх освещён, бок в тени
    d.polygon([(VPX - 30) * S, VPY * S, (VPX - 30) * S, (VPY - 8) * S, 0, (H - 300) * S, 0, (H - 230) * S], fill=hx(P['concrete_lit']))
    d.polygon([(VPX - 30) * S, VPY * S, 0, (H - 230) * S, 0, (H - 130) * S, (VPX - 32) * S, (VPY + 4) * S], fill=hx(P['concrete_shadow']))
    # фонари с натриевыми лампами (ореол — спрайт)
    for t in [0.08, 0.2, 0.38, 0.62, 0.95]:
        bx = lerp(VPX - 40, -60, t); by = lerp(VPY - 6, H - 270, t); hgt = lerp(30, 520, t)
        wdt = lerp(1.5, 12, t)
        d.rectangle([(bx - wdt / 2) * S, (by - hgt) * S, (bx + wdt / 2) * S, by * S], fill=hx(P['concrete_shadow']))
        arm = lerp(10, 150, t)
        d.line([bx * S, (by - hgt) * S, (bx + arm) * S, (by - hgt - arm * 0.12) * S], fill=hx(P['concrete_shadow']), width=int(wdt * S))
        lr = lerp(14, 160, t)
        img.alpha_composite(glow(lr * 2 * S, lr * S, P['lamp'], 0.75), (int((bx + arm - lr) * S), int((by - hgt - arm * 0.12 - lr) * S)))
        d = ImageDraw.Draw(img)
        d.ellipse([(bx + arm - wdt) * S, (by - hgt - arm * 0.12 - wdt * 0.5) * S, (bx + arm + wdt) * S, (by - hgt - arm * 0.12 + wdt * 0.5) * S], fill=hx('#FFF1D6'))
    # верхняя эстакада, пересекающая кадр (силуэт японских развязок)
    deck = [(1460, 0), (W, 0), (W, 200), (1640, 120)]
    d.polygon([(px * S, py * S) for px, py in deck], fill=hx(P['concrete_mid']))
    d.polygon([(1640 * S, 120 * S), (W * S, 200 * S), (W * S, 236 * S), (1650 * S, 146 * S)], fill=hx(P['concrete_shadow']))
    for px in [1720, 1850]:
        d.rectangle([px * S, 150 * S, (px + 46) * S, HOR * S], fill=hx(P['concrete_shadow']))
        d.rectangle([px * S, 150 * S, (px + 14) * S, HOR * S], fill=hx(P['concrete_mid']))

    # ---------- 6. машина игрока: вырезка из рендера-заготовки ----------
    im = np.asarray(Image.open(cars_path).convert('RGB')).astype(int)
    q = im[0:400, 0:640]
    dist = np.min([np.abs(q - np.array(b)).max(-1) for b in ([43, 32, 72], [61, 54, 96])], axis=0)
    lab, _ = ndimage.label(dist <= 4)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    fg = ~np.isin(lab, list(border))
    fg = ndimage.binary_opening(fg, iterations=2)
    l2, n2 = ndimage.label(fg); sizes = ndimage.sum(fg, l2, range(1, n2 + 1))
    fg = ndimage.binary_fill_holes(l2 == (np.argmax(sizes) + 1))
    fg = ndimage.binary_erosion(fg, iterations=1)
    ys, xs = np.where(fg)
    alpha = (np.clip(ndimage.gaussian_filter(fg.astype(float), 0.6), 0, 1) * 255).astype(np.uint8)
    car = Image.fromarray(np.dstack([q.astype(np.uint8), alpha]), 'RGBA').crop((xs.min() - 2, ys.min() - 2, xs.max() + 3, ys.max() + 3))
    k0 = car.width
    cw = 470; ch = int(car.height * cw / car.width); kk = cw / k0
    car = car.resize((cw * S, ch * S), Image.LANCZOS)
    CX, CY = 880, 676
    # блоб-тень (динамических теней нет)
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); sd = ImageDraw.Draw(sh)
    sd.ellipse([(CX + 20) * S, (CY + ch - 70) * S, (CX + cw - 10) * S, (CY + ch + 26) * S], fill=hx(P['shadow_ink'], 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(12 * S))); del sh
    # отсвет стоп-сигналов на асфальте
    for tx in [CX + 325 * kk, CX + 420 * kk]:
        img.alpha_composite(glow(200 * S, 100 * S, P['tail'], 0.45), (int((tx - 100) * S), int((CY + ch - 90) * S)))
    img.alpha_composite(car, (CX * S, CY * S))
    for tx, ty in [(CX + 322 * kk, CY + 110 * kk), (CX + 417 * kk, CY + 108 * kk)]:
        img.alpha_composite(glow(90 * S, 45 * S, P['tail'], 0.7, 1.6), (int((tx - 45) * S), int((ty - 45) * S)))
    d = ImageDraw.Draw(img)

    # ---------- 7. затемнение под UI слева ----------
    sh = np.zeros((H, W), np.float32)
    xs_ = np.linspace(0, 1, W)
    sh[:] = np.clip(1 - xs_ / 0.52, 0, 1)[None, :] ** 1.3 * 0.78
    dim = Image.new('RGBA', (W, H), hx(P['ink'])); dim.putalpha(Image.fromarray((sh * 255).astype(np.uint8)))
    img.alpha_composite(dim.resize(img.size, Image.BILINEAR)); d = ImageDraw.Draw(img)

    # ---------- 8. UI ----------
    # заголовок
    d.polygon(skew_poly(60, 52, 230, 58), fill=hx(P['coral']))
    text(d, (92, 81), 'ФИНИШ', font(F_DISP, 40), hx(P['text']), 'lm')
    text(d, (320, 72), 'ЧЁРНЫЙ СПИСОК · ЛИГА 1 · ГОНКА 4', font(F_BODY_B, 22), hx(P['text_dim']), 'lm')
    text(d, (320, 98), 'Закатная эстакада · 3 круга', font(F_BODY, 22), hx(P['text']), 'lm')
    # место
    text(d, (64, 340), '1', font(F_DISP, 300), hx(P['text']), 'ls')
    text(d, (250, 210), 'МЕСТО', font(F_DISP, 40), hx(P['amber']), 'ls')
    text(d, (250, 262), 'из 8', font(F_DISP_B, 40), hx(P['text_dim']), 'ls')
    d.polygon(skew_poly(250, 282, 330, 46), fill=hx(P['amber']))
    text(d, (272, 305), 'БОСС ПОВЕРЖЕН', font(F_DISP, 30), hx(P['ink']), 'lm')
    # время
    text(d, (70, 395), 'ВРЕМЯ', font(F_BODY_B, 22), hx(P['text_dim']), 'ls')
    text(d, (70, 450), '1:28.47', font(F_DISP, 58), hx(P['text']), 'ls')
    text(d, (330, 395), 'ЛУЧШИЙ КРУГ', font(F_BODY_B, 22), hx(P['text_dim']), 'ls')
    text(d, (330, 450), '0:29.12', font(F_DISP, 58), hx(P['text']), 'ls')
    d.polygon(skew_poly(552, 414, 120, 34), fill=hx(P['cyan']))
    text(d, (568, 431), 'РЕКОРД', font(F_DISP, 22), hx(P['ink']), 'lm')
    # звёзды
    for i, (cap, on) in enumerate([('Финиш', True), ('Стиль 10 000', True), ('Без урона', False)]):
        sx = 100 + i * 250
        if on:
            d.polygon(star(sx, 510, 34), fill=hx(P['amber']))
            d.polygon(star(sx - 3, 506, 18), fill=hx('#FFE0A8'))
        else:
            d.polygon(star(sx, 510, 34), fill=hx(P['panel_hi']), outline=hx(P['text_dim']), width=3 * S)
        text(d, (sx + 44, 512), cap, font(F_BODY_B, 24), hx(P['text'] if on else P['text_dim']), 'lm')
    # таблица мест
    rows = [('1', 'Вы · Хаятэ', None, '1:28.47', True), ('2', 'Кагэ', ('БОСС', 'coral'), '+0.84', False),
            ('3', 'Лена_К', ('ПРИЗРАК', 'cyan'), '+2.10', False), ('4', 'Райдзин', None, '+4.55', False),
            ('5', 'Миша_RX', ('ПРИЗРАК', 'cyan'), '+6.02', False), ('—', 'Буря', ('ВЫБЫЛ', 'coral'), 'таран · 2 круг', False)]
    y0 = 580
    for i, (pos, name, tag, tm, me) in enumerate(rows):
        y = y0 + i * 70
        x = 60 - i * 70 * math.tan(math.radians(12)) * 0  # ровная колонка, наклон только у плашек
        d.polygon(skew_poly(60, y, 740, 60), fill=hx(P['panel_hi'] if me else P['panel'], 240 if me else 225))
        if me: d.polygon(skew_poly(60, y, 14, 60), fill=hx(P['coral']))
        text(d, (106, y + 31), pos, font(F_DISP, 34), hx(P['amber'] if pos == '1' else P['text']), 'mm')
        text(d, (150, y + 31), name, font(F_BODY_B, 28), hx(P['text']), 'lm')
        if tag:
            nf = font(F_BODY_B, 28); tw = d.textlength(name, font=nf) / S
            col = P[tag[1]]
            tf = font(F_DISP, 18); tl = d.textlength(tag[0], font=tf) / S
            if tag[0] == 'ВЫБЫЛ':
                d.polygon(skew_poly(150 + tw + 16, y + 17, tl + 26, 28), fill=hx(col))
                text(d, (150 + tw + 32, y + 31), tag[0], font(F_DISP, 18), hx(P['text']), 'lm')
            else:
                d.polygon(skew_poly(150 + tw + 16, y + 17, tl + 26, 28), outline=hx(col), width=2 * S)
                text(d, (150 + tw + 32, y + 31), tag[0], font(F_DISP, 18), hx(col), 'lm')
        text(d, (770, y + 31), tm, font(F_DISP_B if tm[0] != 'т' else F_BODY, 30 if tm[0] != 'т' else 22), hx(P['text'] if me else P['text_dim']), 'rm')

    # правая колонка: стиль и награды
    RX = 1350
    d.polygon(skew_poly(RX, 280, 510, 320), fill=hx(P['panel'], 230))
    text(d, (RX + 40, 326), 'СТИЛЬ', font(F_BODY_B, 22), hx(P['text_dim']), 'ls')
    text(d, (RX + 40, 384), '12 840', font(F_DISP, 60), hx(P['amber']), 'ls')
    text(d, (RX + 300, 384), '×4', font(F_DISP, 48), hx(P['amber']), 'ls')
    text(d, (RX + 362, 384), 'макс. комбо', font(F_BODY, 20), hx(P['text_dim']), 'ls')
    for i, (k, v) in enumerate([('Дрифт', '6 200'), ('Тараны ×3', '3 000'), ('Выбывание', '2 000'), ('Впритирку', '1 640')]):
        yy = 420 + i * 34
        text(d, (RX + 44, yy), k, font(F_BODY, 22), hx(P['text']), 'lm')
        text(d, (RX + 470, yy), v, font(F_DISP_B, 24), hx(P['text']), 'rm')
    # награды
    d.polygon(skew_poly(RX - 20, 630, 530, 150), fill=hx(P['panel'], 225))
    d.ellipse([(RX + 30) * S, 652 * S, (RX + 74) * S, 696 * S], fill=hx(P['amber']))
    d.ellipse([(RX + 40) * S, 662 * S, (RX + 64) * S, 686 * S], outline=hx('#B86A2A'), width=3 * S)
    text(d, (RX + 88, 674), '+1 250', font(F_DISP, 44), hx(P['text']), 'lm')
    text(d, (RX + 260, 676), 'монет', font(F_BODY, 22), hx(P['text_dim']), 'lm')
    text(d, (RX + 30, 728), 'МАСТЕРСТВО · ХАЯТЭ', font(F_BODY_B, 20), hx(P['text_dim']), 'lm')
    text(d, (RX + 470, 728), '8', font(F_DISP, 26), hx(P['amber']), 'rm')
    d.polygon([((RX + 428) * S, 720 * S), ((RX + 444) * S, 728 * S), ((RX + 428) * S, 736 * S)], fill=hx(P['amber']))
    text(d, (RX + 420, 728), '7', font(F_DISP, 26), hx(P['text_dim']), 'rm')
    for i in range(10):
        bx = RX + 30 + i * 44
        fill = P['amber'] if i < 7 else (P['coral'] if i == 7 else P['panel_hi'])
        d.polygon(skew_poly(bx, 748, 38, 14), fill=hx(fill))
    # кнопки: rewarded — только бонус
    d.polygon(skew_poly(RX + 40, 800, 470, 64), outline=hx(P['cyan']), width=3 * S, fill=hx(P['ink'], 200))
    d.polygon([((RX + 72) * S, 816 * S), ((RX + 72) * S, 848 * S), ((RX + 98) * S, 832 * S)], fill=hx(P['cyan']))
    text(d, (RX + 116, 833), '×2 НАГРАДА ЗА РЕКЛАМУ', font(F_DISP, 28), hx(P['cyan']), 'lm')
    # главная кнопка: реванш в 1 касание
    d.polygon(skew_poly(1430, 900, 430, 110), fill=hx(P['coral']))
    text(d, (1660, 956), 'ЕЩЁ РАЗ', font(F_DISP, 60), hx(P['text']), 'mm')
    d.rounded_rectangle([1806 * S, 916 * S, 1840 * S, 950 * S], radius=4 * S, fill=hx(P['text']))
    text(d, (1823, 934), 'R', font(F_BODY_B, 20), hx(P['ink']), 'mm')
    d.polygon(skew_poly(1030, 916, 360, 94), fill=hx(P['panel'], 235))
    text(d, (1180, 963), 'ДАЛЬШЕ', font(F_DISP, 44), hx(P['text']), 'mm')
    d.rounded_rectangle([1306 * S, 948 * S, 1376 * S, 976 * S], radius=4 * S, fill=hx(P['text_dim']))
    text(d, (1341, 962), 'ENTER', font(F_BODY_B, 15), hx(P['ink']), 'mm')

    out = img.convert('RGB').resize((W, H), Image.LANCZOS)
    out.save(out_path, quality=92)
    print('saved', out_path, out.size)

if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
