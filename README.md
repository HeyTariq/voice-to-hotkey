# ok-garmin

A tray app that listens to your mic and presses a key when it hears a wake phrase. The default phrase is the German Garmin dash cam command "OK Garmin, Video speichern", and the default key is F8.

Recognition is fully offline, using [Vosk](https://alphacephei.com/vosk/) with the small German model.

## Requirements

- Linux with PipeWire (`pw-record` captures the mic)
- Write access to `/dev/uinput` for the virtual keyboard. Most desktops grant this to the logged-in user already. If yours doesn't, add a udev rule such as `KERNEL=="uinput", GROUP="input", MODE="0660"` and add yourself to the `input` group.

## Install

```sh
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Run

```sh
.venv/bin/ok-garmin
```

The first run downloads the speech model (about 45 MB) to `~/.local/share/ok-garmin/models/` and writes a config to `~/.config/ok-garmin/config.toml`.

The tray menu has:

- **Listening**: pause or resume the mic
- **Start on login**: adds or removes an autostart entry
- **Open config**: opens the config file
- **Quit**

## Config

Edit `~/.config/ok-garmin/config.toml` and restart the app.

| Setting | Default | What it does |
| --- | --- | --- |
| `phrases` | spellings of "ok garmin video speichern" | Any of these triggers the key press |
| `key` | `KEY_F8` | Linux input event name of the key to press |
| `model` | `vosk-model-small-de-0.15` | Vosk model to use |
| `device` | empty (default mic) | PipeWire source name to listen to |
| `cooldown_seconds` | `3` | Ignore the phrase this long after a trigger |
| `min_confidence` | `0.7` | Lowest per-word confidence that still counts |

### Changing the phrase

Every word in a phrase has to exist in the model's vocabulary. Unknown words get dropped silently, and that phrase will never match. The small German model doesn't know "garmin", which is why the defaults use sound-alikes like "karmin" and "carmen". If a new phrase never triggers, try other spellings of the unusual words, or switch `model` to a larger one.

Key names come from the Linux input headers: `KEY_F8`, `KEY_SPACE`, `KEY_ENTER`, `KEY_A`, and so on.
