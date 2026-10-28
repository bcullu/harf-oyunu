"""Çizim katmanı: izometrik oda, pixel art karakterler ve ekranlar.

Her şey önce 320x180'lik küçük bir yüzeye çizilir, sonra tam sayı katıyla
komşu-piksel yöntemiyle büyütülür. Pixel art görünümü buradan gelir;
ayrıca küçük yüzeye çizmek CPU'yu düşük tutar.

Ekranda neredeyse hiç yazı yok. Çocuk okuma bilmiyor: bütün anlatım
renk, ok, parıltı ve ses ile yapılır.
"""

from __future__ import annotations

import math

import pygame

from app import flags as flagmod
from app.game import SPOTS, STEPS_TO_WIN
from app.flags import CODES

VIRTUAL = (320, 180)

# izometrik karo ölçüsü ve odanın sol üst köşesinin ekran karşılığı
TILE_W, TILE_H = 22, 11
ORIGIN = (160, 46)
ROOM = 8            # oda ROOM x ROOM karo
WALL_H = 42

# -- palet -----------------------------------------------------------------
BG = (18, 16, 28)
FLOOR_A = (84, 76, 104)
FLOOR_B = (72, 65, 92)
FLOOR_EDGE = (56, 50, 74)
WALL_L = (58, 52, 80)
WALL_R = (46, 41, 66)
WALL_TOP = (72, 64, 96)
GOLD = (245, 198, 72)
DARKGOLD = (176, 132, 36)
WHITE = (247, 247, 243)
BLACK = (20, 18, 28)
SKIN = (238, 190, 150)
HAIR = (72, 48, 38)
SHIRT = (74, 180, 128)
PANTS = (58, 74, 140)
SPIDER_RED = (206, 48, 58)
SPIDER_BLUE = (46, 70, 158)
WEB = (236, 240, 248)
SAFE_GREEN = (104, 226, 140)
DANGER_RED = (236, 96, 96)
CONE_WARM = (255, 206, 120)

# 3x5 piksel rakamlar: küçük sayaç için yeterli, fonta gerek yok
_GLYPHS = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("111", "001", "111", "100", "111"),
    "3": ("111", "001", "111", "001", "111"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "111", "001", "111"),
    "6": ("111", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "111"),
    "/": ("001", "001", "010", "100", "100"),
    " ": ("000", "000", "000", "000", "000"),
}


def iso(tx: float, ty: float) -> tuple[float, float]:
    """Karo koordinatını ekran koordinatına çevirir."""
    return (ORIGIN[0] + (tx - ty) * TILE_W / 2,
            ORIGIN[1] + (tx + ty) * TILE_H / 2)


def _tiny_text(surf, text: str, x: int, y: int, color, scale: int = 1) -> int:
    for char in text:
        rows = _GLYPHS.get(char, _GLYPHS[" "])
        for ry, row in enumerate(rows):
            for rx, bit in enumerate(row):
                if bit == "1":
                    pygame.draw.rect(surf, color,
                                     (x + rx * scale, y + ry * scale, scale, scale))
        x += 4 * scale
    return x


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _pulse(now: int, period: int = 700) -> float:
    """0..1 arası yumuşak nabız."""
    return 0.5 + 0.5 * math.sin(2 * math.pi * (now % period) / period)


class Renderer:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.canvas = pygame.Surface(VIRTUAL).convert()
        self.overlay = pygame.Surface(VIRTUAL, pygame.SRCALPHA)
        # zemine boyanan ışık/parıltı: eşya ve karakterlerin ALTINDA kalır
        self.floor_fx = pygame.Surface(VIRTUAL, pygame.SRCALPHA)
        self.cone_layer = pygame.Surface(VIRTUAL, pygame.SRCALPHA)
        # zemin maskesi: ışık konisi odanın dışına taşmasın
        self.floor_mask = pygame.Surface(VIRTUAL, pygame.SRCALPHA)
        self.floor_mask.fill((0, 0, 0, 0))
        pygame.draw.polygon(self.floor_mask, (255, 255, 255, 255),
                            [iso(0, 0), iso(ROOM, 0), iso(ROOM, ROOM),
                             iso(0, ROOM)])
        self.font = self._load_font(13)
        self.small_font = self._load_font(9)
        self._confetti: list[list[float]] = []

    @staticmethod
    def _load_font(size: int):
        try:
            return pygame.font.SysFont(None, size)
        except Exception:      # font yoksa oyun yazısız devam etsin
            return None

    # -- ekrana basma ----------------------------------------------------
    def present(self) -> None:
        sw, sh = self.screen.get_size()
        scale = max(1, min(sw // VIRTUAL[0], sh // VIRTUAL[1]))
        size = (VIRTUAL[0] * scale, VIRTUAL[1] * scale)
        scaled = pygame.transform.scale(self.canvas, size)
        self.screen.fill(BLACK)
        self.screen.blit(scaled, ((sw - size[0]) // 2, (sh - size[1]) // 2))
        pygame.display.flip()

    def draw(self, game, now: int) -> None:
        from app.game import BOARD, DONE, PLAY, TITLE, WIN

        self.canvas.fill(BG)
        self.overlay.fill((0, 0, 0, 0))
        self.floor_fx.fill((0, 0, 0, 0))
        if game.state in (TITLE, PLAY):
            self._draw_room_scene(game, now)
        elif game.state == WIN:
            self._draw_win(game, now)
        elif game.state == BOARD:
            self._draw_board(game, now)
        elif game.state == DONE:
            self._draw_done(game, now)
        self.canvas.blit(self.overlay, (0, 0))

    # -- oda -------------------------------------------------------------
    def _draw_floor(self) -> None:
        for ty in range(ROOM):
            for tx in range(ROOM):
                pts = [iso(tx, ty), iso(tx + 1, ty),
                       iso(tx + 1, ty + 1), iso(tx, ty + 1)]
                color = FLOOR_A if (tx + ty) % 2 == 0 else FLOOR_B
                pygame.draw.polygon(self.canvas, color, pts)
        # dış kenar, zemini duvardan ayırsın
        pygame.draw.polygon(self.canvas, FLOOR_EDGE,
                            [iso(0, 0), iso(ROOM, 0),
                             iso(ROOM, ROOM), iso(0, ROOM)], 1)

    def _draw_walls(self, now: int) -> None:
        # sol duvar (ty = 0 kenarı)
        a, b = iso(0, 0), iso(ROOM, 0)
        pygame.draw.polygon(self.canvas, WALL_R, [
            a, b, (b[0], b[1] - WALL_H), (a[0], a[1] - WALL_H)])
        # sağ duvar (tx = 0 kenarı)
        c = iso(0, ROOM)
        pygame.draw.polygon(self.canvas, WALL_L, [
            a, c, (c[0], c[1] - WALL_H), (a[0], a[1] - WALL_H)])
        pygame.draw.line(self.canvas, WALL_TOP,
                         (a[0], a[1] - WALL_H), (b[0], b[1] - WALL_H))
        pygame.draw.line(self.canvas, WALL_TOP,
                         (a[0], a[1] - WALL_H), (c[0], c[1] - WALL_H))
        pygame.draw.line(self.canvas, (36, 32, 52), a, (a[0], a[1] - WALL_H))

        # duvarda müze afişleri ve meşaleler: oda boş görünmesin
        self._wall_banner(2.4, True)
        self._wall_banner(5.6, False)
        self._torch(6.6, True, now)
        self._torch(1.4, False, now)

    def _wall_banner(self, t: float, left_wall: bool) -> None:
        base = iso(t, 0) if left_wall else iso(0, t)
        x, y = base[0], base[1] - WALL_H + 6
        pygame.draw.rect(self.canvas, DARKGOLD, (x - 4, y, 9, 18))
        pygame.draw.rect(self.canvas, (120, 70, 150), (x - 3, y + 1, 7, 16))
        pygame.draw.polygon(self.canvas, DARKGOLD,
                            [(x - 4, y + 18), (x + 5, y + 18), (x, y + 22)])

    def _torch(self, t: float, left_wall: bool, now: int) -> None:
        base = iso(t, 0) if left_wall else iso(0, t)
        x, y = base[0], base[1] - WALL_H + 14
        pygame.draw.rect(self.canvas, (92, 70, 50), (x - 1, y, 2, 7))
        flicker = 1 + int(_pulse(now, 430) * 2)
        pygame.draw.circle(self.canvas, (250, 180, 70), (int(x), int(y - 1)),
                           flicker + 1)
        pygame.draw.circle(self.canvas, (255, 238, 170), (int(x), int(y - 1)),
                           max(1, flicker - 1))

    # -- eşyalar ---------------------------------------------------------
    def _prop(self, kind: str, tx: float, ty: float, code: str,
              now: int, has_flag: bool) -> None:
        x, y = iso(tx, ty)
        x, y = int(x), int(y)
        shadow = pygame.Surface((18, 8), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 70), (0, 0, 18, 8))
        self.canvas.blit(shadow, (x - 9, y - 3))

        if kind == "crate":
            pygame.draw.rect(self.canvas, (140, 98, 56), (x - 8, y - 14, 16, 14))
            pygame.draw.rect(self.canvas, (108, 74, 42), (x - 8, y - 14, 16, 14), 1)
            pygame.draw.line(self.canvas, (108, 74, 42), (x - 8, y - 14), (x + 7, y - 1))
            pygame.draw.line(self.canvas, (108, 74, 42), (x + 7, y - 14), (x - 8, y - 1))
        elif kind == "barrel":
            pygame.draw.ellipse(self.canvas, (120, 82, 50), (x - 7, y - 17, 14, 17))
            pygame.draw.rect(self.canvas, (92, 62, 38), (x - 7, y - 12, 14, 2))
            pygame.draw.rect(self.canvas, (92, 62, 38), (x - 7, y - 6, 14, 2))
            pygame.draw.ellipse(self.canvas, (150, 108, 66), (x - 7, y - 19, 14, 5))
        elif kind == "plant":
            pygame.draw.rect(self.canvas, (160, 96, 70), (x - 5, y - 7, 10, 7))
            pygame.draw.rect(self.canvas, (128, 72, 52), (x - 6, y - 9, 12, 3))
            for dx, dy, r in ((-4, -13, 4), (3, -14, 4), (0, -18, 5), (-1, -11, 4)):
                pygame.draw.circle(self.canvas, (56, 150, 86), (x + dx, y + dy), r)
            pygame.draw.circle(self.canvas, (84, 186, 112), (x - 2, y - 17), 2)
        elif kind == "column":
            pygame.draw.rect(self.canvas, (198, 192, 180), (x - 5, y - 26, 10, 26))
            pygame.draw.rect(self.canvas, (170, 164, 152), (x - 5, y - 26, 2, 26))
            pygame.draw.rect(self.canvas, (214, 208, 196), (x - 7, y - 29, 14, 4))
            pygame.draw.rect(self.canvas, (214, 208, 196), (x - 7, y - 2, 14, 3))
        elif kind == "door":
            pygame.draw.polygon(self.canvas, (40, 36, 54),
                                [(x - 10, y + 2), (x + 10, y + 2),
                                 (x + 7, y - 4), (x - 7, y - 4)])
            pygame.draw.polygon(self.canvas, (96, 86, 120),
                                [(x - 10, y + 2), (x + 10, y + 2),
                                 (x + 7, y - 4), (x - 7, y - 4)], 1)
        elif kind == "pedestal":
            pygame.draw.rect(self.canvas, (176, 170, 158), (x - 7, y - 12, 14, 12))
            pygame.draw.rect(self.canvas, (206, 200, 188), (x - 9, y - 15, 18, 4))
            pygame.draw.rect(self.canvas, (146, 140, 128), (x - 9, y - 1, 18, 3))
            if has_flag:
                self._flag_on_pole(x, y - 15, code, now)

    def _flag_on_pole(self, x: int, y: int, code: str, now: int) -> None:
        glow = int(2 + _pulse(now, 1100) * 3)
        for radius, alpha in ((12 + glow, 18), (7 + glow, 26)):
            pygame.draw.circle(self.overlay, (255, 230, 140, alpha),
                               (x, y - 16), radius)
        pygame.draw.rect(self.canvas, (120, 108, 92), (x - 1, y - 30, 2, 30))
        rect = pygame.Rect(x + 1, y - 30, 21, 14)
        flagmod.draw_flag(self.canvas, rect, code)

    # -- karakterler -----------------------------------------------------
    def _draw_player(self, x: int, y: int, now: int, hiding: bool,
                     caught: bool) -> None:
        """Bayrağı çalmaya çalışan küçük kahraman."""
        bob = 1 if (not hiding and (now // 160) % 2 == 0) else 0
        y -= bob
        shadow = pygame.Surface((12, 6), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 80), (0, 0, 12, 6))
        self.canvas.blit(shadow, (x - 6, y - 2))
        # bacaklar
        pygame.draw.rect(self.canvas, PANTS, (x - 3, y - 5, 2, 5))
        pygame.draw.rect(self.canvas, PANTS, (x + 1, y - 5, 2, 5))
        # gövde
        pygame.draw.rect(self.canvas, SHIRT, (x - 4, y - 11, 8, 7))
        pygame.draw.rect(self.canvas, (54, 140, 98), (x - 4, y - 9, 8, 2))
        # kollar
        pygame.draw.rect(self.canvas, SKIN, (x - 6, y - 10, 2, 5))
        pygame.draw.rect(self.canvas, SKIN, (x + 4, y - 10, 2, 5))
        # kafa
        pygame.draw.rect(self.canvas, SKIN, (x - 4, y - 17, 8, 7))
        pygame.draw.rect(self.canvas, HAIR, (x - 4, y - 18, 8, 3))
        pygame.draw.rect(self.canvas, HAIR, (x - 5, y - 17, 1, 2))
        if caught:
            # şaşkın yüz
            pygame.draw.rect(self.canvas, BLACK, (x - 3, y - 15, 2, 2))
            pygame.draw.rect(self.canvas, BLACK, (x + 1, y - 15, 2, 2))
            pygame.draw.rect(self.canvas, BLACK, (x - 1, y - 12, 3, 2))
        else:
            pygame.draw.rect(self.canvas, BLACK, (x - 3, y - 15, 1, 2))
            pygame.draw.rect(self.canvas, BLACK, (x + 2, y - 15, 1, 2))
            pygame.draw.rect(self.canvas, (182, 120, 110), (x - 1, y - 12, 2, 1))

    def _draw_guard(self, x: int, y: int, now: int, safe: bool) -> None:
        """Örümcek bekçi. Sırtı dönükken gözleri görünmez: güvenli an."""
        shadow = pygame.Surface((16, 7), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 90), (0, 0, 16, 7))
        self.canvas.blit(shadow, (x - 8, y - 3))
        step = 1 if (not safe and (now // 130) % 2 == 0) else 0
        # bacaklar
        pygame.draw.rect(self.canvas, SPIDER_BLUE, (x - 4, y - 7, 3, 7))
        pygame.draw.rect(self.canvas, SPIDER_BLUE, (x + 1, y - 7 + step, 3, 7 - step))
        # gövde
        pygame.draw.rect(self.canvas, SPIDER_RED, (x - 5, y - 16, 10, 10))
        pygame.draw.rect(self.canvas, SPIDER_BLUE, (x - 5, y - 16, 10, 3))
        # ağ deseni
        pygame.draw.line(self.canvas, (150, 30, 40), (x, y - 16), (x, y - 7))
        pygame.draw.line(self.canvas, (150, 30, 40), (x - 5, y - 11), (x + 4, y - 11))
        # kollar
        pygame.draw.rect(self.canvas, SPIDER_RED, (x - 7, y - 15, 2, 6))
        pygame.draw.rect(self.canvas, SPIDER_RED, (x + 5, y - 15, 2, 6))
        # kafa
        pygame.draw.rect(self.canvas, SPIDER_RED, (x - 4, y - 23, 8, 8))
        if safe:
            # sırtı dönük: siyah örümcek amblemi, göz yok
            pygame.draw.rect(self.canvas, BLACK, (x - 1, y - 21, 2, 4))
            pygame.draw.rect(self.canvas, BLACK, (x - 3, y - 20, 6, 1))
        else:
            pygame.draw.polygon(self.canvas, WHITE, [
                (x - 4, y - 21), (x - 1, y - 22), (x - 1, y - 18), (x - 4, y - 18)])
            pygame.draw.polygon(self.canvas, WHITE, [
                (x + 4, y - 21), (x + 1, y - 22), (x + 1, y - 18), (x + 4, y - 18)])

    def _vision_cone(self, guard, safe: bool) -> None:
        """Bakış konisi zemine düşer: ışık bize bakmıyorsa koşmak serbest.

        Koni karo uzayında kurulur, sonra izometriye çevrilir; böylece
        zeminin perspektifine oturur ve odanın dışına taşmaz.
        """
        step = -1.0 if safe else 1.0      # sırtı dönükken ışık duvara bakar
        length, half = 4.6, 2.8
        pts = [iso(guard.tx, guard.ty)]
        for dx, dy in ((length - half, length + half),
                       (length + half, length - half)):
            pts.append(iso(guard.tx + step * dx, guard.ty + step * dy))
        color = (*SAFE_GREEN, 70) if safe else (*CONE_WARM, 104)
        self.cone_layer.fill((0, 0, 0, 0))
        pygame.draw.polygon(self.cone_layer, color, pts)
        self.cone_layer.blit(self.floor_mask, (0, 0),
                             special_flags=pygame.BLEND_RGBA_MULT)
        self.floor_fx.blit(self.cone_layer, (0, 0))

    # -- ana sahne -------------------------------------------------------
    def _draw_room_scene(self, game, now: int) -> None:
        from app.game import PLAY, TITLE

        self._draw_floor()
        self._draw_walls(now)

        safe = game.is_safe(now) and game.state == PLAY
        guard = game.guard(now)
        gx, gy = iso(guard.tx, guard.ty)
        self._vision_cone(guard, guard.safe)

        px, py, lift = game.player_pos(now)
        sx, sy = iso(px, py)
        sy -= lift * 14

        # sıradaki saklanma noktası: güvenliyken parlar
        if game.state == PLAY and game.step < STEPS_TO_WIN:
            self._next_spot_marker(game, now, safe)
        self.canvas.blit(self.floor_fx, (0, 0))

        # derinliğe göre sırala: arkadaki önce çizilir
        items: list[tuple[float, object]] = []
        for index, (tx, ty, kind) in enumerate(SPOTS):
            has_flag = (kind == "pedestal" and game.step < STEPS_TO_WIN)
            items.append((tx + ty, lambda tx=tx, ty=ty, kind=kind, h=has_flag:
                          self._prop(kind, tx, ty, game.code, now, h)))
        hiding = not game.hopping(now)
        # saklanırken eşyanın arkasından bakar: biraz yukarı kaydırılır
        depth = px + py - (0.9 if hiding else 0.0)
        offset = -4 if hiding else 0
        items.append((depth, lambda: self._draw_player(
            int(sx) + offset, int(sy) + (2 if hiding else 0), now, hiding,
            game.caught_active(now))))
        items.append((guard.tx + guard.ty,
                      lambda: self._draw_guard(int(gx), int(gy), now, guard.safe)))
        for _, draw in sorted(items, key=lambda item: item[0]):
            draw()

        if game.caught_active(now):
            self._draw_web(gx, gy, sx, sy, now)

        self._draw_hud(game, now, safe)
        if game.state == TITLE:
            self._draw_title_overlay(game, now)

    def _next_spot_marker(self, game, now: int, safe: bool) -> None:
        tx, ty, _ = SPOTS[game.step + 1]
        x, y = iso(tx, ty)
        pulse = _pulse(now, 520)
        color = (*SAFE_GREEN, int(70 + 80 * pulse)) if safe else (255, 255, 255, 28)
        radius = 10 + int(pulse * 3)
        pygame.draw.ellipse(self.floor_fx, color,
                            (x - radius, y - radius / 2 - 1, radius * 2, radius))
        if safe:
            # yukarı zıplayan ok: "buraya koş"
            lift = int(pulse * 3)
            top = y - 26 - lift
            pygame.draw.polygon(self.canvas, SAFE_GREEN, [
                (x, top), (x - 5, top + 6), (x + 5, top + 6)])
            pygame.draw.rect(self.canvas, SAFE_GREEN, (x - 2, top + 6, 4, 6))

    def _draw_web(self, gx: float, gy: float, px: float, py: float,
                  now: int) -> None:
        pygame.draw.line(self.canvas, WEB, (gx, gy - 12), (px, py - 10))
        for i in range(1, 5):
            t = i / 5
            x = gx + (px - gx) * t
            y = (gy - 12) + ((py - 10) - (gy - 12)) * t
            pygame.draw.circle(self.canvas, WEB, (int(x), int(y)), 1)
        pygame.draw.circle(self.canvas, WEB, (int(px), int(py - 10)), 4, 1)

    # -- HUD -------------------------------------------------------------
    def _draw_hud(self, game, now: int, safe: bool) -> None:
        # adım noktaları: kaç kez doğru zamanda basıldı
        for i in range(STEPS_TO_WIN):
            x = 8 + i * 8
            done = i < game.step
            pygame.draw.rect(self.canvas, GOLD if done else (70, 64, 90),
                             (x, 8, 6, 6))
            pygame.draw.rect(self.canvas, (36, 32, 52), (x, 8, 6, 6), 1)

        # toplanan bayrak sayısı
        count = len(game.progress.collected)
        rect = pygame.Rect(VIRTUAL[0] - 46, 6, 15, 10)
        flagmod.draw_flag(self.canvas, rect, game.progress.collected[-1]
                          if game.progress.collected else "tr")
        _tiny_text(self.canvas, f"{count}/{len(CODES)}", VIRTUAL[0] - 29, 8, WHITE)

        self._space_hint(now, safe)

    def _space_hint(self, now: int, safe: bool) -> None:
        """Alt ortada boşluk tuşu: yeşilse bas, griyse bekle."""
        w, h = 74, 15
        x = (VIRTUAL[0] - w) // 2
        y = VIRTUAL[1] - 22
        pulse = _pulse(now, 520)
        if safe:
            body = (int(60 + 40 * pulse), int(200 + 40 * pulse), int(120 + 40 * pulse))
            edge = WHITE
            y -= int(pulse * 2)
        else:
            body = (74, 70, 92)
            edge = (110, 104, 130)
        pygame.draw.rect(self.canvas, (24, 22, 34), (x + 1, y + 2, w, h))
        pygame.draw.rect(self.canvas, body, (x, y, w, h))
        pygame.draw.rect(self.canvas, edge, (x, y, w, h), 1)
        pygame.draw.rect(self.canvas, edge, (x + 8, y + 6, w - 16, 3))
        if safe:
            cx = x + w // 2
            top = y - 8 - int(pulse * 2)
            pygame.draw.polygon(self.canvas, SAFE_GREEN, [
                (cx, top), (cx - 5, top + 6), (cx + 5, top + 6)])
        else:
            # bekleme işareti: iki kırmızı çizgi
            cx = x + w // 2
            pygame.draw.rect(self.canvas, DANGER_RED, (cx - 5, y - 7, 3, 6))
            pygame.draw.rect(self.canvas, DANGER_RED, (cx + 2, y - 7, 3, 6))

    def _draw_title_overlay(self, game, now: int) -> None:
        shade = pygame.Surface(VIRTUAL, pygame.SRCALPHA)
        shade.fill((10, 8, 20, 120))
        self.canvas.blit(shade, (0, 0))
        rect = pygame.Rect(VIRTUAL[0] // 2 - 27, 40, 54, 36)
        flagmod.draw_flag(self.canvas, rect, game.code)
        pulse = _pulse(now, 760)
        pygame.draw.rect(self.canvas, (255, 255, 255, 255), rect.inflate(4, 4),
                         1 + int(pulse))
        self._text_center("Bu bayrağı çal!", 86, GOLD)
        self._text_center(flagmod.name_of(game.code), 100, WHITE, small=True)
        self._space_hint(now, True)

    # -- kazanma ---------------------------------------------------------
    def _draw_win(self, game, now: int) -> None:
        self.canvas.fill((26, 22, 44))
        for i in range(0, VIRTUAL[0], 16):
            pygame.draw.line(self.canvas, (32, 28, 54), (i, 0), (i, VIRTUAL[1]))
        self._confetti_step(now)
        rect = pygame.Rect(VIRTUAL[0] // 2 - 60, 34, 120, 80)
        glow = int(_pulse(now, 900) * 6)
        pygame.draw.rect(self.canvas, GOLD, rect.inflate(8 + glow, 8 + glow), 2)
        flagmod.draw_flag(self.canvas, rect, game.code)
        self._text_center(flagmod.name_of(game.code), 124, WHITE)
        self._text_center("Bayrak panona eklendi", 142, SAFE_GREEN, small=True)
        self._space_hint(now, True)

    def _confetti_step(self, now: int) -> None:
        if len(self._confetti) < 40:
            import random
            for _ in range(40 - len(self._confetti)):
                self._confetti.append([random.uniform(0, VIRTUAL[0]),
                                       random.uniform(-VIRTUAL[1], 0),
                                       random.uniform(0.5, 1.6),
                                       random.randrange(5)])
        palette = (GOLD, SAFE_GREEN, (240, 120, 160), WHITE, (120, 190, 255))
        for piece in self._confetti:
            piece[1] += piece[2]
            if piece[1] > VIRTUAL[1]:
                piece[1] = -4
            pygame.draw.rect(self.canvas, palette[int(piece[3])],
                             (int(piece[0]), int(piece[1]), 2, 2))

    def reset_confetti(self) -> None:
        self._confetti.clear()

    # -- pano ------------------------------------------------------------
    def _draw_board(self, game, now: int) -> None:
        self.canvas.fill((22, 20, 36))
        cols, rows = 10, 5
        cell_w, cell_h = 29, 26
        ox = (VIRTUAL[0] - cols * cell_w) // 2
        oy = 22
        self._text_center("BAYRAK PANOM", 8, GOLD, small=True)
        for index, code in enumerate(CODES):
            col, row = index % cols, index // cols
            x = ox + col * cell_w
            y = oy + row * cell_h
            rect = pygame.Rect(x + 2, y + 2, cell_w - 5, cell_h - 9)
            if game.progress.has(code):
                flagmod.draw_flag(self.canvas, rect, code)
                if code == game.new_code:
                    pulse = _pulse(now, 420)
                    pygame.draw.rect(self.canvas, (255, 255, 180),
                                     rect.inflate(4, 4), 1 + int(pulse * 2))
            else:
                pygame.draw.rect(self.canvas, (44, 40, 62), rect)
                pygame.draw.rect(self.canvas, (62, 58, 84), rect, 1)
                # kilit: çocuk "burası henüz boş" diye anlasın
                cx, cy = rect.centerx, rect.centery
                pygame.draw.rect(self.canvas, (96, 90, 120), (cx - 3, cy - 1, 7, 6))
                pygame.draw.circle(self.canvas, (96, 90, 120), (cx, cy - 2), 3, 1)
            if index == game.board_index:
                pygame.draw.rect(self.canvas, WHITE, rect.inflate(5, 5), 1)

        selected = game.board_code()
        label = flagmod.name_of(selected) if game.progress.has(selected) else "?"
        self._text_center(label, VIRTUAL[1] - 32, WHITE, small=True)
        count = len(game.progress.collected)
        _tiny_text(self.canvas, f"{count}/{len(CODES)}", VIRTUAL[0] - 30, 8, GOLD)
        self._space_hint(now, True)

    def _draw_done(self, game, now: int) -> None:
        self.canvas.fill((24, 20, 42))
        self._confetti_step(now)
        self._text_center("BRAVO!", 40, GOLD)
        self._text_center("Bütün bayrakları topladın", 62, WHITE, small=True)
        cols = 10
        for index, code in enumerate(CODES):
            col, row = index % cols, index // cols
            rect = pygame.Rect(16 + col * 29, 84 + row * 16, 24, 13)
            flagmod.draw_flag(self.canvas, rect, code)
        self._space_hint(now, True)

    # -- yazı (ebeveyn için; çocuk sesi dinler) ---------------------------
    def _text_center(self, text: str, y: int, color, small: bool = False) -> None:
        font = self.small_font if small else self.font
        if font is None:
            return
        surf = font.render(text, False, color)
        self.canvas.blit(surf, ((VIRTUAL[0] - surf.get_width()) // 2, y))
