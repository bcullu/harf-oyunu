"""50 temel ülkenin bayrağı: Türkçe adları ve pixel art çizimleri.

Bayraklar dosyadan değil, kodla çizilir. Böylece oyun hiçbir dış görsele
bağlı olmaz ve her boyutta (panodaki 26x16 kutudan kazanma ekranındaki
büyük bayrağa kadar) aynı kodla üretilir.

Çizim, oyunun düşük çözünürlüklü iç yüzeyine yapılır; yüzey en sonunda
komşu-piksel yöntemiyle büyütüldüğü için sonuç pixel art görünür.
"""

from __future__ import annotations

import math

import pygame

# -- renkler ---------------------------------------------------------------
WHITE = (247, 247, 243)
BLACK = (26, 26, 30)
RED = (206, 43, 55)
DARKRED = (155, 28, 40)
MAROON = (138, 21, 56)
BLUE = (34, 61, 148)
NAVY = (18, 36, 92)
SKY = (108, 172, 228)
GREEN = (26, 136, 72)
DGREEN = (14, 94, 56)
GOLD = (245, 196, 48)
ORANGE = (238, 134, 48)
SAFFRON = (240, 142, 40)
BROWN = (120, 78, 44)
GREY = (150, 150, 155)


def _rect(surf, r, color):
    pygame.draw.rect(surf, color, r)


def _bands(surf, r, colors, weights=None, vertical=False):
    """Yatay ya da dikey şeritler. weights verilmezse şeritler eşit olur."""
    n = len(colors)
    weights = list(weights) if weights else [1] * n
    total = float(sum(weights))
    span = r.w if vertical else r.h
    pos = 0
    for i, (color, weight) in enumerate(zip(colors, weights)):
        size = span - pos if i == n - 1 else max(1, round(span * weight / total))
        if vertical:
            pygame.draw.rect(surf, color, (r.x + pos, r.y, size, r.h))
        else:
            pygame.draw.rect(surf, color, (r.x, r.y + pos, r.w, size))
        pos += size


def _hb(surf, r, colors, weights=None):
    _bands(surf, r, colors, weights, vertical=False)


def _vb(surf, r, colors, weights=None):
    _bands(surf, r, colors, weights, vertical=True)


def _disc(surf, r, fx, fy, fr, color):
    cx = r.x + fx * r.w
    cy = r.y + fy * r.h
    radius = max(1, round(fr * r.h))
    pygame.draw.circle(surf, color, (round(cx), round(cy)), radius)


def _ring(surf, r, fx, fy, fr, color, spokes=0):
    cx = round(r.x + fx * r.w)
    cy = round(r.y + fy * r.h)
    radius = max(2, round(fr * r.h))
    width = max(1, radius // 4)
    pygame.draw.circle(surf, color, (cx, cy), radius, width)
    for i in range(spokes):
        angle = 2 * math.pi * i / spokes
        pygame.draw.line(surf, color, (cx, cy),
                         (cx + radius * math.cos(angle),
                          cy + radius * math.sin(angle)))


def _star(surf, r, fx, fy, fr, color, points=5, rot=-90.0):
    """Çok küçük boyutlarda yıldız lekeye dönüşür; o durumda artı çizilir."""
    cx = r.x + fx * r.w
    cy = r.y + fy * r.h
    radius = fr * r.h
    if radius < 2.2:
        size = max(1, round(radius))
        pygame.draw.rect(surf, color, (round(cx - size), round(cy), size * 2 + 1, 1))
        pygame.draw.rect(surf, color, (round(cx), round(cy - size), 1, size * 2 + 1))
        return
    inner = radius * (0.382 if points == 5 else 0.5)
    verts = []
    for i in range(points * 2):
        angle = math.radians(rot + i * 180.0 / points)
        length = radius if i % 2 == 0 else inner
        verts.append((cx + length * math.cos(angle), cy + length * math.sin(angle)))
    pygame.draw.polygon(surf, color, verts)


def _crescent(surf, r, fx, fy, fr, color, bg):
    """Hilal: dolu daire, üstüne arka plan renginde kaydırılmış daire."""
    radius = max(2, round(fr * r.h))
    cx = round(r.x + fx * r.w)
    cy = round(r.y + fy * r.h)
    pygame.draw.circle(surf, color, (cx, cy), radius)
    pygame.draw.circle(surf, bg, (cx + max(1, round(radius * 0.34)), cy),
                       max(1, round(radius * 0.82)))


def _cross(surf, r, color, fx=0.5, fy=0.5, thick=0.18):
    t = max(1, round(thick * r.h))
    pygame.draw.rect(surf, color, (round(r.x + fx * r.w - t / 2), r.y, t, r.h))
    pygame.draw.rect(surf, color, (r.x, round(r.y + fy * r.h - t / 2), r.w, t))


def _nordic(surf, r, color, thick=0.20):
    _cross(surf, r, color, fx=0.34, fy=0.5, thick=thick)


def _triangle_left(surf, r, color, fw=0.5):
    pygame.draw.polygon(surf, color, [
        (r.x, r.y), (r.x + r.w * fw, r.y + r.h / 2), (r.x, r.y + r.h)])


def _clip(surf, area):
    old = surf.get_clip()
    surf.set_clip(area)
    return old


# -- tek tek bayraklar -----------------------------------------------------
def _f_tr(s, r):
    _rect(s, r, RED)
    _crescent(s, r, 0.38, 0.5, 0.30, WHITE, RED)
    _star(s, r, 0.57, 0.5, 0.15, WHITE)


def _f_az(s, r):
    _hb(s, r, [SKY, RED, GREEN])
    _crescent(s, r, 0.45, 0.5, 0.17, WHITE, RED)
    _star(s, r, 0.58, 0.5, 0.10, WHITE, points=8)


def _f_de(s, r):
    _hb(s, r, [BLACK, RED, GOLD])


def _f_fr(s, r):
    _vb(s, r, [BLUE, WHITE, RED])


def _f_it(s, r):
    _vb(s, r, [GREEN, WHITE, RED])


def _f_es(s, r):
    _hb(s, r, [RED, GOLD, RED], [1, 2, 1])
    box = pygame.Rect(round(r.x + r.w * 0.26), round(r.y + r.h * 0.33),
                      max(2, round(r.w * 0.10)), max(3, round(r.h * 0.34)))
    _rect(s, box, DARKRED)
    pygame.draw.rect(s, GOLD, box, 1)


def _f_pt(s, r):
    _vb(s, r, [DGREEN, RED], [2, 3])
    _disc(s, r, 0.40, 0.5, 0.24, GOLD)
    _disc(s, r, 0.40, 0.5, 0.13, RED)
    _disc(s, r, 0.40, 0.5, 0.05, WHITE)


def _f_nl(s, r):
    _hb(s, r, [RED, WHITE, BLUE])


def _f_be(s, r):
    _vb(s, r, [BLACK, GOLD, RED])


def _f_ch(s, r):
    _rect(s, r, RED)
    _cross(s, r, WHITE, thick=0.20)


def _f_at(s, r):
    _hb(s, r, [RED, WHITE, RED])


def _f_gr(s, r):
    _hb(s, r, [BLUE, WHITE] * 4 + [BLUE])
    canton = pygame.Rect(r.x, r.y, round(r.w * 0.37), round(r.h * 0.56))
    _rect(s, canton, BLUE)
    _cross(s, canton, WHITE, thick=0.22)


def _f_bg(s, r):
    _hb(s, r, [WHITE, GREEN, RED])


def _f_ro(s, r):
    _vb(s, r, [BLUE, GOLD, RED])


def _f_hu(s, r):
    _hb(s, r, [RED, WHITE, GREEN])


def _f_pl(s, r):
    _hb(s, r, [WHITE, RED])


def _f_cz(s, r):
    _hb(s, r, [WHITE, RED])
    _triangle_left(s, r, BLUE, fw=0.52)


def _f_ua(s, r):
    _hb(s, r, [SKY, GOLD])


def _f_ru(s, r):
    _hb(s, r, [WHITE, BLUE, RED])


def _f_se(s, r):
    _rect(s, r, BLUE)
    _nordic(s, r, GOLD)


def _f_no(s, r):
    _rect(s, r, RED)
    _nordic(s, r, WHITE, thick=0.30)
    _nordic(s, r, NAVY, thick=0.14)


def _f_dk(s, r):
    _rect(s, r, RED)
    _nordic(s, r, WHITE)


def _f_fi(s, r):
    _rect(s, r, WHITE)
    _nordic(s, r, BLUE)


def _f_is(s, r):
    _rect(s, r, NAVY)
    _nordic(s, r, WHITE, thick=0.30)
    _nordic(s, r, RED, thick=0.14)


def _f_ie(s, r):
    _vb(s, r, [GREEN, WHITE, ORANGE])


def _union_jack(s, r):
    """Birleşik Krallık bayrağı; ince ayrıntılar pixel ölçeğinde sadeleşti."""
    _rect(s, r, NAVY)
    thick = max(1, round(r.h * 0.16))
    for a, b in (((r.x, r.y), (r.right, r.bottom)),
                 ((r.x, r.bottom), (r.right, r.y))):
        pygame.draw.line(s, WHITE, a, b, thick)
    for a, b in (((r.x, r.y), (r.right, r.bottom)),
                 ((r.x, r.bottom), (r.right, r.y))):
        pygame.draw.line(s, RED, a, b, max(1, thick // 3))
    _cross(s, r, WHITE, thick=0.30)
    _cross(s, r, RED, thick=0.17)


def _f_gb(s, r):
    _union_jack(s, r)


def _f_us(s, r):
    stripe = r.h / 13.0
    _rect(s, r, WHITE)
    for i in range(0, 13, 2):
        pygame.draw.rect(s, RED, (r.x, round(r.y + i * stripe), r.w,
                                  max(1, round(stripe))))
    canton = pygame.Rect(r.x, r.y, round(r.w * 0.40), round(stripe * 7))
    _rect(s, canton, NAVY)
    step_x = canton.w / 6.0
    step_y = canton.h / 5.0
    for row in range(5):
        for col in range(6):
            pygame.draw.rect(s, WHITE, (round(canton.x + step_x * (col + 0.5)),
                                        round(canton.y + step_y * (row + 0.5)), 1, 1))


def _maple(s, r, color):
    pts = [(0.50, 0.08), (0.56, 0.26), (0.69, 0.22), (0.65, 0.34),
           (0.80, 0.44), (0.72, 0.50), (0.76, 0.62), (0.61, 0.57),
           (0.57, 0.64), (0.53, 0.60), (0.55, 0.93), (0.45, 0.93),
           (0.47, 0.60), (0.43, 0.64), (0.39, 0.57), (0.24, 0.62),
           (0.28, 0.50), (0.20, 0.44), (0.35, 0.34), (0.31, 0.22),
           (0.44, 0.26)]
    pygame.draw.polygon(s, color, [(r.x + x * r.w, r.y + y * r.h) for x, y in pts])


def _f_ca(s, r):
    _vb(s, r, [RED, WHITE, RED], [1, 2, 1])
    leaf = pygame.Rect(round(r.x + r.w * 0.34), round(r.y + r.h * 0.10),
                       round(r.w * 0.32), round(r.h * 0.80))
    _maple(s, leaf, RED)


def _f_mx(s, r):
    _vb(s, r, [GREEN, WHITE, RED])
    _disc(s, r, 0.50, 0.50, 0.13, BROWN)
    _disc(s, r, 0.50, 0.58, 0.07, DGREEN)


def _f_br(s, r):
    _rect(s, r, GREEN)
    pygame.draw.polygon(s, GOLD, [
        (r.x + r.w * 0.5, r.y + r.h * 0.10),
        (r.x + r.w * 0.90, r.y + r.h * 0.5),
        (r.x + r.w * 0.5, r.y + r.h * 0.90),
        (r.x + r.w * 0.10, r.y + r.h * 0.5)])
    _disc(s, r, 0.50, 0.50, 0.26, BLUE)
    band = pygame.Rect(round(r.x + r.w * 0.34), round(r.y + r.h * 0.48),
                       round(r.w * 0.32), max(1, round(r.h * 0.09)))
    _rect(s, band, WHITE)


def _f_ar(s, r):
    _hb(s, r, [SKY, WHITE, SKY])
    _star(s, r, 0.50, 0.50, 0.17, GOLD, points=8, rot=0)
    _disc(s, r, 0.50, 0.50, 0.09, GOLD)


def _f_cl(s, r):
    _hb(s, r, [WHITE, RED])
    canton = pygame.Rect(r.x, r.y, round(r.w * 0.34), round(r.h * 0.5))
    _rect(s, canton, BLUE)
    _star(s, canton, 0.5, 0.5, 0.32, WHITE)


def _f_co(s, r):
    _hb(s, r, [GOLD, BLUE, RED], [2, 1, 1])


def _f_pe(s, r):
    _vb(s, r, [RED, WHITE, RED])


def _f_jp(s, r):
    _rect(s, r, WHITE)
    _disc(s, r, 0.50, 0.50, 0.30, RED)


def _f_cn(s, r):
    _rect(s, r, RED)
    _star(s, r, 0.18, 0.30, 0.17, GOLD)
    for fx, fy in ((0.34, 0.14), (0.40, 0.26), (0.40, 0.42), (0.34, 0.54)):
        _star(s, r, fx, fy, 0.07, GOLD)


def _f_kr(s, r):
    _rect(s, r, WHITE)
    radius = max(3, round(r.h * 0.22))
    cx = round(r.x + r.w * 0.5)
    cy = round(r.y + r.h * 0.5)
    pygame.draw.circle(s, RED, (cx, cy), radius)
    old = _clip(s, pygame.Rect(cx - radius, cy, radius * 2 + 1, radius + 1))
    pygame.draw.circle(s, BLUE, (cx, cy), radius)
    s.set_clip(old)
    half = max(1, radius // 2)
    pygame.draw.circle(s, BLUE, (cx - half, cy), max(1, half // 2 + 1))
    pygame.draw.circle(s, RED, (cx + half, cy), max(1, half // 2 + 1))
    bar_w = max(2, round(r.w * 0.11))
    bar_h = max(1, round(r.h * 0.05))
    for fx, fy in ((0.16, 0.22), (0.16, 0.78), (0.84, 0.22), (0.84, 0.78)):
        for i in range(3):
            pygame.draw.rect(s, BLACK, (round(r.x + fx * r.w - bar_w / 2),
                                        round(r.y + fy * r.h + i * (bar_h + 1) - bar_h),
                                        bar_w, bar_h))


def _f_in(s, r):
    _hb(s, r, [SAFFRON, WHITE, GREEN])
    _ring(s, r, 0.50, 0.50, 0.14, NAVY, spokes=8)


def _f_id(s, r):
    _hb(s, r, [RED, WHITE])


def _f_vn(s, r):
    _rect(s, r, RED)
    _star(s, r, 0.50, 0.50, 0.28, GOLD)


def _f_th(s, r):
    _hb(s, r, [RED, WHITE, NAVY, WHITE, RED], [1, 1, 2, 1, 1])


def _f_pk(s, r):
    _vb(s, r, [WHITE, DGREEN], [1, 3])
    _crescent(s, r, 0.62, 0.50, 0.24, WHITE, DGREEN)
    _star(s, r, 0.76, 0.32, 0.10, WHITE)


def _f_ir(s, r):
    _hb(s, r, [GREEN, WHITE, RED])
    _disc(s, r, 0.50, 0.50, 0.10, RED)


def _f_qa(s, r):
    _rect(s, r, MAROON)
    band = round(r.w * 0.30)
    pygame.draw.rect(s, WHITE, (r.x, r.y, band, r.h))
    teeth = 9
    step = r.h / teeth
    for i in range(teeth):
        pygame.draw.polygon(s, MAROON, [
            (r.x + band, r.y + i * step),
            (r.x + band - r.w * 0.09, r.y + (i + 0.5) * step),
            (r.x + band, r.y + (i + 1) * step)])


def _f_za(s, r):
    _hb(s, r, [RED, BLUE])
    pygame.draw.polygon(s, WHITE, [
        (r.x, r.y), (r.x + r.w * 0.52, r.y + r.h * 0.5),
        (r.x, r.bottom), (r.x, r.bottom - r.h * 0.22),
        (r.x + r.w * 0.26, r.y + r.h * 0.5),
        (r.x, r.y + r.h * 0.22)])
    pygame.draw.polygon(s, GREEN, [
        (r.x, r.y + r.h * 0.30), (r.x + r.w * 0.30, r.y + r.h * 0.5),
        (r.x, r.bottom - r.h * 0.30)])
    pygame.draw.polygon(s, GOLD, [
        (r.x, r.y + r.h * 0.18), (r.x + r.w * 0.16, r.y + r.h * 0.5),
        (r.x, r.bottom - r.h * 0.18)])
    pygame.draw.polygon(s, BLACK, [
        (r.x, r.y + r.h * 0.26), (r.x + r.w * 0.11, r.y + r.h * 0.5),
        (r.x, r.bottom - r.h * 0.26)])


def _f_ng(s, r):
    _vb(s, r, [GREEN, WHITE, GREEN])


def _f_au(s, r):
    _rect(s, r, NAVY)
    canton = pygame.Rect(r.x, r.y, round(r.w * 0.50), round(r.h * 0.50))
    _union_jack(s, canton)
    _star(s, r, 0.25, 0.78, 0.11, WHITE, points=7)
    for fx, fy, fr in ((0.72, 0.22, 0.07), (0.86, 0.46, 0.07),
                       (0.72, 0.72, 0.07), (0.62, 0.52, 0.05),
                       (0.78, 0.46, 0.04)):
        _star(s, r, fx, fy, fr, WHITE, points=7)


def _f_nz(s, r):
    _rect(s, r, NAVY)
    canton = pygame.Rect(r.x, r.y, round(r.w * 0.50), round(r.h * 0.50))
    _union_jack(s, canton)
    for fx, fy in ((0.70, 0.26), (0.84, 0.50), (0.70, 0.76), (0.62, 0.52)):
        _star(s, r, fx, fy, 0.07, RED)


def _f_il(s, r):
    _rect(s, r, WHITE)
    band = max(1, round(r.h * 0.13))
    pygame.draw.rect(s, BLUE, (r.x, round(r.y + r.h * 0.12), r.w, band))
    pygame.draw.rect(s, BLUE, (r.x, round(r.bottom - r.h * 0.12 - band), r.w, band))
    # Davud yıldızı: ters yönde iki üçgen
    cx, cy, rad = r.x + r.w * 0.5, r.y + r.h * 0.5, r.h * 0.24
    for flip in (-1, 1):
        pts = [(cx + rad * math.cos(math.radians(a)),
                cy + flip * rad * math.sin(math.radians(a)))
               for a in (-90, 30, 150)]
        pygame.draw.polygon(s, BLUE, pts, max(1, round(r.h * 0.05)))


def _f_ma(s, r):
    _rect(s, r, DARKRED)
    _star(s, r, 0.50, 0.50, 0.26, GREEN)


# -- kayıt -----------------------------------------------------------------
# Sıra panoda da kullanılır: komşu ülkeler yan yana olsun diye kabaca
# bölgelere göre dizildi.
FLAGS: list[tuple[str, str, object]] = [
    ("tr", "Türkiye", _f_tr),
    ("az", "Azerbaycan", _f_az),
    ("gr", "Yunanistan", _f_gr),
    ("bg", "Bulgaristan", _f_bg),
    ("ro", "Romanya", _f_ro),
    ("hu", "Macaristan", _f_hu),
    ("at", "Avusturya", _f_at),
    ("ch", "İsviçre", _f_ch),
    ("de", "Almanya", _f_de),
    ("fr", "Fransa", _f_fr),
    ("it", "İtalya", _f_it),
    ("es", "İspanya", _f_es),
    ("pt", "Portekiz", _f_pt),
    ("nl", "Hollanda", _f_nl),
    ("be", "Belçika", _f_be),
    ("ie", "İrlanda", _f_ie),
    ("gb", "İngiltere", _f_gb),
    ("pl", "Polonya", _f_pl),
    ("cz", "Çekya", _f_cz),
    ("ua", "Ukrayna", _f_ua),
    ("ru", "Rusya", _f_ru),
    ("se", "İsveç", _f_se),
    ("no", "Norveç", _f_no),
    ("dk", "Danimarka", _f_dk),
    ("fi", "Finlandiya", _f_fi),
    ("is", "İzlanda", _f_is),
    ("us", "Amerika", _f_us),
    ("ca", "Kanada", _f_ca),
    ("mx", "Meksika", _f_mx),
    ("br", "Brezilya", _f_br),
    ("ar", "Arjantin", _f_ar),
    ("cl", "Şili", _f_cl),
    ("co", "Kolombiya", _f_co),
    ("pe", "Peru", _f_pe),
    ("jp", "Japonya", _f_jp),
    ("cn", "Çin", _f_cn),
    ("kr", "Güney Kore", _f_kr),
    ("in", "Hindistan", _f_in),
    ("id", "Endonezya", _f_id),
    ("vn", "Vietnam", _f_vn),
    ("th", "Tayland", _f_th),
    ("pk", "Pakistan", _f_pk),
    ("ir", "İran", _f_ir),
    ("qa", "Katar", _f_qa),
    ("il", "İsrail", _f_il),
    ("ma", "Fas", _f_ma),
    ("ng", "Nijerya", _f_ng),
    ("za", "Güney Afrika", _f_za),
    ("au", "Avustralya", _f_au),
    ("nz", "Yeni Zelanda", _f_nz),
]

CODES = [code for code, _, _ in FLAGS]
NAMES = {code: name for code, name, _ in FLAGS}
_DRAWERS = {code: fn for code, _, fn in FLAGS}


def name_of(code: str) -> str:
    return NAMES.get(code, code)


def draw_flag(surface: pygame.Surface, rect, code: str,
              border: bool = True) -> None:
    """Bayrağı verilen dikdörtgene çizer. Bilinmeyen kod gri kutu olur."""
    rect = pygame.Rect(rect)
    if rect.w < 2 or rect.h < 2:
        return
    old_clip = surface.get_clip()
    surface.set_clip(rect.clip(old_clip) if old_clip else rect)
    drawer = _DRAWERS.get(code)
    if drawer is None:
        pygame.draw.rect(surface, GREY, rect)
    else:
        drawer(surface, rect)
    surface.set_clip(old_clip)
    if border:
        pygame.draw.rect(surface, BLACK, rect, 1)


def flag_surface(code: str, size: tuple[int, int],
                 border: bool = True) -> pygame.Surface:
    surf = pygame.Surface(size, pygame.SRCALPHA)
    draw_flag(surf, pygame.Rect(0, 0, size[0], size[1]), code, border=border)
    return surf
