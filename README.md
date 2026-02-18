# arpi — Vision Server

Pi Zero 2W camera + OpenAI Vision, served over HTTP for Quest 3 AR display.

## How It Works

1. Pi runs an HTTP server (`app.py`).
2. Physical button press triggers: camera capture → OpenAI Vision API → store result.
3. Unity polls `/health` and `/result` to display the answer in AR.

## Architecture

```
config.py       ← Env-based secrets/hardware config
prompts.py      ← Prompt dataclass registry (edit here to change prompts)
camera.py       ← Pi camera abstraction (picamera2 / legacy)
analyzer.py     ← Stateless OpenAI Vision API client
state.py        ← Thread-safe application state
button.py       ← HID button listener (background thread)
server.py       ← Flask HTTP server (/health, /result, /prompts)
app.py          ← Entry point — wires everything together
```

## API

| Endpoint   | Method | Response                                                                                                  |
| ---------- | ------ | --------------------------------------------------------------------------------------------------------- |
| `/health`  | GET    | `{ "status": "ok", "camera": bool, "button": bool, "uptime_s": int }`                                     |
| `/result`  | GET    | `{ "status": "idle"\|"processing"\|"ready"\|"error", "text": "...", "timestamp": "...", "error": "..." }` |
| `/prompts` | GET    | `{ "default": "...", "available": [...] }`                                                                |

## Requirements

- Raspberry Pi with camera configured
- Python 3.10+
- `picamera2` (recommended) or legacy `picamera`
- OpenAI API key

## Setup

Install OS-level dependencies first (once):

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-picamera2 python3-evdev libcamera-apps evtest
```

Create venv with system package access:

```bash
cd arpi
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set:
- `OPENAI_API_KEY` (required)
- `ARPI_INPUT_DEVICE` — e.g. `/dev/input/event3` (find via `sudo evtest`)
- `ARPI_ROTATE_180` — `1` or `0`
- `ARPI_SERVER_HOST` — default `0.0.0.0`
- `ARPI_SERVER_PORT` — default `5000`

## Run

```bash
cd arpi
source .venv/bin/activate
python app.py
```

Test from another machine:

```bash
curl http://<pi-ip>:5000/health
curl http://<pi-ip>:5000/result
```

## Changing Prompts

Edit `prompts.py` to add or modify prompts. Change `DEFAULT_PROMPT` to switch the active prompt.

## Legacy

The original monolithic script is preserved as `mvp_camera_chat.py` for reference.
