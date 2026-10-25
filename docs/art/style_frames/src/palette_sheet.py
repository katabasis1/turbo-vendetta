"""Лист палитры «Закатная трасса» (STYLE_GUIDE §2). Запуск: python3 palette_sheet.py out.png"""
import sys
from PIL import Image, ImageDraw, ImageFont
FD = '/usr/share/fonts/truetype/noto/'
FH = ImageFont.truetype(FD + 'NotoSansDisplay-SemiCondensedBlackItalic.ttf', 30)
FL = ImageFont.truetype(FD + 'NotoSans-SemiCondensedSemiBold.ttf', 17)
FX = ImageFont.truetype(FD + 'NotoSans-SemiCondensed.ttf', 15)
G = [
 ('НЕБО И СВЕТ', [('#24163F','зенит'),('#46286E','верх неба'),('#9D4488','лиловый'),('#EB7B93','коралл'),('#F6B26B','янтарь горизонта'),('#FFF1D6','солнце'),('#6A3A80','облако'),('#F3A0A8','кромка облака')]),
 ('МИР', [('#7A4A86','город дальний'),('#3A2260','город ближний'),('#FFC870','окна / фонари'),('#A390C0','бетон, свет'),('#715194','бетон, полутон'),('#402A69','бетон, тень'),('#6A3F7C','асфальт вдали'),('#2E1D47','асфальт рядом'),('#EEC2E4','разметка'),('#1B1030','самая тёмная тень')]),
 ('МАШИНЫ', [('#FAF2F4','перламутр, свет'),('#D9B0BE','перламутр, полутон'),('#9E6396','перламутр, тень'),('#E8364F','полоса героя'),('#4448C8','соперник, свет'),('#3030B2','соперник, полутон'),('#212274','соперник, тень'),('#2A1A48','стекло'),('#FF4F6E','стоп-сигнал'),('#FFF6E0','фары')]),
 ('ЭФФЕКТЫ', [('#FFFEDA','вспышка, ядро'),('#F4AC5A','вспышка, кромка'),('#1B1030','кромка вспышки'),('#FFC870','искры'),('#D5B1BB','дым, свет'),('#A390C0','дым, тень'),('#FF5FA2','шлейф огней'),('#FFFFFF','линии скорости')]),
 ('ИНТЕРФЕЙС', [('#130C27','чернила'),('#1B1433','панель'),('#2C2050','панель, выделение'),('#FCF7F9','текст'),('#BCA4D1','текст, второй план'),('#F13858','действие · атака'),('#54DFFA','защита · инфо'),('#F4AC5A','стиль · награды'),('#FFE45C','угроза + полосы')]),
]
SW, SH, PADX = 150, 92, 24
cols = max(len(s) for _, s in G)
Wd = PADX * 2 + cols * (SW + 10)
Hd = 70 + len(G) * (SH + 96)
im = Image.new('RGB', (Wd, Hd), '#130C27'); d = ImageDraw.Draw(im)
d.text((PADX, 18), 'ТУРБОВЕНДЕТТА · ПАЛИТРА «ЗАКАТНАЯ ТРАССА» (база)', font=FH, fill='#FCF7F9')
y = 74
for title, sw in G:
    d.text((PADX, y), title, font=FL, fill='#F4AC5A'); y += 28
    for i, (hx, name) in enumerate(sw):
        x = PADX + i * (SW + 10)
        d.rectangle([x, y, x + SW, y + SH], fill=hx, outline='#2C2050')
        d.text((x, y + SH + 6), hx, font=FL, fill='#FCF7F9')
        d.text((x, y + SH + 26), name, font=FX, fill='#BCA4D1')
    y += SH + 68
# полосы угрозы на последнем образце
xs = PADX + 8 * (SW + 10); ys = y - SH - 68
for k in range(-SH, SW, 28):
    d.polygon([(xs + max(k, 0), ys + max(0, -k)), (xs + max(k + 14, 0), ys + max(0, -k - 14)), (xs + min(k + 14 + SH, SW), ys + min(SH, SW - k - 14)), (xs + min(k + SH, SW), ys + min(SH, SW - k))], fill='#130C27')
im.save(sys.argv[1]); print(im.size)
