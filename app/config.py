"""Dil verisi yükleme ve (M3'te) config.json yönetimi."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

SUPPORTED_LANGUAGES = ("tr", "en")


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


def load_language(code: str) -> LanguageData:
    """Dil verisini diskten okur. Bilinmeyen kod için ValueError atar."""
    if code not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Desteklenmeyen dil kodu: {code}")
    path = DATA_DIR / f"{code}.json"
    with path.open(encoding="utf-8") as fh:
        return LanguageData(json.load(fh))
