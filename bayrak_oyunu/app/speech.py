"""Seslendirilecek Türkçe metinler.

Oyun ekranında neredeyse hiç yazı yok: çocuk okuma bilmiyor, her şeyi
resim ve ses anlatıyor. Bu tablo hem ses üretiminde (scripts/build_audio.py)
hem de testlerde kullanılır.
"""

from __future__ import annotations

from app.audio import name_key, win_key
from app.flags import FLAGS

# Oyunun anlatıcı cümleleri
PHRASES = {
    "intro": "Hazır mısın? Boşluk tuşuna bas.",
    "watch": "Örümcek arkasını dönünce boşluk tuşuna bas.",
    "praise_1": "Harika!",
    "praise_2": "Süper!",
    "praise_3": "Çok iyi!",
    "caught": "Yakalandın! Geri dön.",
    "near": "Bayrak çok yakın!",
    "board": "İşte bayrak panon.",
    "again": "Yeni bayrak için boşluk tuşuna bas.",
    "all_done": "Bravo! Bütün bayrakları topladın!",
}

PRAISE_KEYS = ("praise_1", "praise_2", "praise_3")


def speech_table() -> dict[str, str]:
    """Üretilecek bütün konuşma dosyaları: anahtar -> metin."""
    table = {f"phrase_{key}": text for key, text in PHRASES.items()}
    for code, name, _ in FLAGS:
        table[name_key(code)] = name
        table[win_key(code)] = f"Aferin! Bu, {name} bayrağı."
    return table
