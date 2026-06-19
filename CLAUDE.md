# CLAUDE.md

## Project
Endless binaural drone synth for art installation. Raspberry Pi 5 → multi-channel sound card → 8 speakers. Dark room, illuminated mystical picture.

## Quick start
```bash
source .venv/bin/activate
python drone.py        # Ctrl+C to stop
```

## Architecture
See `DESIGN.md` for detailed design rationale, reference analysis, and key decisions.

Three-layer synth: drone hum (4 pure harmonic tones) + binaural vibration (hard-panned L/R beat pair) + melody (frequency-gliding harmonic voice).

## Key files
- `drone.py` — main synth engine
- `DESIGN.md` — design decisions, reference analysis
- `analyze.py` — reference track spectrum analyzer
- `requirements.txt` — Python deps

## Tuning
Edit knobs at top of `drone.py`: `FUNDAMENTAL`, `DRONE_HARMONICS`, `MELODY_NOTE_MIN/MAX`, `BINAURAL_OFFSET`, `MASTER_GAIN`.
