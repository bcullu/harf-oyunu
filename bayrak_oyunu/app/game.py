"""Oyun mantığı: devriye döngüsü, saklanma noktaları, zamanlama.

Burada pygame yok; her şey milisaniye damgalarıyla hesaplanır. Böylece
mantık ekransız test edilebilir ve çizim katmanı sadece "şu anda neresi
nerede" diye sorar.

Oda, çocuk için okunması kolay ve ezberlenebilir tek bir ritim kurar:

    tehlike  ->  örümcek odayı tarar, bize bakıyor
    güvenli  ->  örümcek duvara döner, sırtı bize dönük

Güvenli pencerede boşluğa basmak bir sonraki saklanma noktasına atlatır.
Tehlikede basmak yakalatır; ceza bir adım geri gitmektir (oyun bitmez,
5 yaşındaki bir çocuk için cesaret kırıcı olmasın diye).
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.flags import CODES

# Saklanma noktaları: (tx, ty) izometrik kare koordinatı ve prop türü.
# 0 kapı (başlangıç), son eleman bayrağın durduğu kaide.
SPOTS: list[tuple[float, float, str]] = [
    (7.0, 7.0, "door"),
    (6.6, 4.8, "crate"),
    (3.9, 6.1, "plant"),
    (4.6, 2.9, "barrel"),
    (1.9, 4.2, "column"),
    (1.0, 1.0, "pedestal"),
]
STEPS_TO_WIN = len(SPOTS) - 1  # 5 doğru basış

# Örümceğin devriye hattı (izometrik kare koordinatı)
PATROL_A = (1.4, 6.4)
PATROL_B = (6.4, 1.4)

# Zamanlama (ms)
DANGER_MS = 2500        # örümcek odayı tarıyor
SAFE_BASE = 2100        # ilk adımda güvenli pencere
SAFE_MIN = 1150         # en zor durumda bile bu kadar süre var
SAFE_PER_STEP = 130     # her adımda pencere biraz daralır
SAFE_PER_FLAG = 8       # biriken her bayrakla biraz daha
HOP_MS = 420            # bir saklanma noktasından diğerine sıçrama
CAUGHT_MS = 1200        # yakalanma animasyonu
GRAB_MS = 900           # bayrağı alma animasyonu

# Durumlar
TITLE = "title"
PLAY = "play"
WIN = "win"
BOARD = "board"
DONE = "done"

# update()/press_space() dönen olaylar; main.py bunları sese çevirir
EV_SAFE = "safe"
EV_DANGER = "danger"
EV_HOP = "hop"
EV_CAUGHT = "caught"
EV_NEAR = "near"
EV_GRAB = "grab"
EV_WIN = "win"
EV_BOARD = "board"
EV_START = "start"
EV_ALL_DONE = "all_done"


@dataclass
class GuardState:
    """Örümceğin o andaki hali (çizim katmanı için)."""
    tx: float
    ty: float
    safe: bool          # sırtı bize dönük mü
    facing_down: bool   # kameraya doğru mu yürüyor (bakış konisinin yönü)
    phase_ratio: float  # içinde bulunulan evrenin ne kadarı geçti (0..1)


class Game:
    def __init__(self, progress, rng: random.Random | None = None,
                 now: int = 0):
        self.progress = progress
        self.rng = rng or random.Random()
        self.state = TITLE
        self.code = self._pick_code()
        self.step = 0
        self.caught_flash = 0      # kaç kez yakalandı (sadece gösterim)
        self.new_code: str | None = None   # panoda parlayacak yeni bayrak
        self.board_index = 0

        # devriye döngüsü
        self.cycle_start = now
        self.direction = 1          # 1: A->B, -1: B->A
        self.safe_ms = self._safe_window()
        self._last_safe: bool | None = None

        # animasyonlar
        self.hop_from = 0
        self.hop_start = -10_000
        self.caught_start = -10_000
        self.grab_start = -10_000
        self.grab_pending = False

    # -- kurulum ---------------------------------------------------------
    def _pick_code(self) -> str:
        return self.progress.pick_next(self.rng)

    def _safe_window(self) -> int:
        collected = len(self.progress.collected)
        return max(SAFE_MIN, SAFE_BASE - SAFE_PER_STEP * self.step
                   - SAFE_PER_FLAG * collected)

    @property
    def cycle_ms(self) -> int:
        return DANGER_MS + self.safe_ms

    # -- devriye ---------------------------------------------------------
    def _advance_cycles(self, now: int) -> None:
        """Geçen tam devriye turlarını işler ve yönü çevirir."""
        guard = 0
        while now - self.cycle_start >= self.cycle_ms and guard < 1000:
            self.cycle_start += self.cycle_ms
            self.direction *= -1
            self.safe_ms = self._safe_window()
            guard += 1

    def is_safe(self, now: int) -> bool:
        return (now - self.cycle_start) >= DANGER_MS

    def guard(self, now: int) -> GuardState:
        elapsed = max(0, now - self.cycle_start)
        a, b = (PATROL_A, PATROL_B) if self.direction > 0 else (PATROL_B, PATROL_A)
        if elapsed < DANGER_MS:
            ratio = elapsed / DANGER_MS
            # yumuşak hızlanma/yavaşlama: hareket göz için daha okunur
            eased = 0.5 - 0.5 * _cos_pi(ratio)
            tx = a[0] + (b[0] - a[0]) * eased
            ty = a[1] + (b[1] - a[1]) * eased
            return GuardState(tx, ty, False, True, ratio)
        ratio = (elapsed - DANGER_MS) / max(1, self.safe_ms)
        return GuardState(b[0], b[1], True, False, min(1.0, ratio))

    # -- oyuncu ----------------------------------------------------------
    def hopping(self, now: int) -> bool:
        return 0 <= now - self.hop_start < HOP_MS

    def hop_pending(self, now: int) -> bool:
        """Sıçrama planlandı ama henüz başlamadı (yakalanınca geri dönüş)."""
        return now < self.hop_start < now + CAUGHT_MS

    def caught_active(self, now: int) -> bool:
        return 0 <= now - self.caught_start < CAUGHT_MS

    def grabbing(self, now: int) -> bool:
        """Son sıçrama ve bayrağı kapma anı: tuşlar bu sırada kilitli."""
        return self.grab_pending and now < self.grab_start + GRAB_MS

    def player_pos(self, now: int) -> tuple[float, float, float]:
        """(tx, ty, yükseklik). Yükseklik sıçrama yayı için 0..1."""
        start = SPOTS[self.hop_from]
        target = SPOTS[self.step]
        if self.hop_pending(now):
            return start[0], start[1], 0.0
        if not self.hopping(now):
            return target[0], target[1], 0.0
        ratio = (now - self.hop_start) / HOP_MS
        tx = start[0] + (target[0] - start[0]) * ratio
        ty = start[1] + (target[1] - start[1]) * ratio
        return tx, ty, _arc(ratio)

    # -- olaylar ---------------------------------------------------------
    def update(self, now: int) -> list[str]:
        """Zaman ilerledi. Ses tetikleyen olayları döndürür."""
        events: list[str] = []
        self._advance_cycles(now)

        if self.state == PLAY:
            safe = self.is_safe(now)
            if self._last_safe is None:
                self._last_safe = safe
            elif safe != self._last_safe:
                events.append(EV_SAFE if safe else EV_DANGER)
                self._last_safe = safe

            if self.grab_pending and now >= self.grab_start + GRAB_MS:
                self.grab_pending = False
                events.append(self._finish_win())
        return events

    def press_space(self, now: int) -> list[str]:
        """Tek tuşlu oyun: boşluk her ekranda doğru şeyi yapar."""
        if self.state == TITLE:
            return self.start_run(now)
        if self.state == PLAY:
            return self._try_hop(now)
        if self.state == WIN:
            return self.show_board()
        if self.state == BOARD:
            return self.next_round(now)
        if self.state == DONE:
            return self.show_board()
        return []

    def start_run(self, now: int) -> list[str]:
        self.state = PLAY
        self.step = 0
        self.cycle_start = now
        self.direction = 1
        self.safe_ms = self._safe_window()
        self._last_safe = None
        self.hop_start = -10_000
        self.caught_start = -10_000
        self.grab_start = -10_000
        self.grab_pending = False
        self.hop_from = 0
        return [EV_START]

    def _try_hop(self, now: int) -> list[str]:
        # tuşa basıldığı an devriye turunu da ilerlet: update() ile press_space()
        # arasında bir tur kapanmışsa "güvenli mi" sorusu yanlış cevaplanmasın
        self._advance_cycles(now)
        if self.hopping(now) or self.caught_active(now) or self.grabbing(now):
            return []           # animasyon sürerken tuş yok sayılır
        if self.step >= STEPS_TO_WIN:
            return []
        if not self.is_safe(now):
            return self._catch(now)

        self.hop_from = self.step
        self.step += 1
        self.hop_start = now
        self.safe_ms = self._safe_window()
        events = [EV_HOP]
        if self.step >= STEPS_TO_WIN:
            self.grab_start = now + HOP_MS
            self.grab_pending = True
            events.append(EV_GRAB)
        elif self.step == STEPS_TO_WIN - 1:
            events.append(EV_NEAR)
        return events

    def _catch(self, now: int) -> list[str]:
        self.caught_start = now
        self.caught_flash += 1
        if self.step > 0:
            self.hop_from = self.step
            self.step -= 1
            # ağ önce gelir, çocuk ne olduğunu görsün diye geri dönüş gecikir
            self.hop_start = now + 450
        return [EV_CAUGHT]

    def _finish_win(self) -> str:
        self.state = WIN
        self.new_code = self.code if not self.progress.has(self.code) else None
        self.progress.add(self.code)
        return EV_WIN

    # -- pano ------------------------------------------------------------
    def show_board(self) -> list[str]:
        self.state = BOARD
        if self.new_code and self.new_code in CODES:
            self.board_index = CODES.index(self.new_code)
        return [EV_BOARD]

    def move_board(self, dx: int, dy: int, columns: int = 10) -> bool:
        index = self.board_index + dx + dy * columns
        if 0 <= index < len(CODES):
            self.board_index = index
            return True
        return False

    def board_code(self) -> str:
        return CODES[self.board_index]

    def next_round(self, now: int) -> list[str]:
        """Panodan yeni oyuna. Hepsi toplandıysa kutlama ekranına."""
        self.new_code = None
        if self.progress.complete():
            self.state = DONE
            return [EV_ALL_DONE]
        self.code = self._pick_code()
        self.state = TITLE
        self.step = 0
        self.cycle_start = now
        return []


def _cos_pi(ratio: float) -> float:
    import math
    return math.cos(math.pi * max(0.0, min(1.0, ratio)))


def _arc(ratio: float) -> float:
    """0 -> 1 -> 0 arası sıçrama yayı."""
    ratio = max(0.0, min(1.0, ratio))
    return 4 * ratio * (1 - ratio)
