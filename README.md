# arpi

Minimal MVP for Raspberry Pi camera + OpenAI vision.

When you press any key in the terminal, the app:
1. Captures a photo from Pi camera.
2. Sends the image + prompt to OpenAI.
3. Prints the model response.

## Requirements

- Raspberry Pi with camera configured
- Python 3.10+
- `picamera2` (recommended) or legacy `picamera`
- OpenAI API key

## Setup

Install OS-level dependencies first (once):

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-picamera2 libcamera-apps
```

Create venv with system package access (`--system-site-packages`):

```bash
cd arpi
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

If you already created `.venv` without system packages, recreate it:

```bash
cd arpi
rm -rf .venv
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Edit `.env` and set:
- `OPENAI_API_KEY`
- optionally `OPENAI_MODEL` and `ARPI_PROMPT`

## Run

```bash
cd arpi
source .venv/bin/activate
python mvp_camera_chat.py
```

Controls:
- Press any key to capture/analyze.
- Press `q` to quit.

## Notes

- Terminal must be focused to receive HID key events.
- For Meta Quest + Bluetooth remote, this MVP assumes the remote produces keyboard events to the terminal session.
- `picamera2` is expected from apt (`python3-picamera2`) and made visible inside venv via `--system-site-packages`.
