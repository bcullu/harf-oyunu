import pytest

from app.text_tr import tr_lower, tr_upper, upper_for_lang


@pytest.mark.parametrize("lower,upper", [
    ("i", "İ"),
    ("ı", "I"),
    ("ğ", "Ğ"),
    ("ü", "Ü"),
    ("ş", "Ş"),
    ("ö", "Ö"),
    ("ç", "Ç"),
    ("a", "A"),
    ("z", "Z"),
])
def test_tr_upper_single(lower, upper):
    assert tr_upper(lower) == upper


@pytest.mark.parametrize("upper,lower", [
    ("İ", "i"),
    ("I", "ı"),
    ("Ğ", "ğ"),
    ("Ş", "ş"),
    ("A", "a"),
])
def test_tr_lower_single(upper, lower):
    assert tr_lower(upper) == lower


def test_python_default_is_wrong_but_ours_is_right():
    # Python'un kendi upper()'ı Türkçe için hatalı; regresyon koruması
    assert "i".upper() == "I"
    assert tr_upper("i") == "İ"


def test_roundtrip_all_letters():
    from app.config import load_language
    letters = load_language("tr").letters
    for ch in letters:
        assert tr_upper(tr_lower(ch)) == ch


def test_words():
    assert tr_upper("ısırgan") == "ISIRGAN"
    assert tr_upper("iğne") == "İĞNE"
    assert tr_lower("İSTANBUL") == "istanbul"


def test_upper_for_lang():
    assert upper_for_lang("i", "tr") == "İ"
    assert upper_for_lang("i", "en") == "I"
