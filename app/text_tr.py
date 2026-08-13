"""Türkçeye özel büyük/küçük harf dönüşümleri.

Python'un str.upper()/lower() metotları Türkçe için yanlıştır:
    "i".upper()  -> "I"   (doğrusu "İ")
    "İ".lower()  -> "i̇"   (birleşik nokta ekler, doğrusu "i")
Bu modül doğru eşlemeyi yapar.
"""

# Küçük -> büyük özel durumlar (diğer harflerde str.upper doğru çalışır)
_UPPER_MAP = {"i": "İ", "ı": "I"}

# Büyük -> küçük özel durumlar
_LOWER_MAP = {"İ": "i", "I": "ı"}


def tr_upper(text: str) -> str:
    """Türkçe kurallarına göre büyük harfe çevirir."""
    return "".join(_UPPER_MAP.get(ch, ch.upper()) for ch in text)


def tr_lower(text: str) -> str:
    """Türkçe kurallarına göre küçük harfe çevirir."""
    return "".join(_LOWER_MAP.get(ch, ch.lower()) for ch in text)


def upper_for_lang(text: str, lang_code: str) -> str:
    """Dile göre doğru büyük harf dönüşümünü seçer."""
    return tr_upper(text) if lang_code == "tr" else text.upper()
