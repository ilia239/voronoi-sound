# Voronoi Sound — Design Notes

## Reference analysis

Analyzed The Binaural Monk — "New Way Alpha 100Hz - 110Hz" (2026):

| Metric | Reference | Key insight |
|---|---|---|
| Dominant tone | 82 Hz (2nd harmonic of 41 Hz fundamental) | Not dual sines — full harmonic series |
| Frequency bands | 26 distinct peaks | Many harmonics, widely spread |
| Stereo correlation | 0.18 (nearly uncorrelated) | Different ears get different content |
| Spectral bandwidth | 610 Hz | Not pure narrow peaks |
| Dynamic range | 61.5 dB | Significant amplitude variation over time |

## Three-layer architecture

The reference has three distinct sonic layers. Our synth mirrors them:

### 1. Drone hum (гул)
- Pure centered sine tones at harmonics of 55 Hz fundamental
- 4 voices: 55, 110 (dominant), 165, 220 Hz
- Minimal LFO — barely perceptible drift
- No binaural detuning on drone bed

### 2. Binaural vibration (вибрация)
- Dedicated hard-panned L/R pair at 110 Hz
- 0.4 Hz frequency offset between ears
- Brain creates the beat percept
- Clean and distinct from drone hum

### 3. Melody (мелодия)
- Single voice gliding through drone harmonics (110→165→220→275→330 Hz)
- 4-8 seconds per note, 1.5 sec glide transition
- Frequency gliding — no crossfade phase jumps (avoids clicks)
- Very subtle vibrato
- Quiet — emerges from drone, doesn't sit on top

## Critical design decisions

### Phase-continuous frequency changes
Crossfading two voices for note transitions caused clicks (phase discontinuity). Solution: single voice with linear frequency glide from old note to new note. No phase jumps.

### Drone bed purity
First version used 14 binaurally-detuned voices with independent LFOs. Result: broadband noise, not clean drone. Fix: remove binaural offset from drone, center all drone voices, minimize LFO depth. Binaural beating only from dedicated vibe pair.

### Melody blending
Random pentatonic notes sounded disconnected from drone. Fix: melody uses the drone's own harmonic frequencies. Notes ascend/descend through harmonic series in gentle arcs. Melody emerges naturally from the harmonic structure.
