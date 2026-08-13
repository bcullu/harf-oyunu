"""Oyun modu durum makinesi (pygame gerektirmez)."""

import random

import pytest

from app.game_modes import (CELEBRATE, CORRECT, PROMPT, SAY, SHOW, STAR,
                            STARS_TO_WIN, WRONG, FindLetterMode, FreeMode,
                            build_modes)

CHARS = list("ABCÇDEFG")


def kinds(actions):
    return [a.kind for a in actions]


def only(actions, kind):
    return [a.value for a in actions if a.kind == kind]


# --- serbest mod ------------------------------------------------------------

def test_free_mode_shows_and_says():
    mode = FreeMode(CHARS)
    actions = mode.on_char("Ç")
    assert kinds(actions) == [SHOW, SAY]
    assert only(actions, SHOW) == ["Ç"] and only(actions, SAY) == ["Ç"]


def test_free_mode_has_no_prompt_or_stars():
    mode = FreeMode(CHARS)
    assert mode.enter() == []
    assert mode.shows_prompt is False


# --- Harfi Bul --------------------------------------------------------------

@pytest.fixture
def find():
    mode = FindLetterMode(CHARS, random.Random(42))
    mode.enter()
    return mode


def test_enter_asks_for_a_target():
    mode = FindLetterMode(CHARS, random.Random(1))
    actions = mode.enter()
    assert kinds(actions) == [PROMPT]
    assert actions[0].value in CHARS
    assert mode.stars == 0


def test_correct_answer_gives_star_and_new_target(find):
    first = find.target
    actions = find.on_char(first)
    assert kinds(actions) == [SHOW, CORRECT, STAR, PROMPT]
    assert find.stars == 1
    assert find.target != first  # aynı hedef üst üste gelmez


def test_wrong_answer_is_gentle_and_keeps_target(find):
    target = find.target
    wrong = next(c for c in CHARS if c != target)
    actions = find.on_char(wrong)
    assert kinds(actions) == [SHOW, WRONG, PROMPT]
    assert find.stars == 0          # ceza yok, yıldız da yok
    assert find.target == target    # hedef değişmedi


def test_five_stars_triggers_celebration(find):
    for step in range(STARS_TO_WIN):
        actions = find.on_char(find.target)
        assert find.stars == step + 1
    assert CELEBRATE in kinds(actions)
    assert find.celebrating is True


def test_keys_ignored_during_celebration(find):
    for _ in range(STARS_TO_WIN):
        find.on_char(find.target)
    assert find.on_char("A") == []


def test_celebration_end_resets_and_starts_new_round(find):
    for _ in range(STARS_TO_WIN):
        find.on_char(find.target)
    actions = find.on_celebration_end()
    assert kinds(actions) == [STAR, PROMPT]
    assert find.stars == 0
    assert find.celebrating is False


def test_target_comes_from_current_char_set(find):
    # F3 ile rakamlara geçilirse sonraki hedefler de rakam olmalı
    find.set_chars(list("0123456789"))
    for _ in range(4):
        actions = find.on_char(find.target)
        for value in only(actions, PROMPT):
            assert value in "0123456789"
        if find.celebrating:
            find.on_celebration_end()


def test_set_chars_picks_new_target_from_new_set(find):
    actions = find.set_chars(list("0123456789"))
    assert kinds(actions) == [PROMPT]
    assert find.target in "0123456789"


def test_set_chars_keeps_valid_target(find):
    target = find.target
    assert find.set_chars(CHARS) == []
    assert find.target == target


def test_single_char_set_repeats_same_target():
    mode = FindLetterMode(["A"], random.Random(0))
    mode.enter()
    assert mode.target == "A"
    mode.on_char("A")
    assert mode.target == "A"  # başka seçenek yok, kilitlenmemeli


def test_empty_char_set_does_not_crash():
    mode = FindLetterMode([], random.Random(0))
    assert mode.enter() == []
    assert mode.on_char("A") == [] or kinds(mode.on_char("A")) == [SHOW, WRONG, PROMPT]


def test_targets_vary_over_many_rounds():
    mode = FindLetterMode(CHARS, random.Random(7))
    mode.enter()
    seen = set()
    for _ in range(40):
        seen.add(mode.target)
        mode.on_char(mode.target)
        if mode.celebrating:
            mode.on_celebration_end()
    assert len(seen) > 1


def test_build_modes_order():
    modes = build_modes(CHARS)
    assert [m.name for m in modes] == ["free", "find"]
