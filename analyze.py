#!/usr/bin/env python3
"""
Analyze reference track: extract spectral structure, stereo differences,
temporal evolution, and layering. Used to understand what makes the
professional binaural drone richer than our pure-sine synth.
"""

import numpy as np
import librosa
import sys
import json

REF = "reference.wav/The Binaural Monk - New Way Alpha 100Hz - 110Hz.wav"

def main():
    print(f"Loading {REF}...")
    y, sr = librosa.load(REF, sr=None, mono=False)  # keep stereo
    # y shape: (2, samples)

    duration = y.shape[1] / sr
    print(f"  Sample rate: {sr} Hz")
    print(f"  Channels: {y.shape[0]}")
    print(f"  Duration: {duration:.1f} s ({int(duration//60)}:{int(duration%60):02d})")

    left = y[0, :]
    right = y[1, :]

    # ── 1. Overall frequency spectrum ──
    print("\n── 1. Frequency Spectrum (full track average) ──")
    n_fft = 16384
    hop = n_fft // 4

    D_left = librosa.amplitude_to_db(np.abs(librosa.stft(left, n_fft=n_fft, hop_length=hop)), ref=np.max)
    D_right = librosa.amplitude_to_db(np.abs(librosa.stft(right, n_fft=n_fft, hop_length=hop)), ref=np.max)
    D_diff = D_left - D_right  # positive = left louder, negative = right louder

    freqs = librosa.fft_frequencies(sr=sr, n_fft=n_fft)

    # Average spectrum per channel
    avg_left = np.mean(D_left, axis=1)
    avg_right = np.mean(D_right, axis=1)

    # Find peaks in averaged spectrum (sum of L+R)
    avg_mono = np.mean(D_left + D_right, axis=1) / 2
    peaks = []
    for i in range(2, len(avg_mono) - 2):
        if (avg_mono[i] > avg_mono[i-1] and avg_mono[i] > avg_mono[i-2] and
            avg_mono[i] > avg_mono[i+1] and avg_mono[i] > avg_mono[i+2] and
            avg_mono[i] > -60):  # only peaks above -60 dB
            peaks.append((freqs[i], avg_mono[i], avg_left[i], avg_right[i]))

    # Sort by amplitude, show top 20
    peaks.sort(key=lambda x: x[1], reverse=True)
    print(f"\n  Top 20 spectral peaks (freq, avg_dB, left_dB, right_dB):")
    for f, avg_db, l_db, r_db in peaks[:20]:
        lr_diff = l_db - r_db
        pan_indicator = "  ←L" if lr_diff > 3 else ("  R→" if lr_diff < -3 else "  C")
        print(f"    {f:8.1f} Hz  |  avg: {avg_db:5.1f} dB  |  L: {l_db:5.1f}  R: {r_db:5.1f}{pan_indicator}")

    # ── 2. Harmonic series detection ──
    print("\n── 2. Harmonic Structure ──")
    # Find the fundamental by looking at lowest strong peak
    strong_peaks = [p for p in peaks if p[1] > -30]
    strong_peaks.sort(key=lambda x: x[0])  # sort by frequency
    if strong_peaks:
        fundamental = strong_peaks[0][0]
        print(f"  Likely fundamental: {fundamental:.1f} Hz")
        # Check for harmonic series
        for p in strong_peaks[1:]:
            ratio = p[0] / fundamental
            nearest_harmonic = round(ratio)
            if abs(ratio - nearest_harmonic) < 0.08:
                print(f"    Harmonic {nearest_harmonic}: {p[0]:.1f} Hz (ratio {ratio:.2f}, {p[1]:.1f} dB)")

    # ── 3. Stereo analysis ──
    print("\n── 3. Stereo / Binaural Analysis ──")
    # Find frequency pairs: same frequency zone, different L/R amplitude
    for f, avg_db, l_db, r_db in peaks:
        lr_diff = abs(l_db - r_db)
        if lr_diff > 2:  # noticeable stereo separation
            side = "LEFT" if l_db > r_db else "RIGHT"
            print(f"    {f:.1f} Hz: {lr_diff:.1f} dB louder in {side}")

    # Correlation between channels over time
    corr = np.corrcoef(left, right)[0, 1]
    print(f"\n  Stereo correlation: {corr:.4f} (0 = uncorrelated, 1 = mono)")

    # ── 4. Temporal evolution ──
    print("\n── 4. Temporal Evolution ──")
    # Split into 10-second windows, track dominant frequency
    window_s = 10
    window_samples = int(window_s * sr)
    n_windows = y.shape[1] // window_samples

    print(f"  {window_s}s windows, dominant frequency per window:")
    for w in range(min(n_windows, 15)):  # show first 15 windows
        start = w * window_samples
        end = start + window_samples
        D_win = np.abs(librosa.stft(left[start:end] + right[start:end], n_fft=n_fft, hop_length=hop))
        avg_win = np.mean(D_win, axis=1)
        # Find max in 80-350 Hz range (drone zone)
        lo = np.searchsorted(freqs, 80)
        hi = np.searchsorted(freqs, 350)
        peak_idx = lo + np.argmax(avg_win[lo:hi])
        t_start = w * window_s
        print(f"    {t_start:3d}s–{min(t_start+window_s, int(duration)):3d}s:  peak at {freqs[peak_idx]:.1f} Hz")

    # ── 5. Spectral features ──
    print("\n── 5. Spectral Features ──")
    cent = librosa.feature.spectral_centroid(y=left + right, sr=sr, n_fft=n_fft, hop_length=hop)[0]
    bw = librosa.feature.spectral_bandwidth(y=left + right, sr=sr, n_fft=n_fft, hop_length=hop)[0]
    rolloff = librosa.feature.spectral_rolloff(y=left + right, sr=sr, n_fft=n_fft, hop_length=hop)[0]

    print(f"  Spectral centroid:  mean {np.mean(cent):.1f} Hz,  range {np.min(cent):.0f}–{np.max(cent):.0f} Hz")
    print(f"  Spectral bandwidth: mean {np.mean(bw):.1f} Hz,  range {np.min(bw):.0f}–{np.max(bw):.0f} Hz")
    print(f"  Spectral rolloff:   mean {np.mean(rolloff):.1f} Hz")

    # ── 6. Amplitude envelope ──
    print("\n── 6. Amplitude Envelope ──")
    rms = librosa.feature.rms(y=left + right, hop_length=hop)[0]
    rms_db = librosa.amplitude_to_db(rms)
    print(f"  RMS energy: mean {np.mean(rms_db):.1f} dB, min {np.min(rms_db):.1f} dB, max {np.max(rms_db):.1f} dB")
    print(f"  Dynamic range: {np.max(rms_db) - np.min(rms_db):.1f} dB")

    # ── 7. Key differences summary ──
    print("\n── 7. What this track has that our synth lacks ──")
    print(f"  • Stereo separation: {corr:.3f} (not 1.0 mono)")
    print(f"  • Spectral bandwidth: {np.mean(bw):.0f} Hz (not near-zero)")
    print(f"  • Dynamic range: {np.max(rms_db) - np.min(rms_db):.1f} dB variation over time")

    # Count distinct frequency clusters
    clusters = []
    for p in peaks[:30]:
        if not clusters or abs(p[0] - clusters[-1]) > 15:
            clusters.append(p[0])
    print(f"  • Frequency clusters (>15 Hz apart): {len(clusters)} distinct bands")

    # ── Export for further analysis ──
    results = {
        "peaks": [(float(f), float(db)) for f, db, _, _ in peaks[:30]],
        "stereo_correlation": float(corr),
        "spectral_centroid_mean": float(np.mean(cent)),
        "spectral_bandwidth_mean": float(np.mean(bw)),
    }
    with open("reference_analysis.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Detailed data saved to reference_analysis.json")


if __name__ == "__main__":
    main()
