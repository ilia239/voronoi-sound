#!/usr/bin/env python3
"""
Endless binaural drone — v5.

Three layers matching the reference:
  1. Drone hum — harmonic series bed, centered
  2. Binaural vibration — L/R frequency offset, brain-level beating
  3. Clean melody — slow harmonic notes that develop over time,
     emerging from and blending with the drone's own harmonic structure.
"""

import numpy as np
import sounddevice as sd
import signal
import sys
import random

# ── Knobs ────────────────────────────────────────────────────────────────────

SAMPLE_RATE = 48000
BLOCK_SIZE = 512
CHANNELS = 2
MASTER_GAIN = 0.4
FADE_IN = 3.0

# ── 1. Drone bed (гул) ──────────────────────────────────────────────────────

FUNDAMENTAL = 55.0
BINAURAL_OFFSET = 0.4

DRONE_HARMONICS = [
    # (harmonic, amp, L_gain, R_gain)
    (1,  0.02, 1.0, 1.0),     #  55 Hz — minimal low
    (2,  0.15, 1.0, 1.0),     # 110 Hz — dominant
    (3,  0.06, 1.0, 1.0),     # 165 Hz
    (4,  0.03, 1.0, 1.0),     # 220 Hz
    (5,  0.015, 1.0, 1.0),    # 275 Hz
]

DRONE_LFO_FREQ = 0.001          # barely perceptible drift
DRONE_LFO_AMP = 0.04            # minimal amplitude variation
DRONE_LFO_PITCH = 0.01          # minimal pitch variation

# ── 2. Binaural vibration layer (вибрация) ──────────────────────────────────

# Extra voice pair at dominant frequency with stronger stereo separation
# to make the binaural beat more present.
VIBE_FREQ = FUNDAMENTAL * 2   # 110 Hz — same as dominant drone
VIBE_OFFSET = 0.4             # beat frequency
VIBE_AMP = 0.08               # quiet presence
VIBE_PAN_L = -1.0             # hard left
VIBE_PAN_R = 1.0              # hard right

# ── 3. Melody layer (мелодия) ────────────────────────────────────────────────

# Melody uses actual harmonics of the drone fundamental — so it blends
# naturally. Notes are harmonic numbers, converted to frequencies.
# The melody slowly moves through different harmonics.
#
# Pattern: each "phrase" visits 4-5 harmonics in gentle arcs.
MELODY_HARMONICS = [2, 3, 4, 5, 6]  # harmonic numbers (×55 Hz)
MELODY_AMP = 0.10                     # per-voice amp (× ensemble size)
MELODY_NOTE_MIN = 6.0
MELODY_NOTE_MAX = 14.0
MELODY_XFADE = 2.0
MELODY_VIBRATO_FREQ = 0.0
MELODY_VIBRATO_DEPTH = 0.0
MELODY_HARMONIC_RICHNESS = 0.0
MELODY_PAN = 0.0

# Ensemble/choir effect — each melody note is N detuned voices
# creating a soft pad timbre instead of pure sine.
MELODY_ENSEMBLE = 4                   # voices per note
MELODY_DETUNE_SPREAD = 0.6            # Hz — total spread across ensemble
MELODY_STEREO_SPREAD = 0.8            # pan spread across ensemble


# ── Build voices ─────────────────────────────────────────────────────────────

def build_drone_voices():
    """Clean drone bed — no binaural detuning, minimal LFO. Just pure tones."""
    voices = []
    rng = np.random.default_rng(seed=42)
    for h, amp, gl, gr in DRONE_HARMONICS:
        f = FUNDAMENTAL * h
        # Slight stereo spread through panning, not frequency offset
        voices.append({
            "freq": f,
            "amp": 0.35 * amp * gl,
            "pan": 0.0,  # centered — clean drone fills the room evenly
            "lfo_f": DRONE_LFO_FREQ + rng.uniform(0, 0.001),
            "lfo_amp": DRONE_LFO_AMP * rng.uniform(0.2, 1.0),
            "lfo_pitch": DRONE_LFO_PITCH * rng.uniform(0.2, 1.0),
        })
    return voices


def build_vibe_voices():
    """Dedicated binaural beat pair — hard-panned for clear brain-level beat."""
    return [
        {"freq": VIBE_FREQ - VIBE_OFFSET / 2, "amp": VIBE_AMP, "pan": VIBE_PAN_L,
         "lfo_f": 0.002, "lfo_amp": 0.05, "lfo_pitch": 0.02},
        {"freq": VIBE_FREQ + VIBE_OFFSET / 2, "amp": VIBE_AMP, "pan": VIBE_PAN_R,
         "lfo_f": 0.002, "lfo_amp": 0.05, "lfo_pitch": 0.02},
    ]


class MelodyScheduler:
    """
    Melody that walks through harmonics with smooth frequency gliding.
    Single voice — no crossfade phase jumps. Frequency linearly
    interpolates from old note to new note during transition.
    """

    def __init__(self, harmonics, fundamental, note_min, note_max, xfade,
                 amp, pan, vibrato_freq, vibrato_depth, harmonic_richness,
                 sample_rate):
        self.harmonics = harmonics
        self.fundamental = fundamental
        self.note_min = note_min
        self.note_max = note_max
        self.xfade = xfade
        self.amp = amp
        self.pan = pan
        self.vibrato_freq = vibrato_freq
        self.vibrato_depth = vibrato_depth
        self.harmonic_richness = harmonic_richness
        self.sample_rate = sample_rate
        self.rng = random.Random(42)

        # Start with first harmonic, schedule transition to second
        self.from_h = harmonics[0]
        self.to_h = harmonics[1]
        self.from_freq = fundamental * self.from_h
        self.to_freq = fundamental * self.to_h
        self.transition_start_sample = 0
        self.transition_duration = int(xfade * sample_rate)
        self._schedule_next(0)

    def _schedule_next(self, current_sample):
        """Pick next harmonic — random walk with occasional leaps."""
        hold_duration = self.rng.uniform(self.note_min, self.note_max)
        self.transition_start_sample = current_sample + int(hold_duration * self.sample_rate)

        # Random walk: step ±1 or ±2, stay in bounds, occasionally leap
        old_idx = self.harmonics.index(self.to_h)
        step = self.rng.choice([-2, -1, 1, 2])
        # 20% chance of larger leap
        if self.rng.random() < 0.2:
            step = self.rng.choice([-3, -2, 2, 3])
        new_idx = old_idx + step
        new_idx = max(0, min(len(self.harmonics) - 1, new_idx))

        self.from_h = self.to_h
        self.from_freq = self.fundamental * self.from_h
        self.to_h = self.harmonics[new_idx]
        self.to_freq = self.fundamental * self.to_h

    def get_freq(self, sample_count):
        """
        Returns a single frequency for the current sample.
        Glides linearly between from_freq and to_freq during transition.
        """
        if sample_count < self.transition_start_sample:
            # Holding current note
            return self.from_freq
        else:
            # Gliding
            elapsed = sample_count - self.transition_start_sample
            t = min(elapsed / self.transition_duration, 1.0)
            if t >= 1.0:
                self._schedule_next(sample_count)
                return self.to_freq
            return self.from_freq + t * (self.to_freq - self.from_freq)


# ── Engine ───────────────────────────────────────────────────────────────────

running = True

def signal_handler(sig, frame):
    global running
    running = False
    print("\nFading out...")


class Engine:
    def __init__(self, drone_voices, vibe_voices, melody, sample_rate,
                 block_size, master_gain, fade_in, ensemble_size,
                 detune_spread, stereo_spread):
        self.sr = sample_rate
        self.bs = block_size
        self.master_gain = master_gain
        self.melody = melody
        self.fade_in_samples = int(fade_in * sample_rate)
        self.sample_count = 0
        self.ensemble_size = ensemble_size
        self.detune_spread = detune_spread

        self.all_voices = drone_voices + vibe_voices
        rng = np.random.default_rng()
        n = len(self.all_voices)
        self.phases = rng.uniform(0, 2 * np.pi, n)
        self.lfo_phases = rng.uniform(0, 2 * np.pi, n)

        self.pans = np.zeros((n, 2), dtype=np.float32)
        for i, v in enumerate(self.all_voices):
            pan = v.get("pan", 0.0)
            angle = (pan + 1.0) * np.pi / 4.0
            self.pans[i, 0] = np.cos(angle)
            self.pans[i, 1] = np.sin(angle)

        # Ensemble melody: N voices with detuning and stereo spread
        self.m_phases = rng.uniform(0, 2 * np.pi, ensemble_size)
        # Detune offsets: evenly spread across [-spread/2, +spread/2]
        self.m_detunes = np.linspace(-detune_spread / 2, detune_spread / 2,
                                      ensemble_size)
        # Pan per ensemble voice
        base_pan = melody.pan if hasattr(melody, 'pan') else 0.0
        self.m_pans = np.zeros((ensemble_size, 2), dtype=np.float32)
        for i in range(ensemble_size):
            t = ensemble_size - 1
            offset = 0.0 if t == 0 else (-stereo_spread / 2
                                         + i * stereo_spread / t)
            pan = base_pan + offset
            angle = (np.clip(pan, -1.0, 1.0) + 1.0) * np.pi / 4.0
            self.m_pans[i, 0] = np.cos(angle)
            self.m_pans[i, 1] = np.sin(angle)

        self.m_vib_phase = rng.uniform(0, 2 * np.pi)

    def process_block(self, outdata, frames, time_info, status):
        if status:
            print(f"Audio status: {status}", file=sys.stderr)

        block = np.zeros((frames, 2), dtype=np.float32)

        # Drone + vibration voices
        for i, v in enumerate(self.all_voices):
            idx = np.arange(self.sample_count, self.sample_count + frames,
                            dtype=np.float64)

            lfo = np.sin(2.0 * np.pi * v["lfo_f"] * idx / self.sr
                         + self.lfo_phases[i])
            freq_mod = v["freq"] + v["lfo_pitch"] * lfo
            pinc = 2.0 * np.pi * freq_mod / self.sr

            phases = self.phases[i] + np.cumsum(pinc)
            self.phases[i] = phases[-1]
            mono = v["amp"] * np.sin(phases).astype(np.float32)

            alfo = np.sin(2.0 * np.pi * v["lfo_f"] * 1.3 * idx / self.sr
                          + self.lfo_phases[i] + 1.7)
            mono *= (1.0 + v["lfo_amp"] * alfo)

            block[:, 0] += self.pans[i, 0] * mono
            block[:, 1] += self.pans[i, 1] * mono

        # Melody ensemble — N detuned voices with stereo spread, pad timbre
        f_start = self.melody.get_freq(self.sample_count)
        f_end = self.melody.get_freq(self.sample_count + frames - 1)
        base_freqs = np.linspace(f_start, f_end, frames, dtype=np.float64)

        for ev in range(self.ensemble_size):
            freqs = base_freqs + self.m_detunes[ev]

            if self.melody.vibrato_depth > 0:
                idx_m = np.arange(self.sample_count, self.sample_count + frames,
                                  dtype=np.float64)
                vibrato = np.sin(2.0 * np.pi * self.melody.vibrato_freq * idx_m / self.sr
                                 + self.m_vib_phase)
                freqs = freqs + self.melody.vibrato_depth * vibrato

            pinc = 2.0 * np.pi * freqs / self.sr
            phases = self.m_phases[ev] + np.cumsum(pinc)
            self.m_phases[ev] = phases[-1]

            mono = self.melody.amp * np.sin(phases).astype(np.float32)
            block[:, 0] += self.m_pans[ev, 0] * mono
            block[:, 1] += self.m_pans[ev, 1] * mono

        if self.melody.vibrato_depth > 0:
            self.m_vib_phase += (2.0 * np.pi * self.melody.vibrato_freq
                                 * frames / self.sr)

        # Output
        if self.sample_count < self.fade_in_samples:
            block *= self.sample_count / self.fade_in_samples
        block *= self.master_gain
        np.clip(block, -1.0, 1.0, out=block)
        self.sample_count += frames
        outdata[:] = block


def main():
    drone = build_drone_voices()
    vibe = build_vibe_voices()
    melody = MelodyScheduler(
        harmonics=MELODY_HARMONICS,
        fundamental=FUNDAMENTAL,
        note_min=MELODY_NOTE_MIN,
        note_max=MELODY_NOTE_MAX,
        xfade=MELODY_XFADE,
        amp=MELODY_AMP,
        pan=MELODY_PAN,
        vibrato_freq=MELODY_VIBRATO_FREQ,
        vibrato_depth=MELODY_VIBRATO_DEPTH,
        harmonic_richness=MELODY_HARMONIC_RICHNESS,
        sample_rate=SAMPLE_RATE,
    )

    print("Voronoi Sound — Three-Layer Binaural Drone")
    print(f"  1. Drone hum: {len(drone)} voices, {len(DRONE_HARMONICS)} harmonics")
    print(f"  2. Binaural vibe: {len(vibe)} voices hard-panned L/R")
    print(f"  3. Melody: harmonics {MELODY_HARMONICS} of {FUNDAMENTAL:.0f} Hz")
    print(f"     Notes: {MELODY_NOTE_MIN}-{MELODY_NOTE_MAX}s, crossfade {MELODY_XFADE}s")
    print(f"     Ensemble: {MELODY_ENSEMBLE} voices, detune {MELODY_DETUNE_SPREAD} Hz, stereo spread {MELODY_STEREO_SPREAD}")
    print(f"  Press Ctrl+C to stop\n")
    print("Starting...")

    engine = Engine(
        drone_voices=drone,
        vibe_voices=vibe,
        melody=melody,
        sample_rate=SAMPLE_RATE,
        block_size=BLOCK_SIZE,
        master_gain=MASTER_GAIN,
        fade_in=FADE_IN,
        ensemble_size=MELODY_ENSEMBLE,
        detune_spread=MELODY_DETUNE_SPREAD,
        stereo_spread=MELODY_STEREO_SPREAD,
    )

    signal.signal(signal.SIGINT, signal_handler)

    try:
        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=CHANNELS,
            callback=engine.process_block,
            dtype="float32",
        ):
            while running:
                sd.sleep(250)
    except KeyboardInterrupt:
        pass
    finally:
        print("Stopped.")


if __name__ == "__main__":
    main()
