"""Loudness / peak measurement helpers shared by gen_sfx.py and analyze_sfx.py.

Implements ITU-R BS.1770-4 integrated loudness for a single (mono) channel at
48 kHz:
  * K-weighting with the two biquads published in BS.1770 for fs = 48 kHz
    (stage 1 high-shelf "pre-filter", stage 2 RLB high-pass).
  * 400 ms gating blocks with 75 % overlap (100 ms hop).
  * Absolute gate -70 LUFS, relative gate -10 LU.
  * Channel weight G = 1.0 (mono file, treated as one front channel).

Project-specific conventions (documented in production/audio/REPORT.md):
  * Clips shorter than one 400 ms block are zero-padded to 400 ms, so their
    "integrated" value equals the loudness of one block containing the whole
    event. Strict BS.1770 is undefined for such short signals.
  * For loop files, the K-weighting filters are run over the loop twice and
    only the second pass is measured (filter state is in steady state, as it
    would be during looped playback).

True peak is approximated by 4x polyphase oversampling with
scipy.signal.resample_poly (Kaiser-windowed FIR), not the exact
BS.1770 Annex 2 reference filter.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import lfilter, resample_poly

FS = 48000

# BS.1770-4, Table 1 / Table 2 coefficients (valid for 48 kHz only).
_B1 = [1.53512485958697, -2.69169618940638, 1.19839281085285]
_A1 = [1.0, -1.69065929318241, 0.73248077421585]
_B2 = [1.0, -2.0, 1.0]
_A2 = [1.0, -1.99004745483398, 0.99007225036621]

BLOCK = int(0.400 * FS)
HOP = int(0.100 * FS)
ABS_GATE = -70.0
REL_GATE = -10.0


def k_weight(x: np.ndarray, loop: bool = False) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if loop:
        y = lfilter(_B2, _A2, lfilter(_B1, _A1, np.concatenate([x, x])))
        return y[len(x):]
    return lfilter(_B2, _A2, lfilter(_B1, _A1, x))


def _block_ms(x: np.ndarray, loop: bool = False) -> np.ndarray:
    x = np.asarray(x, dtype=np.float64)
    if len(x) < BLOCK:
        x = np.pad(x, (0, BLOCK - len(x)))
    z = k_weight(x, loop=loop)
    sq = np.concatenate([[0.0], np.cumsum(z * z)])
    starts = np.arange(0, len(z) - BLOCK + 1, HOP)
    return (sq[starts + BLOCK] - sq[starts]) / BLOCK


def _lk(ms):
    with np.errstate(divide="ignore"):
        return -0.691 + 10.0 * np.log10(ms)


def integrated_loudness(x: np.ndarray, loop: bool = False) -> float:
    """Gated integrated loudness in LUFS (mono, 48 kHz). -inf if fully gated."""
    ms = _block_ms(x, loop=loop)
    lk = _lk(ms)
    above_abs = ms[lk > ABS_GATE]
    if above_abs.size == 0:
        return float("-inf")
    rel = _lk(np.mean(above_abs)) + REL_GATE
    gated = ms[(lk > ABS_GATE) & (lk > rel)]
    return float(_lk(np.mean(gated)))


def max_momentary(x: np.ndarray, loop: bool = False) -> float:
    """Maximum 400 ms (momentary) loudness in LUFS."""
    return float(np.max(_lk(_block_ms(x, loop=loop))))


def sample_peak_db(x: np.ndarray) -> float:
    p = float(np.max(np.abs(x)))
    return float("-inf") if p == 0 else 20.0 * np.log10(p)


def true_peak_db(x: np.ndarray, loop: bool = False) -> float:
    """Approximate true peak (dBTP) via 4x oversampling."""
    x = np.asarray(x, dtype=np.float64)
    pad = 64
    if loop:
        ext = np.concatenate([x[-pad:], x, x[:pad]])
    else:
        ext = np.pad(x, (pad, pad))
    up = resample_poly(ext, 4, 1)
    p = max(float(np.max(np.abs(up))), float(np.max(np.abs(x))))
    return float("-inf") if p == 0 else 20.0 * np.log10(p)


def selftest() -> dict:
    """997 Hz sine at -20 dBFS peak should read about -23.0 LUFS (mono, G=1)."""
    t = np.arange(10 * FS) / FS
    x = 10 ** (-20 / 20) * np.sin(2 * np.pi * 997.0 * t)
    measured = integrated_loudness(x)
    expected = -20.0 - 3.0103
    return {
        "signal": "997 Hz sine, 10 s, peak -20 dBFS, mono",
        "expected_lufs": round(expected, 3),
        "measured_lufs": round(measured, 3),
        "pass": bool(abs(measured - expected) < 0.1),
    }
