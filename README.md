# voronoi-sound

Endless drone generator for art installation. Pure sine additive synthesis with slow LFO-driven evolution — inspired by binaural beat textures in the 100Hz alpha range.

Target: Raspberry Pi 5 → multi-channel sound card → 8 speakers around dark room with illuminated mystical picture.

Currently: mono, algorithmic, never-ending.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
source .venv/bin/activate
python drone.py
```

Ctrl+C to stop (fades out cleanly).

## Tuning

Edit `VOICES` list in `drone.py`:
- `freq` — base frequency (Hz)
- `amp` — voice amplitude (0–1)
- `lfo_freq` — pitch drift speed (lower = slower)
- `lfo_depth` — pitch drift range (Hz)

`MASTER_GAIN` controls overall volume. `CHANNELS` for mono/stereo/multi-channel output.

## Raspberry Pi deployment

Same Python code. Install ALSA dependencies first:

```bash
sudo apt install libportaudio2 portaudio19-dev python3-numpy
python3 -m venv .venv
source .venv/bin/activate
pip install sounddevice
```

Auto-start via systemd (TODO). Multi-channel via HiFiBerry DAC8x (TODO).

## Reference

The Binaural Monk — "New Way Alpha 100Hz - 110Hz" (2026)
