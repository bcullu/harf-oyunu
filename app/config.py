"""Dil verisi yükleme ve ebeveyn ayarlarının (config.json) yönetimi."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "config.json"

SUPPORTED_LANGUAGES = ("tr", "en")

# Ebeveyn ayarları
CHAR_SETS = ("letters", "digits", "both")
FONT_SCALES = (0.45, 0.62, 0.80)  # F4 ile sırayla dolaşılır
VOLUME_STEP = 0.1
MIN_FONT_SCALE, MAX_FONT_SCALE = 0.2, 0.95

DEFAULTS = {
    "language": "tr",
    "volume": 0.9,
    "char_set": "both",
    "font_scale": 0.62,
}


class LanguageData:
    """data/<code>.json içeriğini sarmalayan basit veri sınıfı."""

    def __init__(self, payload: dict):
        self.code: str = payload["code"]
        self.name: str = payload["name"]
        self.letters: list[str] = payload["letters"]
        self.digits: list[str] = payload["digits"]
        self.phonetics: dict[str, str] = payload["phonetics"]
        self.phrases: dict[str, str] = payload.get("phrases", {})
        self.ui: dict[str, str] = payload.get("ui", {})

    def charset(self, kind: str = "both") -> list[str]:
        """kind: letters | digits | both"""
        if kind == "letters":
            return list(self.letters)
        if kind == "digits":
            return list(self.digits)
        return list(self.letters) + list(self.digits)

    def all_speech_keys(self) -> list[str]:
        """Seslendirilmesi gereken tüm anahtarlar (build_audio.py bunu kullanır)."""
        return list(self.phonetics.keys()) + [f"phrase.{k}" for k in self.phrases]


class Config:
    """config.json içeriği. Bozuk/eksik alanlar sessizce varsayılana döner."""

    def __init__(self, values: dict | None = None, path: Path = CONFIG_PATH):
        self.path = Path(path)
        self._values = validate(values or {})

    # -- disk ------------------------------------------------------------
    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        path = Path(path)
        try:
            with path.open(encoding="utf-8") as fh:
                raw = json.load(fh)
            if not isinstance(raw, dict):
                raw = {}
        except (OSError, json.JSONDecodeError):
            raw = {}  # dosya yok ya da bozuk: varsayılanlarla başla
        return cls(raw, path)

    def save(self) -> bool:
        """Ayarları diske yazar. Yazılamazsa oyun durmasın diye False döner."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as fh:
                json.dump(self._values, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            return True
        except OSError:
            return False

    def as_dict(self) -> dict:
        return dict(self._values)

    # -- alanlar ---------------------------------------------------------
    @property
    def language(self) -> str:
        return self._values["language"]

    @language.setter
    def language(self, code: str) -> None:
        if code in SUPPORTED_LANGUAGES:
            self._values["language"] = code

    @property
    def volume(self) -> float:
        return self._values["volume"]

    @volume.setter
    def volume(self, value: float) -> None:
        self._values["volume"] = round(min(1.0, max(0.0, float(value))), 2)

    @property
    def char_set(self) -> str:
        return self._values["char_set"]

    @char_set.setter
    def char_set(self, value: str) -> None:
        if value in CHAR_SETS:
            self._values["char_set"] = value

    @property
    def font_scale(self) -> float:
        return self._values["font_scale"]

    @font_scale.setter
    def font_scale(self, value: float) -> None:
        self._values["font_scale"] = round(
            min(MAX_FONT_SCALE, max(MIN_FONT_SCALE, float(value))), 2)

    # -- ebeveyn kısayollarının kullandığı geçişler -----------------------
    def toggle_language(self) -> str:
        index = SUPPORTED_LANGUAGES.index(self.language)
        self.language = SUPPORTED_LANGUAGES[(index + 1) % len(SUPPORTED_LANGUAGES)]
        return self.language

    def cycle_char_set(self) -> str:
        index = CHAR_SETS.index(self.char_set)
        self.char_set = CHAR_SETS[(index + 1) % len(CHAR_SETS)]
        return self.char_set

    def cycle_font_scale(self) -> float:
        # Mevcut değere en yakın kademeden bir sonrakine geç
        nearest = min(range(len(FONT_SCALES)),
                      key=lambda i: abs(FONT_SCALES[i] - self.font_scale))
        self.font_scale = FONT_SCALES[(nearest + 1) % len(FONT_SCALES)]
        return self.font_scale

    def change_volume(self, delta: float) -> float:
        self.volume = self.volume + delta
        return self.volume


def validate(raw: dict) -> dict:
    """Bilinmeyen alanları atar, hatalı değerleri varsayılana çevirir."""
    values = dict(DEFAULTS)
    if raw.get("language") in SUPPORTED_LANGUAGES:
        values["language"] = raw["language"]
    if raw.get("char_set") in CHAR_SETS:
        values["char_set"] = raw["char_set"]
    try:
        values["volume"] = round(min(1.0, max(0.0, float(raw["volume"]))), 2)
    except (KeyError, TypeError, ValueError):
        pass
    try:
        values["font_scale"] = round(
            min(MAX_FONT_SCALE, max(MIN_FONT_SCALE, float(raw["font_scale"]))), 2)
    except (KeyError, TypeError, ValueError):
        pass
    return values


def load_language(code: str) -> LanguageData:
    """Dil verisini diskten okur. Bilinmeyen kod için ValueError atar."""
    if code not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Desteklenmeyen dil kodu: {code}")
    path = DATA_DIR / f"{code}.json"
    with path.open(encoding="utf-8") as fh:
        return LanguageData(json.load(fh))
