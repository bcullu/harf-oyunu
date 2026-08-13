"""Oyun modları: saf durum makinesi (pygame'e bağlı değil).

Her mod tuş girdisine karşılık bir Action listesi döndürür; ekranı çizmek ve
sesi çalmak main.py'nin işi. Böylece oyun mantığı ekransız test edilebilir.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Action türleri
SHOW = "show"            # value: gösterilecek karakter
SAY = "say"              # value: seslendirilecek karakter
PROMPT = "prompt"        # value: bulunması istenen karakter
CORRECT = "correct"      # doğru cevap
WRONG = "wrong"          # yanlış cevap (ceza yok)
STAR = "star"            # value: toplam yıldız sayısı
CELEBRATE = "celebrate"  # kutlama ekranı

STARS_TO_WIN = 5


@dataclass
class Action:
    kind: str
    value: object = None


class FreeMode:
    """Serbest mod: basılan tuş büyük görünür ve seslendirilir."""

    name = "free"
    ui_key = "free_mode"
    shows_prompt = False

    def __init__(self, chars: list[str]):
        self.chars = chars

    def set_chars(self, chars: list[str]) -> list[Action]:
        self.chars = chars
        return []

    def enter(self) -> list[Action]:
        return []

    def on_char(self, char: str) -> list[Action]:
        return [Action(SHOW, char), Action(SAY, char)]

    def on_celebration_end(self) -> list[Action]:
        return []


class FindLetterMode:
    """'Harfi Bul': istenen harfe basılınca yıldız kazanılır.

    Yanlışta ceza yok; hedef değişmez, nazikçe tekrar denemesi istenir.
    """

    name = "find"
    ui_key = "find_mode"
    shows_prompt = True

    def __init__(self, chars: list[str], rng: random.Random | None = None):
        self.chars = list(chars)
        self.rng = rng or random.Random()
        self.target: str | None = None
        self.stars = 0
        self.celebrating = False

    def set_chars(self, chars: list[str]) -> list[Action]:
        """Harf seti değişirse (F3) yeni setten yeni bir hedef seçilir."""
        self.chars = list(chars)
        if self.target not in self.chars:
            self.target = None
            return self._new_round()
        return []

    def enter(self) -> list[Action]:
        self.stars = 0
        self.celebrating = False
        return self._new_round()

    def _new_round(self) -> list[Action]:
        if not self.chars:
            return []
        choices = [c for c in self.chars if c != self.target] or self.chars
        self.target = self.rng.choice(choices)
        return [Action(PROMPT, self.target)]

    def on_char(self, char: str) -> list[Action]:
        if self.celebrating:
            return []  # kutlama sürerken tuşlar yok sayılır
        if self.target is None:  # hedef yoksa (boş set) önce tur başlat
            return self._new_round()
        if char == self.target:
            self.stars += 1
            actions = [Action(SHOW, char), Action(CORRECT), Action(STAR, self.stars)]
            if self.stars >= STARS_TO_WIN:
                self.celebrating = True
                actions.append(Action(CELEBRATE))
            else:
                actions.extend(self._new_round())
            return actions
        return [Action(SHOW, char), Action(WRONG), Action(PROMPT, self.target)]

    def on_celebration_end(self) -> list[Action]:
        """Kutlama bitince yıldızlar sıfırlanır ve yeni tur başlar."""
        self.celebrating = False
        self.stars = 0
        return [Action(STAR, 0)] + self._new_round()


def build_modes(chars: list[str], rng: random.Random | None = None) -> list:
    """F2 ile sırayla dolaşılan mod listesi."""
    return [FreeMode(chars), FindLetterMode(chars, rng)]
