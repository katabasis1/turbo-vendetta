#!/usr/bin/env python3
"""car_01 v2: подложки с метрической сеткой (для MeshForge) и сводный лист для утверждения.
Запуск из корня репозитория: python3 docs/art/cars/car_01/src/make_board.py
Вход: docs/art/cars/car_01/ref/*.png (сгенерированы, промпты — prompts.md).
Выход: underlay/car_01_side_grid.png, underlay/car_01_front_rear_grid.png, car_01_board.jpg.
Калибровка ortho-листа (1536×864) измерена 2026-10-25 (Hough по ободам, маска по фону #DFD7F9):
бок — нос x=84, корма x=1395 (без крыла), земля y=436, длина 4,40 м → 297,95 px/м;
оси (центры колёс) x=402.6 и 1162.2, y≈341; перёд — рамка x 24..428 (с зеркалами 1,98 м), корма — x 458..887 (по аркам 1,92 м), земля y=754.
"""
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REF = os.path.join(ROOT, 'ref')
UND = os.path.join(ROOT, 'underlay')
F = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'        # есть стрелки, ≤, ≈
FB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
INK = (27, 16, 48)          # #1B1030 — контур (D-018)
CORAL = (232, 54, 79)       # #E8364F
CYAN = (84, 223, 250)       # #54DFFA
PANEL = (27, 20, 51)        # #1B1433
TXT = (252, 247, 249)       # #FCF7F9
TXT2 = (188, 164, 209)      # #BCA4D1

ORTHO = os.path.join(REF, 'car_01_ref_03_ortho.png')
S_NOSE, S_TAIL, S_GROUND = 84, 1395, 436
S_PPM = (S_TAIL - S_NOSE) / 4.40
AXLES_PX = (402.6, 1162.2)


def font(sz, bold=False):
    return ImageFont.truetype(FB if bold else F, sz)


def grid(d, x0, ground, ppm, xmin, xmax, ymax, label_x=True, origin_label='нос'):
    """Сетка: x0 — пиксель нуля по X, ground — земля; шаг 0,1 м тонко, 0,5 м толще."""
    f = font(13)
    k = int(round(xmin * 10))
    while k <= int(round(xmax * 10)):
        x = x0 + k / 10 * ppm
        w, c = (2, (113, 81, 148)) if k % 5 == 0 else (1, (190, 175, 225))
        d.line([(x, ground - ymax * ppm), (x, ground + 6)], fill=c, width=w)
        if label_x and k % 5 == 0:
            d.text((x + 3, ground + 6), f'{k/10:.1f}', fill=INK, font=f)
        k += 1
    for j in range(0, int(ymax * 10) + 1):
        y = ground - j / 10 * ppm
        w, c = (2, (113, 81, 148)) if j % 5 == 0 else (1, (190, 175, 225))
        d.line([(x0 + xmin * ppm, y), (x0 + xmax * ppm, y)], fill=c, width=w)
        if j % 5 == 0:
            d.text((x0 + xmin * ppm + 3, y - 17), f'{j/10:.1f} м', fill=INK, font=f)


def side_underlay():
    src = Image.open(ORTHO).convert('RGBA')
    crop = (40, 40, 1460, 480)
    base = src.crop(crop)
    lay = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    x0, g = S_NOSE - crop[0], S_GROUND - crop[1]
    grid(d, x0, g, S_PPM, -0.1, 4.7, 1.3)
    f = font(15, True)
    for i, ax in enumerate(AXLES_PX):
        x = ax - crop[0]
        m = (ax - S_NOSE) / S_PPM
        for yy in range(0, int(g), 10):
            d.line([(x, yy), (x, yy + 5)], fill=CORAL, width=2)
        d.text((x + 4, 4 + 20 * i), f'ось {"перед" if i == 0 else "зад"} {m:.2f} м', fill=CORAL, font=f)
    roof = (S_GROUND - 88) / S_PPM
    y = 88 - crop[1]
    d.line([(x0, y), (x0 + 4.4 * S_PPM, y)], fill=CYAN, width=2)
    d.text((x0 + 3.0 * S_PPM, y - 22), f'крыша {roof:.2f} м', fill=(33, 34, 116), font=f)
    out = Image.alpha_composite(base, lay).convert('RGB')
    out.save(os.path.join(UND, 'car_01_side_grid.png'))
    return out


def front_rear_underlay():
    src = Image.open(ORTHO).convert('RGBA')
    crop = (10, 470, 900, 790)
    base = src.crop(crop)
    lay = Image.new('RGBA', base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    g = 754 - crop[1]
    for (a, b, wm, name) in ((24, 428, 1.98, 'перед (по зеркалам 1,98)'), (458, 887, 1.92, 'корма (по аркам 1,92)')):
        ppm = (b - a) / wm
        cx = (a + b) / 2 - crop[0]
        grid(d, cx, g, ppm, -1.0, 1.0, 1.3, label_x=False)
        d.line([(cx, g - 1.3 * ppm), (cx, g)], fill=CORAL, width=2)
        d.text((a - crop[0] + 4, 2), name, fill=INK, font=font(14, True))
    out = Image.alpha_composite(base, lay).convert('RGB')
    out.save(os.path.join(UND, 'car_01_front_rear_grid.png'))
    return out


def fit(im, w):
    return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)


def board(side):
    W, M = 2400, 20
    cw = (W - 3 * M) // 2
    hero = fit(Image.open(os.path.join(REF, 'car_01_ref_01_hero.png')).convert('RGB'), cw)
    chase = fit(Image.open(os.path.join(REF, 'car_01_ref_02_chase.png')).convert('RGB'), cw)
    det = fit(Image.open(os.path.join(REF, 'car_01_ref_04_details.png')).convert('RGB'), cw)
    ortho = fit(Image.open(ORTHO).convert('RGB'), cw)
    colors = fit(Image.open(os.path.join(REF, 'car_01_ref_05_colorways.png')).convert('RGB'), cw)
    sideg = fit(side, W - 2 * M)
    HDR = 90
    rows = [HDR, hero.height, sideg.height + 34, max(ortho.height, det.height), colors.height]
    H = sum(rows) + M * (len(rows) + 1) + 40
    bd = Image.new('RGB', (W, H), PANEL)
    d = ImageDraw.Draw(bd)
    d.text((M, 14), 'car_01 v2 «Сэнко» — референсы на утверждение', fill=TXT, font=font(40, True))
    d.text((M, 62), 'STYLE_GUIDE v1.1: cel 3 ступени + тушевой контур #1B1030 (D-018) · порядок бриф → референсы → утверждение → модель (D-019) · бриф: docs/art/cars/car_01/BRIEF.md', fill=TXT2, font=font(18))
    y = HDR + M
    def cap(img, x, y, t):
        bd.paste(img, (x, y)); d.rectangle([x, y, x + img.width - 1, y + img.height - 1], outline=INK, width=3)
        d.rectangle([x, y, x + len(t) * 11 + 24, y + 30], fill=INK); d.text((x + 10, y + 3), t, fill=TXT, font=font(18, True))
    cap(hero, M, y, '01 · герой 3/4 спереди'); cap(chase, 2 * M + cw, y, '02 · камера погони — главный ракурс')
    y += hero.height + M
    cap(sideg, M, y, '03 · бок с сеткой (м) — подложка для MeshForge')
    d.text((M, y + sideg.height + 6), 'Масштаб по длине 4,40 м. Пунктир — оси колёс по картинке; бриф §2 — источник правды, картинка — образ.', fill=TXT2, font=font(18))
    y += sideg.height + 34 + M
    cap(ortho, M, y, '03 · ортогональный лист'); cap(det, 2 * M + cw, y, '04 · детали: огни, поп-апы, диск, крыло, арка, воздухозаборник')
    y += max(ortho.height, det.height) + M
    cap(colors, M, y, '05 · окраска: перламутр · коралл · ультрамарин · полночь')
    # палитра и размеры
    x = 2 * M + cw
    d.text((x, y), 'Палитра машины (STYLE_GUIDE §2.3, новых цветов нет)', fill=TXT, font=font(22, True))
    chips = [('#FAF2F4', 'перламутр свет'), ('#D9B0BE', 'перламутр полутон'), ('#9E6396', 'перламутр тень'), ('#E8364F', 'полоса героя'),
             ('#2A1A48', 'стекло, жалюзи, губа'), ('#1B1030', 'контур, пазы, днище'), ('#FF4F6E', 'стоп-сигналы'), ('#FFF6E0', 'фары'),
             ('#402A69', 'диск'), ('#3A2260', 'шина')]
    for i, (h, n) in enumerate(chips):
        cx, cy = x + (i % 2) * (cw // 2), y + 40 + (i // 2) * 52
        rgb = tuple(int(h[k:k + 2], 16) for k in (1, 3, 5))
        d.rectangle([cx, cy, cx + 44, cy + 40], fill=rgb, outline=TXT2, width=1)
        d.text((cx + 56, cy + 2), f'{h}  {n}', fill=TXT, font=font(18))
    yy = y + 40 + 5 * 52 + 14
    d.text((x, yy), 'Размеры (бриф §2, м)', fill=TXT, font=font(22, True))
    dims = ['длина 4,40 · высота 1,17–1,20 · крыло 1,14–1,18', 'ширина: двери 1,78 · арки зад 1,92 / перёд 1,88 · зеркала 1,98',
            'база 2,55 · свес перед 1,07 / зад 0,78 (по листу 03)', 'колесо Ø 0,64 · колея ±0,80 · просвет 0,12',
            'бюджет ≤ 4000 треугольников с колёсами, LOD1 ≈ 1500']
    for i, t in enumerate(dims):
        d.text((x, yy + 36 + i * 30), '• ' + t, fill=TXT, font=font(19))
    d.text((M, H - 34), 'Сгенерировано 2026-10-25, промпты — docs/art/cars/car_01/src/prompts.md, сборка листа — src/make_board.py', fill=TXT2, font=font(16))
    bd.save(os.path.join(ROOT, 'car_01_board.jpg'), quality=90)
    return bd


if __name__ == '__main__':
    os.makedirs(UND, exist_ok=True)
    s = side_underlay()
    front_rear_underlay()
    b = board(s)
    print('board', b.size)
