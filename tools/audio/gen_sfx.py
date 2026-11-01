#!/usr/bin/env python3
"""Deterministic procedural SFX generator for "The Unfinished Confession" (L0_B01).

Every sound is synthesised from code (noise, oscillators, modal resonators,
simple synthetic reverbs). No samples, recordings or third-party audio are
read. The output format is the runtime contract:

    RIFF WAV, PCM 16-bit signed little-endian, mono, 48000 Hz,
    canonical 44-byte header (fmt + data only), file name = <sound_id>.wav

Usage (from repo root, inside a venv with numpy + scipy):
    python tools/audio/gen_sfx.py                # write all WAVs + manifest
    python tools/audio/gen_sfx.py --only rain_loop
    python tools/audio/gen_sfx.py --out-dir /tmp/x --no-manifest

Determinism: one fixed base seed; each sound gets its own RNG stream derived
from (BASE_SEED, crc32(sound_id)), so adding/removing a sound never changes
another sound's output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, lfilter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bs1770  # noqa: E402

FS = 48000
BASE_SEED = 20261101
TP_CEILING_DB = -1.5          # generator ceiling; contract limit is -1.0 dBTP
REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "ue58" / "Content" / "Confession" / "Audio"
MANIFEST = REPO / "production" / "audio" / "sound_manifest.json"
LICENCE = "original, procedurally generated for this project"

# Studio-defined loudness categories (integrated LUFS, see bs1770.py notes).
CATEGORIES = {
    "ambience_bed": {"lufs_range": [-30.0, -26.0], "true_peak_max_dbtp": -1.0},
    "one_shot":     {"lufs_range": [-24.0, -18.0], "true_peak_max_dbtp": -1.0},
    "footstep":     {"lufs_range": [-28.0, -22.0], "true_peak_max_dbtp": -1.0},
}


# --------------------------------------------------------------------------
# DSP helpers
# --------------------------------------------------------------------------
def rng_for(sound_id: str) -> np.random.Generator:
    return np.random.default_rng([BASE_SEED, zlib.crc32(sound_id.encode())])


def secs(s: float) -> int:
    return int(round(s * FS))


def _sos(kind, f, order):
    return butter(order, f, btype=kind, fs=FS, output="sos")


def lp(x, f, order=2):
    return sosfilt(_sos("lowpass", f, order), x)


def hp(x, f, order=2):
    return sosfilt(_sos("highpass", f, order), x)


def bp(x, lo, hi, order=2):
    return sosfilt(_sos("bandpass", [lo, hi], order), x)


def circular(fn, x, reps=3):
    """Apply a (causal) filter fn to a periodic signal without start transient."""
    n = len(x)
    y = fn(np.tile(x, reps))
    return y[(reps - 1) * n:]


def pink(rng, n):
    """Pink (1/f power) noise via spectral shaping, unit RMS."""
    w = rng.standard_normal(n)
    spec = np.fft.rfft(w)
    f = np.fft.rfftfreq(n, 1 / FS)
    f[0] = f[1]
    spec /= np.sqrt(f)
    y = np.fft.irfft(spec, n)
    return y / np.std(y)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)))) if len(x) else 0.0


def modal(exc, modes):
    """Sum of two-pole resonators. modes = [(freq_hz, t60_s, gain), ...].

    An impulse of height 1 into a mode yields a damped sinusoid of initial
    amplitude ~gain that decays 60 dB in t60 seconds.
    """
    y = np.zeros(len(exc))
    for f, t60, g in modes:
        r = 10 ** (-3.0 / (t60 * FS))
        w = 2 * np.pi * f / FS
        y += lfilter([g * np.sin(w)], [1.0, -2 * r * np.cos(w), r * r], exc)
    return y


def impulses(n, events):
    """events = [(time_s, amplitude)] -> sparse impulse train of length n."""
    x = np.zeros(n)
    for t, a in events:
        i = secs(t)
        if 0 <= i < n:
            x[i] += a
    return x


def burst(rng, n, t, dur, amp=1.0, lo=None, hi=None):
    """Short windowed noise burst placed at time t (optionally band-passed)."""
    x = np.zeros(n)
    m = max(secs(dur), 8)
    b = rng.standard_normal(m) * np.hanning(m)
    i = secs(t)
    if i >= n:
        return x
    seg = b[: n - i]
    x[i:i + len(seg)] = seg * amp
    if lo and hi:
        x = bp(x, lo, hi)
    elif hi:
        x = lp(x, hi)
    elif lo:
        x = hp(x, lo)
    return x


def fade(x, fin=0.002, fout=0.02):
    y = x.copy()
    a, b = secs(fin), secs(fout)
    if a:
        y[:a] *= 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, a))
    if b:
        y[-b:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, b))
    return y


def reverb_ir(rng, length, t60_low, t60_high, predelay=0.004, split_hz=1500.0,
              early=()):
    """Synthetic room IR: two-band exponentially decaying noise + early taps."""
    n = secs(length)
    t = np.arange(n) / FS
    lo = lp(rng.standard_normal(n), split_hz) * 10 ** (-3 * t / t60_low)
    hi = hp(rng.standard_normal(n), split_hz) * 10 ** (-3 * t / t60_high)
    tail = lo + hi
    d = secs(predelay)
    tail = np.concatenate([np.zeros(d), tail])[:n]
    tail[: d + secs(0.002)] *= np.linspace(0, 1, d + secs(0.002))
    tail /= np.sqrt(np.sum(tail ** 2))
    for td, g in early:
        i = secs(td)
        if i < n:
            tail[i] += g
    return tail


def add_room(x, ir, wet):
    y = fftconvolve(x, ir)[: len(x)]
    return x + wet * y


def chirp_drop(rng, n, t, f0, rise, tau, amp):
    """Water drop / bubble: upward-gliding damped sinusoid (Minnaert-like).
    The glide saturates at f0 * (1 + rise), so it never approaches Nyquist."""
    x = np.zeros(n)
    i = secs(t)
    m = min(secs(tau * 7), n - i)
    if m <= 0:
        return x
    tt = np.arange(m) / FS
    f = f0 * (1 + rise * (1 - np.exp(-tt / tau)))
    ph = 2 * np.pi * np.cumsum(f) / FS + rng.uniform(0, 2 * np.pi)
    x[i:i + m] = amp * np.sin(ph) * np.exp(-tt / tau) * (1 - np.exp(-tt / 0.0004))
    return x


def make_loop(y, length, xfade):
    """Equal-power crossfade loop: y must hold length + xfade samples.

    out[n] = y[n] for n >= xfade; the head is crossfaded with y[length:].
    At the wrap, out[length-1] = y[length-1] is followed by out[0] = y[length],
    i.e. the original continuous signal, so the seam is sample-continuous.
    """
    assert len(y) >= length + xfade
    out = y[:length].copy()
    ph = np.linspace(0, np.pi / 2, xfade)
    out[:xfade] = y[:xfade] * np.sin(ph) + y[length:length + xfade] * np.cos(ph)
    return out


# --------------------------------------------------------------------------
# Sound generators (one per sound id). Each returns float64 in [-1, 1]-ish;
# level is set afterwards by finalize() from the category loudness target.
# --------------------------------------------------------------------------
def gen_rain_loop(rng):
    """Rain on a concrete canopy: pink bed + dense droplet patter + gutter drips."""
    L, X, pre = secs(16.0), secs(1.0), secs(0.6)
    n = pre + L + X
    bed = lp(hp(pink(rng, n), 250, 2), 6500, 2)

    patter = np.zeros(n)
    # (events/s, centre freqs, decay s, gain): small impacts on concrete.
    for rate, freqs, tau, g in [(1400, (1900, 2400, 2900, 3400), 0.0025, 1.0),
                                (900, (3600, 4300, 5100), 0.0016, 0.55),
                                (500, (700, 950, 1250), 0.0050, 0.7)]:
        for f in freqs:
            k = int(rate / len(freqs) * n / FS)
            pos = rng.integers(0, n, k)
            amp = rng.lognormal(0.0, 0.7, k) * rng.choice([-1.0, 1.0], k)
            imp = np.zeros(n)
            np.add.at(imp, pos, amp)
            kt = np.arange(secs(tau * 6)) / FS
            kern = np.sin(2 * np.pi * f * kt) * np.exp(-kt / tau)
            patter += g * fftconvolve(imp, kern)[:n]
    patter = lp(patter, 7500, 2)
    patter *= 0.75 * rms(bed) / rms(patter)

    # slow gust modulation, +-1.5 dB
    gust = lp(rng.standard_normal(n), 0.35, 2)
    gust /= np.std(gust)
    env = 10 ** (1.5 * np.clip(gust, -2.5, 2.5) / 2.5 / 20)

    runoff = lp(rng.standard_normal(n), 140, 2)
    runoff *= 0.35 * rms(bed) / rms(runoff)

    # gutter drips: one quasi-regular drip spot + sparse random drips
    drips = np.zeros(n)
    t = 0.3
    while t < n / FS - 0.2:
        drips += chirp_drop(rng, n, t, rng.uniform(820, 900), 0.8,
                            rng.uniform(0.014, 0.020), rng.uniform(0.8, 1.0))
        t += 1.55 + rng.normal(0, 0.18)
    for _ in range(int(0.45 * n / FS)):
        drips += chirp_drop(rng, n, rng.uniform(0, n / FS - 0.2),
                            rng.uniform(600, 1500), rng.uniform(0.4, 1.2),
                            rng.uniform(0.008, 0.02), rng.uniform(0.3, 0.7))
    drips = bp(drips, 300, 6000, 1)
    drips *= 2.2 * rms(bed) / np.max(np.abs(drips))

    y = (bed + patter) * env + runoff + drips
    y = lp(hp(y, 40, 2), 9000, 2)
    return make_loop(y[pre:], L, X)


def gen_hum_electrical(rng):
    """50 Hz mains family hum + ballast buzz. All tonal parts are exactly
    periodic over the 8 s loop (400 mains cycles); only the faint noise floor
    is crossfade-looped."""
    L, X = secs(8.0), secs(0.5)
    T = L / FS
    t = np.arange(L) / FS
    phi = 0.4 * np.sin(2 * np.pi * t / T)        # slow mains wander, periodic
    harm = {1: 0.30, 2: 1.00, 3: 0.16, 4: 0.42, 5: 0.06, 6: 0.22, 8: 0.11,
            10: 0.06, 12: 0.04, 14: 0.025}
    hum = np.zeros(L)
    for k, a in harm.items():
        hum += a * np.sin(2 * np.pi * 50 * k * t + k * phi + rng.uniform(0, 2 * np.pi))
    am = (1 + 0.07 * np.sin(2 * np.pi * (1 / T) * t + 0.3)
          + 0.04 * np.sin(2 * np.pi * (5 / T) * t + 1.1))
    hum *= am

    # ballast buzz: narrow pulses at 100 Hz (peaks of |sin|), band-passed
    s = np.abs(np.sin(2 * np.pi * 50 * t + phi))
    pulses = np.clip((s - 0.9) / 0.1, 0, 1) ** 2
    pulses -= pulses.mean()
    buzz = circular(lambda v: lp(hp(v, 900, 2), 5500, 2), pulses)
    flutter = 0.55 + 0.45 * np.sin(2 * np.pi * (2 / T) * t) ** 2
    buzz *= flutter
    buzz *= 0.12 * rms(hum) / rms(buzz)

    nz = bp(pink(rng, L + X + secs(0.3)), 150, 3000, 2)[secs(0.3):]
    nz = make_loop(nz, L, X)
    nz *= 0.03 * rms(hum) / rms(nz)
    return hum + buzz + nz


def gen_clock_tick(rng):
    """Mechanical desk clock, 2 beats/s, exactly 8 s (16 beats).

    Irregularity ("ticking out of sync"): an out-of-beat escapement
    (tick->tock 0.482 s, tock->tick 0.518 s), +-4 ms jitter and one 22 ms
    hesitation; intervals are rescaled to sum to exactly 8.000 s. Events and
    their decays are rendered circularly, so the wrap is seamless."""
    L = secs(8.0)
    tail = secs(0.4)
    base = np.array([0.482, 0.518] * 8)
    iv = base + rng.normal(0, 0.004, 16)
    iv[10] += 0.022
    iv *= 8.0 / iv.sum()
    onsets = 0.137 + np.concatenate([[0.0], np.cumsum(iv)[:-1]])

    tick_modes = [(2250, 0.045, 1.0), (3480, 0.035, 0.7), (5120, 0.020, 0.4),
                  (7900, 0.010, 0.2), (860, 0.080, 0.45), (185, 0.040, 0.12)]
    tock_modes = [(f * 0.94, t60 * 1.1, g * gg) for (f, t60, g), gg in
                  zip(tick_modes, [0.8, 1.0, 0.6, 0.35, 0.5, 0.15])]

    out = np.zeros(L + tail)
    for i, t0 in enumerate(onsets):
        modes = tick_modes if i % 2 == 0 else tock_modes
        modes = [(f * rng.uniform(0.985, 1.015), t60, g * 10 ** (rng.normal(0, 1.5) / 20))
                 for f, t60, g in modes]
        # escapement: unlock + drop + recoil sub-impacts
        subs = [(0.0, 1.0), (rng.uniform(0.0022, 0.0030), 0.45),
                (rng.uniform(0.0055, 0.0070), 0.22)]
        exc = np.zeros(L + tail)
        for dt, a in subs:
            exc += burst(rng, L + tail, t0 + dt, 0.0006, a)
        out += modal(exc, modes)
    # desk-surface early reflections
    refl = out.copy()
    for d, g in [(0.0045, 0.35), (0.011, 0.2), (0.019, 0.1)]:
        refl[secs(d):] += g * out[: len(out) - secs(d)]
    refl = hp(refl, 60, 2)
    loop = refl[:L].copy()
    loop[:tail] += refl[L:L + tail]          # wrap decays to the loop head
    return loop


def gen_queue_chime(rng):
    """Three-tone descending ticket-call chime (G5 E5 C5) through a degraded
    small PA speaker: 16 kHz sample-and-hold + 8-bit mu-law, band-limit,
    soft saturation, then a hall-like synthetic reverb."""
    n = secs(3.0)
    t = np.arange(n) / FS
    y = np.zeros(n)
    for t0, f in [(0.05, 784.0), (0.47, 659.3), (0.89, 523.3)]:
        tt = np.clip(t - t0, 0, None)
        on = (t >= t0).astype(float)
        att = np.clip(tt / 0.004, 0, 1)
        for ratio, a, t60 in [(1.0, 1.0, 1.4), (2.0, 0.18, 0.7),
                              (3.01, 0.05, 0.4), (2.76, 0.12, 0.08)]:
            y += on * att * a * np.sin(2 * np.pi * f * ratio * tt) * 10 ** (-3 * tt / t60)
    y /= np.max(np.abs(y))
    # cheap playback chip: 16 kHz sample-and-hold, 8-bit mu-law
    mu = 255.0
    d = y[::3]
    c = np.sign(d) * np.log1p(mu * np.abs(d)) / np.log1p(mu)
    c = np.round(c * 127) / 127
    d = np.sign(c) * ((1 + mu) ** np.abs(c) - 1) / mu
    y = np.repeat(d, 3)[:n]
    # small speaker: band-limit + presence bump + soft saturation
    y = hp(y, 450, 2)
    y = y + 0.5 * bp(y, 1500, 2500, 1)
    y = lp(y, 4500, 4)
    y = np.tanh(1.6 * y / np.max(np.abs(y))) / np.tanh(1.6)
    # PA amplifier hiss while the line is open
    amp_env = np.clip(t / 0.02, 0, 1) * np.clip((2.7 - t) / 0.1, 0, 1)
    y += amp_env * 0.004 * bp(rng.standard_normal(n), 400, 5000, 2)
    ir = reverb_ir(rng, 1.6, 1.1, 0.6, predelay=0.018,
                   early=[(0.023, 0.25), (0.041, 0.15)])
    y = add_room(y, ir, 0.45)
    return fade(y, 0.001, 0.25)


def gen_paper_pickup(rng):
    """Sheet slid out of a brass spring clip: clip tick, paper friction slide
    with crinkle grains, clip snapping back, paper flex."""
    n = secs(0.7)
    t = np.arange(n) / FS
    clip_open = modal(burst(rng, n, 0.040, 0.0004, 1.0),
                      [(3100, 0.03, 1.0), (4700, 0.02, 0.6), (6900, 0.012, 0.3)])
    slide_env = np.clip((t - 0.05) / 0.08, 0, 1) * np.clip((0.33 - t) / 0.12, 0, 1)
    slide = bp(rng.standard_normal(n), 1200, 6500, 2) * slide_env
    k = 60
    grains = np.zeros(n)
    pos = rng.integers(secs(0.06), secs(0.32), k)
    np.add.at(grains, pos, rng.lognormal(0, 0.6, k) * rng.choice([-1, 1], k))
    grains = bp(grains, 2500, 9000, 2)
    clip_close = modal(burst(rng, n, 0.335, 0.0004, 1.0),
                       [(2200, 0.05, 1.0), (3550, 0.03, 0.5), (5300, 0.015, 0.25)])
    flex = burst(rng, n, 0.36, 0.06, 1.0, 180, 900)
    y = (0.5 * clip_open / np.max(np.abs(clip_open))
         + 0.35 * slide / np.max(np.abs(slide))
         + 0.25 * grains / np.max(np.abs(grains))
         + 0.6 * clip_close / np.max(np.abs(clip_close))
         + 0.35 * flex / np.max(np.abs(flex)))
    ir = reverb_ir(rng, 0.3, 0.3, 0.2, early=[(0.006, 0.3)])
    return fade(hp(add_room(y, ir, 0.15), 60, 2), 0.002, 0.1)


def gen_card_slot(rng):
    """Plastic card pulled from a spring slot: microswitch release, friction
    slide with edge ridges, leaf spring returning to its stop."""
    n = secs(0.6)
    t = np.arange(n) / FS
    switch = np.zeros(n)
    for dt, a in [(0.0, 1.0), (0.0013, 0.4), (0.0024, 0.15)]:
        switch += burst(rng, n, 0.012 + dt, 0.0003, a)
    switch = modal(switch, [(4200, 0.010, 1.0), (6800, 0.006, 0.6), (2500, 0.015, 0.4)])
    env = np.clip((t - 0.025) / 0.03, 0, 1) * np.clip((0.24 - t) / 0.06, 0, 1)
    slide = bp(rng.standard_normal(n), 900, 5000, 2) * env
    # ridge texture: impulse train at a falling rate as the card speeds off
    ridge_t, ev, rate = 0.03, [], 260.0
    while ridge_t < 0.23:
        ev.append((ridge_t, rng.uniform(0.5, 1.0)))
        ridge_t += 1.0 / rate
        rate *= 0.985
    ridges = modal(impulses(n, ev), [(3300, 0.004, 1.0), (5200, 0.003, 0.5)]) * env
    spring = modal(burst(rng, n, 0.250, 0.0004, 1.0),
                   [(1150, 0.07, 1.0), (2390, 0.045, 0.45), (3720, 0.025, 0.22)])
    stop = modal(burst(rng, n, 0.262, 0.0003, 1.0), [(5600, 0.006, 1.0), (8100, 0.004, 0.5)])
    y = (0.6 * switch / np.max(np.abs(switch))
         + 0.45 * slide / np.max(np.abs(slide))
         + 0.25 * ridges / np.max(np.abs(ridges))
         + 0.55 * spring / np.max(np.abs(spring))
         + 0.3 * stop / np.max(np.abs(stop)))
    ir = reverb_ir(rng, 0.25, 0.25, 0.15, early=[(0.005, 0.3)])
    return fade(hp(add_room(y, ir, 0.12), 80, 2), 0.002, 0.08)


def gen_door_reject(rng):
    """Access reader rejection: relay pull-in, two piezo beeps (2.73 kHz square
    drive into a resonant piezo, 100 Hz supply ripple, second beep sagging),
    relay drop-out."""
    n = secs(0.6)
    t = np.arange(n) / FS

    def relay(t0, a):
        e = np.zeros(n)
        for dt, aa in [(0.0, 1.0), (0.0011, 0.45), (0.0020, 0.2)]:
            e += burst(rng, n, t0 + dt, 0.0003, aa)
        return a * modal(e, [(3200, 0.008, 1.0), (5400, 0.005, 0.6), (1800, 0.012, 0.5),
                             (520, 0.02, 0.3)])

    beeps = np.zeros(n)
    for t0, t1, f in [(0.040, 0.170, 2730.0), (0.230, 0.360, 2650.0)]:
        g = np.clip((t - t0) / 0.003, 0, 1) * np.clip((t1 - t) / 0.003, 0, 1)
        sq = np.sign(np.sin(2 * np.pi * f * t))
        ripple = 1 + 0.12 * np.sin(2 * np.pi * 100 * t)
        beeps += g * ripple * sq
    beeps = modal(beeps, [(2700, 0.02, 1.0), (8150, 0.006, 0.12)])
    beeps = beeps + 0.25 * bp(beeps, 1000, 1500, 1)        # plastic housing
    beeps /= np.max(np.abs(beeps))
    r1 = relay(0.012, 1.0)
    r2 = relay(0.420, 0.6)
    y = 0.8 * beeps + 0.5 * r1 / np.max(np.abs(r1)) + 0.5 * r2 / np.max(np.abs(r1))
    ir = reverb_ir(rng, 0.35, 0.45, 0.25, early=[(0.007, 0.2)])
    return fade(add_room(y, ir, 0.12), 0.002, 0.08)


def gen_door_release(rng):
    """Electric strike releasing: brief AC solenoid buzz, steel keeper clack
    with frame thunk, one bounce, bolt shift scrape, short room tail."""
    n = secs(0.8)
    t = np.arange(n) / FS
    sol_env = np.clip(t / 0.004, 0, 1) * np.clip((0.045 - t) / 0.004, 0, 1)
    sol = np.abs(np.sin(2 * np.pi * 50 * t)) ** 8 * sol_env
    sol = bp(sol - sol.mean() * sol_env, 180, 2500, 2)
    strike_modes = [(140, 0.08, 0.45), (310, 0.06, 0.35), (980, 0.35, 0.5),
                    (1730, 0.27, 0.45), (2870, 0.18, 0.35), (4550, 0.10, 0.2),
                    (6900, 0.05, 0.1)]
    exc = (burst(rng, n, 0.045, 0.0010, 1.0)
           + burst(rng, n, 0.081, 0.0008, 0.3))
    clack = modal(exc, strike_modes)
    scrape = burst(rng, n, 0.12, 0.035, 1.0, 1500, 5000)
    y = (0.35 * sol / np.max(np.abs(sol))
         + 1.0 * clack / np.max(np.abs(clack))
         + 0.25 * scrape / np.max(np.abs(scrape)))
    ir = reverb_ir(rng, 0.7, 0.55, 0.3, predelay=0.006,
                   early=[(0.009, 0.25), (0.017, 0.15)])
    return fade(hp(add_room(y, ir, 0.3), 40, 2), 0.001, 0.12)


def gen_door_open(rng):
    """Heavy steel door on old hinges: latch tongue clears the keeper, then an
    intermittent stick-slip hinge creak (slip rate 35-125 Hz, resonances kept
    below 3.1 kHz and low-passed at 5.5 kHz to avoid a screech), panel groan,
    air movement, room tail."""
    n = secs(2.0)
    t = np.arange(n) / FS
    v = (1 - np.exp(-np.clip(t - 0.08, 0, None) / 0.18)) * np.exp(-np.clip(t - 0.3, 0, None) / 0.7)
    v *= (t > 0.08) * np.clip((1.85 - t) / 0.2, 0, 1)
    v /= v.max()

    latch = (burst(rng, n, 0.005, 0.07, 1.0, 2000, 6000)
             + modal(burst(rng, n, 0.078, 0.0004, 1.0), [(2600, 0.03, 1.0), (4100, 0.02, 0.5)]))

    def seg(a, b):
        return np.clip((t - a) / 0.04, 0, 1) * np.clip((b - t) / 0.04, 0, 1)
    grip = seg(0.18, 0.62) + 0.8 * seg(0.78, 1.25) + 0.55 * seg(1.38, 1.62)
    ev, ts, wander = [], 0.15, 1.0
    while ts < 1.65:
        i = secs(ts)
        rate = 35 + 90 * v[i]
        wander = np.clip(wander * np.exp(rng.normal(0, 0.03)), 0.92, 1.08)
        a = (v[i] ** 1.3) * grip[i] * rng.uniform(0.7, 1.3)
        if a > 0.01:
            ev.append((ts, a))
        ts += 1.0 / (rate * wander)
    stick = impulses(n, ev)
    creak = modal(stick, [(410, 0.05, 1.0), (870, 0.04, 0.7), (1460, 0.03, 0.5),
                          (2230, 0.025, 0.3), (3100, 0.02, 0.12)])
    groan = modal(stick, [(95, 0.25, 0.4), (182, 0.2, 0.3)])
    air = lp(rng.standard_normal(n), 250, 2) * v
    rumble = lp(rng.standard_normal(n), 120, 2) * v
    y = (0.25 * latch / np.max(np.abs(latch))
         + 0.55 * creak / np.max(np.abs(creak))
         + 0.35 * groan / np.max(np.abs(groan))
         + 0.15 * air / np.max(np.abs(air))
         + 0.15 * rumble / np.max(np.abs(rumble)))
    y = lp(y, 5500, 2)
    ir = reverb_ir(rng, 1.0, 0.75, 0.4, predelay=0.008,
                   early=[(0.012, 0.25), (0.026, 0.15)])
    return fade(hp(add_room(y, ir, 0.25), 40, 2), 0.002, 0.15)


PHONE_GONG_A = [(1180, 1.6, 1.0), (2726, 0.9, 0.5), (4696, 0.5, 0.25), (6986, 0.3, 0.12)]
PHONE_GONG_B = [(1420, 1.5, 1.0), (3280, 0.85, 0.5), (5652, 0.45, 0.25), (8406, 0.28, 0.1)]


def gen_phone_ring(rng):
    """Electromechanical bell ringer: a 25 Hz ringing current swings the clapper
    between two gongs (each struck 25x/s, alternating) for a 1.0 s burst, then
    the gongs ring out freely. 1.0 s on matches a 1 s on / 4 s off cadence; the
    file holds the burst plus ring-out (2.5 s)."""
    n = secs(2.5)
    t = np.arange(n) / FS
    ev_a, ev_b = [], []
    k = 0
    while k * 0.04 < 1.0:
        build = min(1.0, 0.35 + k / 4)
        ev_a.append((0.03 + k * 0.04, build * rng.uniform(0.85, 1.15)))
        ev_b.append((0.05 + k * 0.04, build * rng.uniform(0.85, 1.15)))
        k += 1
    exc_a, exc_b = impulses(n, ev_a), impulses(n, ev_b)
    bells = modal(exc_a, PHONE_GONG_A) + modal(exc_b, PHONE_GONG_B)
    clicks = hp(exc_a + exc_b, 3000, 2)
    rattle = modal(impulses(n, [(e[0], 1.0) for e in ev_a + ev_b]), [(240, 0.02, 1.0)])
    y = (bells / np.max(np.abs(bells))
         + 0.08 * clicks / np.max(np.abs(clicks))
         + 0.1 * rattle / np.max(np.abs(rattle)))
    y = y + 0.3 * bp(y, 600, 3000, 1)                      # phone case
    ir = reverb_ir(rng, 0.8, 0.6, 0.35, early=[(0.008, 0.2), (0.015, 0.12)])
    y = add_room(y, ir, 0.2)
    return fade(hp(y, 80, 2), 0.002, 0.15)


def gen_phone_pickup(rng):
    """Handset lifted: plastic scrape on the cradle, hook-switch plunger click
    with bounce, faint bell 'tink' from the ringer as the hook flips, cord rustle."""
    n = secs(0.5)
    t = np.arange(n) / FS
    scrape = burst(rng, n, 0.02, 0.045, 1.0, 1000, 5000)
    hook = np.zeros(n)
    for dt, a in [(0.0, 1.0), (0.0012, 0.35)]:
        hook += burst(rng, n, 0.05 + dt, 0.0003, a)
    hook = modal(hook, [(2600, 0.012, 1.0), (4100, 0.008, 0.6), (1300, 0.02, 0.4)])
    tink = modal(impulses(n, [(0.055, 1.0)]), [(f, t60 * 0.2, g) for f, t60, g in PHONE_GONG_A])
    cord_env = np.clip((t - 0.1) / 0.05, 0, 1) * np.clip((0.38 - t) / 0.1, 0, 1)
    cord = bp(rng.standard_normal(n), 150, 900, 2) * cord_env
    y = (0.5 * scrape / np.max(np.abs(scrape))
         + 0.5 * hook / np.max(np.abs(hook))
         + 0.08 * tink / np.max(np.abs(tink))
         + 0.35 * cord / np.max(np.abs(cord)))
    ir = reverb_ir(rng, 0.25, 0.25, 0.15, early=[(0.005, 0.25)])
    return fade(hp(add_room(y, ir, 0.1), 80, 2), 0.002, 0.06)


def gen_dial_tone(rng):
    """450 Hz continuous dial tone (common in 50 Hz-mains regions) heard through
    a handset: transducer non-linearity, 100 Hz line ripple, line hiss,
    300-3400 Hz telephone band, earpiece resonance."""
    n = secs(3.0)
    t = np.arange(n) / FS
    s = np.sin(2 * np.pi * 450 * t)
    s = s + 0.06 * s ** 2 + 0.03 * s ** 3
    s *= 1 + 0.015 * np.sin(2 * np.pi * 100 * t)
    s += 0.006 * rng.standard_normal(n)
    pre = secs(0.2)
    s = np.concatenate([s[-pre:], s])
    s = lp(hp(s, 300, 4), 3400, 4)
    s = s + 0.3 * bp(s, 900, 1300, 1)
    s = s[pre:]
    return fade(s - s.mean(), 0.015, 0.04)


def gen_checkpoint_soft(rng):
    """Rubber stamp onto paper on a wooden desk (soft wide excitation into desk
    modes + paper slap), then the tacky lift of the stamp. Non-tonal on purpose."""
    n = secs(1.0)
    m = secs(0.003)
    soft = np.zeros(n)
    i = secs(0.05)
    soft[i:i + m] = 0.5 - 0.5 * np.cos(np.linspace(0, 2 * np.pi, m))
    desk = modal(soft, [(165, 0.09, 1.0), (290, 0.07, 0.6), (510, 0.05, 0.35),
                        (1150, 0.03, 0.2)])
    slap = burst(rng, n, 0.05, 0.015, 1.0, 600, 4000)
    lift = np.zeros(n)
    for dt in np.sort(rng.uniform(0, 0.006, 4)):
        lift += burst(rng, n, 0.29 + dt, 0.0004, rng.uniform(0.4, 1.0))
    lift = hp(lift, 2000, 2)
    y = (1.0 * desk / np.max(np.abs(desk))
         + 0.5 * slap / np.max(np.abs(slap))
         + 0.12 * lift / np.max(np.abs(lift)))
    ir = reverb_ir(rng, 0.5, 0.4, 0.25, early=[(0.006, 0.2)])
    return fade(hp(add_room(y, ir, 0.15), 50, 2), 0.002, 0.2)


def gen_footstep(rng, index):
    """Leather-sole step on wet terrazzo: heel strike (body thump + hard click),
    sole/toe slap 45-85 ms later, wet squelch + droplet chirps, optional grit."""
    dur = rng.uniform(0.22, 0.32)
    n = secs(dur)
    heel_t = 0.004
    bright = rng.uniform(0.6, 1.0)
    heel_exc = burst(rng, n, heel_t, 0.0012, 1.0)
    heel = modal(heel_exc, [(rng.uniform(85, 130), 0.05, 1.0),
                            (rng.uniform(220, 330), 0.04, 0.6),
                            (rng.uniform(900, 1400), 0.02, 0.3)])
    click = burst(rng, n, heel_t, 0.003, 1.0, 2500, 8000)
    toe_t = heel_t + rng.uniform(0.045, 0.085)
    slap = burst(rng, n, toe_t, 0.008, 1.0, 400, 4000)
    wet_amt = rng.uniform(0.15, 0.4)
    squelch = burst(rng, n, toe_t + 0.004, 0.03, 1.0, 1200, 3500)
    drops = np.zeros(n)
    for _ in range(int(rng.integers(3, 9))):
        drops += chirp_drop(rng, n, toe_t + rng.uniform(0.01, 0.08),
                            rng.uniform(2000, 4500), rng.uniform(0.3, 0.8),
                            rng.uniform(0.004, 0.008), rng.uniform(0.3, 1.0))
    y = (1.0 * heel / np.max(np.abs(heel))
         + 0.5 * bright * click / np.max(np.abs(click))
         + rng.uniform(0.5, 0.8) * slap / np.max(np.abs(slap))
         + wet_amt * squelch / np.max(np.abs(squelch))
         + 0.5 * wet_amt * drops / max(np.max(np.abs(drops)), 1e-9))
    if index in (2, 5):   # two variants with a grit scrape on the sole
        grit = burst(rng, n, toe_t + rng.uniform(0.01, 0.03), 0.02, 1.0, 3000, 7000)
        y += 0.15 * grit / np.max(np.abs(grit))
    refl = y.copy()
    for d, g in [(rng.uniform(0.006, 0.011), 0.25), (rng.uniform(0.014, 0.022), 0.16)]:
        refl[secs(d):] += g * y[: n - secs(d)]
    return fade(hp(refl, 50, 2), 0.002, 0.03)


def _footstep(i):
    return lambda rng: gen_footstep(rng, i)


# --------------------------------------------------------------------------
# Registry
# --------------------------------------------------------------------------
SOUNDS = [
    dict(id="rain_loop", category="ambience_bed", loop=True, target_lufs=-27.0,
         fn=gen_rain_loop,
         use="audio_emitters A_Rain_Arcade, A_Rain_Lobby (L0_B01_layout.json)"),
    dict(id="hum_electrical", category="ambience_bed", loop=True, target_lufs=-29.0,
         fn=gen_hum_electrical,
         use="audio_emitters A_Hum_Cable (L0_B01_layout.json)"),
    dict(id="clock_tick", category="ambience_bed", loop=True, target_lufs=-28.0,
         fn=gen_clock_tick,
         use="audio_emitters A_Clock_Desk (L0_B01_layout.json)"),
    dict(id="queue_chime", category="one_shot", loop=False, target_lufs=-22.0,
         fn=gen_queue_chime,
         use="audio_emitters A_QueueChime, interval 22-38 s (L0_B01_layout.json)"),
    dict(id="paper_pickup", category="one_shot", loop=False, target_lufs=-21.0,
         fn=gen_paper_pickup,
         use="interactables Pickup_JobOrder_2147.sound (L0_B01_layout.json)"),
    dict(id="card_slot", category="one_shot", loop=False, target_lufs=-21.0,
         fn=gen_card_slot,
         use="interactables Pickup_AccessCard_21.sound (L0_B01_layout.json)"),
    dict(id="door_reject", category="one_shot", loop=False, target_lufs=-20.0,
         fn=gen_door_reject,
         use="suggested: Door_Entrance_01 reject step (msg_entrance_reject) and "
             "Door_Basement_01 no-card; not yet bound by a 'sound' field in layout"),
    dict(id="door_release", category="one_shot", loop=False, target_lufs=-20.0,
         fn=gen_door_release,
         use="suggested: Door_Entrance_01 release after release_delay_s "
             "(msg_entrance_release); not yet bound by a 'sound' field in layout"),
    dict(id="door_open", category="one_shot", loop=False, target_lufs=-21.0,
         fn=gen_door_open,
         use="suggested: Door_Entrance_01 / Door_Basement_01 swing open; "
             "not yet bound by a 'sound' field in layout"),
    dict(id="phone_ring", category="one_shot", loop=False, target_lufs=-20.0,
         fn=gen_phone_ring,
         use="suggested: Phone_Counter_01 ring_event phone_ring_once (fired by "
             "Pickup_AccessCard_21.on_pickup_event) and relay to Phone_Wall_01"),
    dict(id="phone_pickup", category="one_shot", loop=False, target_lufs=-22.0,
         fn=gen_phone_pickup,
         use="suggested: Phone_Counter_01 / Phone_Wall_01 on answer"),
    dict(id="dial_tone", category="one_shot", loop=False, target_lufs=-23.0,
         fn=gen_dial_tone,
         use="suggested: Phone_Counter_01 on_answer_msg msg_phone_dialtone"),
    dict(id="checkpoint_soft", category="one_shot", loop=False, target_lufs=-23.5,
         fn=gen_checkpoint_soft,
         use="suggested: Checkpoint_Lobby, Checkpoint_ServiceDoor (msg_checkpoint)"),
] + [
    dict(id=f"footstep_concrete_{i:02d}", category="footstep", loop=False,
         target_lufs=[-25.0, -24.5, -25.5, -24.8, -25.2, -24.6][i - 1],
         fn=_footstep(i),
         use="player locomotion on terrazzo_wet / concrete_wet, random rotation of 6")
    for i in range(1, 7)
]


# --------------------------------------------------------------------------
# Output
# --------------------------------------------------------------------------
def write_wav(path: Path, pcm: np.ndarray) -> None:
    """Canonical 44-byte RIFF/WAVE header + PCM16 LE mono 48 kHz data."""
    data = pcm.astype("<i2").tobytes()
    header = b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVE"
    header += b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, FS, FS * 2, 2, 16)
    header += b"data" + struct.pack("<I", len(data))
    assert len(header) == 44
    path.write_bytes(header + data)


def finalize(x: np.ndarray, spec: dict, rng: np.random.Generator):
    """DC removal, loudness normalisation to the category target, true-peak
    ceiling, TPDF dither and 16-bit quantisation."""
    loop = spec["loop"]
    x = np.asarray(x, dtype=np.float64)
    x = x - np.mean(x)                      # constant shift keeps loops seamless
    if not loop:
        x = fade(x, 0.001, 0.005)           # guarantee silent first/last samples
    lufs = bs1770.integrated_loudness(x, loop=loop)
    gain_db = spec["target_lufs"] - lufs
    x = x * 10 ** (gain_db / 20)
    tp = bs1770.true_peak_db(x, loop=loop)
    limited = False
    if tp > TP_CEILING_DB:
        x = x * 10 ** ((TP_CEILING_DB - tp) / 20)
        limited = True
    dither = (rng.random(len(x)) - rng.random(len(x)))       # +-1 LSB TPDF
    pcm = np.clip(np.round(x * 32767.0 + dither), -32768, 32767).astype(np.int16)
    return pcm, limited


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=REPO, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:
        return ""


def generator_commit() -> str:
    rel = "tools/audio/gen_sfx.py"
    if git("status", "--porcelain", "--", rel, "tools/audio/bs1770.py"):
        return "UNCOMMITTED (working tree differs from HEAD)"
    return git("log", "-1", "--format=%H", "--", rel) or "UNKNOWN"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out-dir", type=Path, default=OUT_DIR)
    ap.add_argument("--only", nargs="*", help="subset of sound ids")
    ap.add_argument("--no-manifest", action="store_true")
    args = ap.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for spec in SOUNDS:
        if args.only and spec["id"] not in args.only:
            continue
        rng = rng_for(spec["id"])
        pcm, limited = finalize(spec["fn"](rng), spec, rng)
        path = args.out_dir / f"{spec['id']}.wav"
        write_wav(path, pcm)
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        print(f"{spec['id']:24s} {len(pcm) / FS:7.3f} s  "
              f"{'peak-limited ' if limited else ''}sha256={sha[:16]}")
        entries.append({
            "id": spec["id"],
            "file": path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else str(path),
            "category": spec["category"],
            "loop": spec["loop"],
            "duration_s": round(len(pcm) / FS, 6),
            "samples": int(len(pcm)),
            "target_lufs": spec["target_lufs"],
            "peak_limited_by_generator": limited,
            "intended_use": spec["use"],
            "licence": LICENCE,
            "sha256": sha,
        })

    if not args.no_manifest and not args.only:
        manifest = {
            "schema": "confession.sound_manifest/1",
            "format_contract": "RIFF WAV, PCM s16le, mono, 48000 Hz, 44-byte header",
            "generator": "tools/audio/gen_sfx.py",
            "generator_commit": generator_commit(),
            "generator_blob_sha1": git("hash-object", "tools/audio/gen_sfx.py"),
            "base_seed": BASE_SEED,
            "categories": CATEGORIES,
            "licence": LICENCE,
            "sounds": entries,
        }
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        print(f"manifest -> {MANIFEST.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
