from voice_to_hotkey.listener import matches


def words(*pairs):
    return [{"word": w, "conf": c} for w, c in pairs]


def test_matches_phrase_in_order():
    heard = words(("[unk]", 1.0), ("clip", 0.9), ("that", 0.95))
    assert matches(heard, ["clip that"], 0.7)


def test_rejects_wrong_order():
    assert not matches(words(("that", 1.0), ("clip", 1.0)), ["clip that"], 0.7)


def test_rejects_low_confidence():
    assert not matches(words(("clip", 0.5), ("that", 1.0)), ["clip that"], 0.7)


def test_any_phrase_matches():
    assert matches(words(("save", 1.0), ("it", 1.0)), ["clip that", "save it"], 0.7)
