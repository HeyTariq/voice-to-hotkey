import pytest

from voice_to_hotkey import config


def test_template_loads_with_defaults(tmp_path):
    file = tmp_path / "config.toml"
    file.write_text(config.TEMPLATE)
    cfg = config.load(file)
    assert cfg.phrases == ["clip that"]
    assert cfg.hotkey == ["f8"]
    assert cfg.start_listening is True


def test_missing_settings_fall_back_to_defaults(tmp_path):
    file = tmp_path / "config.toml"
    file.write_text('hotkey = "alt+f10"\n')
    cfg = config.load(file)
    assert cfg.hotkey == ["alt", "f10"]
    assert cfg.phrases == ["clip that"]


def test_phrases_are_normalized(tmp_path):
    file = tmp_path / "config.toml"
    file.write_text('phrases = ["  Save   THAT ", ""]\n')
    assert config.load(file).phrases == ["save that"]


@pytest.mark.parametrize("text", [
    "phrases = [",
    'hotkey = "ctrl+banana"',
    "phrases = []",
    'cooldown_seconds = "soon"',
    "phrases = [1]",
])
def test_bad_config_raises_config_error(tmp_path, text):
    file = tmp_path / "config.toml"
    file.write_text(text + "\n")
    with pytest.raises(config.ConfigError):
        config.load(file)


def test_create_and_set_value_keep_comments(tmp_path):
    file = tmp_path / "sub" / "config.toml"
    config.create(file, phrases=["save it"], hotkey="ctrl+s", start_listening=False)
    file.write_text(file.read_text() + "# my note\n")
    config.set_value(file, "start_listening", True)

    text = file.read_text()
    assert "# Hotkey to press" in text
    assert "# my note" in text
    cfg = config.load(file)
    assert cfg.phrases == ["save it"]
    assert cfg.hotkey == ["ctrl", "s"]
    assert cfg.start_listening is True
