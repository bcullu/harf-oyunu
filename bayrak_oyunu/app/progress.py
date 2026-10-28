"""Kazanılmış bayrakların ve ebeveyn ayarlarının diskte tutulması.

progress.json bozuk ya da eksikse oyun sıfırdan başlar, çökmez.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from app.flags import CODES

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_PATH = PROJECT_ROOT / "progress.json"

DEFAULT_VOLUME = 0.9


class Progress:
    def __init__(self, collected=None, volume: float = DEFAULT_VOLUME,
                 path: Path = PROGRESS_PATH):
        self.path = Path(path)
        known = set(CODES)
        seen: list[str] = []
        for code in (collected or []):
            if code in known and code not in seen:
                seen.append(code)
        self.collected = seen
        self.volume = _clamp_volume(volume)

    # -- disk ------------------------------------------------------------
    @classmethod
    def load(cls, path: Path = PROGRESS_PATH) -> "Progress":
        path = Path(path)
        try:
            with path.open(encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                raw = {}
        except (OSError, json.JSONDecodeError):
            raw = {}
        collected = raw.get("collected")
        if not isinstance(collected, list):
            collected = []
        try:
            volume = float(raw.get("volume", DEFAULT_VOLUME))
        except (TypeError, ValueError):
            volume = DEFAULT_VOLUME
        return cls(collected, volume, path)

    def save(self) -> bool:
        """Yazılamazsa oyun durmasın diye sessizce False döner."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as fh:
                json.dump({"collected": self.collected,
                           "volume": round(self.volume, 2)},
                          fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            return True
        except OSError:
            return False

    # -- bayraklar -------------------------------------------------------
    def has(self, code: str) -> bool:
        return code in self.collected

    def remaining(self) -> list[str]:
        return [code for code in CODES if code not in self.collected]

    def complete(self) -> bool:
        return not self.remaining()

    def add(self, code: str) -> bool:
        """Yeni bayrağı panoya ekler. Zaten varsa False döner."""
        if code not in CODES or code in self.collected:
            return False
        self.collected.append(code)
        self.save()
        return True

    def pick_next(self, rng: random.Random | None = None) -> str:
        """Bir sonraki oyunun bayrağı: henüz kazanılmamışlardan biri.

        Hepsi toplanmışsa (çocuk oynamaya devam etsin diye) rastgele biri.
        """
        rng = rng or random
        pool = self.remaining() or list(CODES)
        return rng.choice(pool)

    def reset(self) -> None:
        self.collected = []
        self.save()

    def change_volume(self, delta: float) -> float:
        self.volume = _clamp_volume(self.volume + delta)
        self.save()
        return self.volume


def _clamp_volume(value) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError):
        value = DEFAULT_VOLUME
    return round(min(1.0, max(0.0, value)), 2)
