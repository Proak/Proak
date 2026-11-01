#!/usr/bin/env python3
"""Render sanity-check spectrograms of the generated SFX (needs matplotlib).

Writes into production/audio/spectrograms/:
  ambience_bed.png   spectrogram of each loop
  loop_seams.png     each loop tiled twice: spectrogram +-1 s around the wrap and
                     the waveform +-10 ms around the wrap (wrap at t = 0)
  one_shot.png       spectrogram of each one-shot
  footstep.png       spectrogram of each footstep

Usage: python tools/audio/plot_sfx.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

FS = 48000
REPO = Path(__file__).resolve().parents[2]
AUDIO = REPO / "ue58" / "Content" / "Confession" / "Audio"
OUT = REPO / "production" / "audio" / "spectrograms"
MANIFEST = REPO / "production" / "audio" / "sound_manifest.json"


def load(sid):
    raw = (AUDIO / f"{sid}.wav").read_bytes()
    return np.frombuffer(raw[44:], dtype="<i2").astype(np.float64) / 32768.0


def spec(ax, x, title, t0=0.0):
    nfft = 1024 if len(x) > FS else 512
    ax.specgram(x, NFFT=nfft, Fs=FS, noverlap=nfft * 3 // 4, cmap="magma",
                vmin=-130, vmax=-30, xextent=(t0, t0 + len(x) / FS))
    ax.set_ylim(0, 16000)
    ax.set_title(title, fontsize=8)
    ax.tick_params(labelsize=6)
    ax.set_ylabel("Hz", fontsize=6)


def grid(ids, path, title, cols=2):
    rows = int(np.ceil(len(ids) / cols))
    fig, axes = plt.subplots(rows, cols, figsize=(5 * cols, 2.0 * rows), squeeze=False)
    for ax, sid in zip(axes.flat, ids):
        spec(ax, load(sid), sid)
    for ax in list(axes.flat)[len(ids):]:
        ax.axis("off")
    fig.suptitle(title, fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def seams(ids, path):
    fig, axes = plt.subplots(len(ids), 2, figsize=(11, 2.2 * len(ids)), squeeze=False)
    for (a1, a2), sid in zip(axes, ids):
        x = load(sid)
        two = np.concatenate([x, x])
        n = len(x)
        w = FS
        spec(a1, two[n - w:n + w], f"{sid}: spectrogram, wrap at t=0", t0=-1.0)
        a1.axvline(0, color="cyan", lw=0.6, ls="--")
        z = int(0.010 * FS)
        tt = (np.arange(-z, z)) / FS * 1000
        a2.plot(tt, two[n - z:n + z] * 32768, lw=0.6)
        a2.axvline(0, color="red", lw=0.6, ls="--")
        a2.set_title(f"{sid}: waveform +-10 ms around wrap (LSB)", fontsize=8)
        a2.tick_params(labelsize=6)
        a2.set_xlabel("ms", fontsize=6)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = json.loads(MANIFEST.read_text())["sounds"]
    by = {}
    for s in m:
        by.setdefault(s["category"], []).append(s["id"])
    grid(by["ambience_bed"], OUT / "ambience_bed.png", "ambience_bed loops", cols=1)
    seams(by["ambience_bed"], OUT / "loop_seams.png")
    grid(by["one_shot"], OUT / "one_shot.png", "one_shot")
    grid(by["footstep"], OUT / "footstep.png", "footstep")
    for p in sorted(OUT.glob("*.png")):
        print(p.relative_to(REPO), p.stat().st_size)


if __name__ == "__main__":
    main()
