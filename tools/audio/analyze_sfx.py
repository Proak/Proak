#!/usr/bin/env python3
"""Re-read every WAV produced by gen_sfx.py and verify the runtime contract.

Checks per file (FAIL makes the script exit 1):
  * header: exact canonical 44-byte RIFF/WAVE, fmt chunk size 16, PCM (1),
    mono, 48000 Hz, byte rate 96000, block align 2, 16 bit, 'data' chunk
    immediately after, RIFF/data sizes consistent with the file size,
    no extra chunks / trailing bytes
  * file name == sound id listed in production/audio/sound_manifest.json,
    sha256 matches the manifest
  * duration inside the brief's window for that id
  * true peak (4x oversampled, approx.) <= -1.0 dBTP and sample peak <= -1.0 dBFS
  * clipping: no samples at +32767 / -32768
  * DC offset |mean| < 0.001 (-60 dBFS)
  * integrated loudness inside the category range
  * one-shots: first and last sample |x| <= -60 dBFS (no start/end click)
  * loops: seam |last - first| no larger than the 99.9th percentile of
    in-file |x[n+1] - x[n]|, and the high-pass (>4 kHz, 2nd difference)
    energy in a 256-sample window centred on the seam must not exceed the
    99th percentile of the same metric over all circular windows of the loop

Usage:
    python tools/audio/analyze_sfx.py [--audio-dir DIR] [--report PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bs1770  # noqa: E402

FS = 48000
REPO = Path(__file__).resolve().parents[2]
AUDIO_DIR = REPO / "ue58" / "Content" / "Confession" / "Audio"
MANIFEST = REPO / "production" / "audio" / "sound_manifest.json"
REPORT = REPO / "production" / "audio" / "audio_report.json"

# Duration windows from the audio brief (seconds, inclusive).
DURATION_WINDOWS = {
    "rain_loop": (12.0, 20.0),
    "hum_electrical": (6.0, 10.0),
    "clock_tick": (8.0, 8.0),
    "queue_chime": (2.0, 3.5),
    "paper_pickup": (0.0, 1.0),
    "card_slot": (0.0, 1.0),
    "door_reject": (0.5, 0.7),
    "door_release": (0.7, 0.9),
    "door_open": (1.5, 2.2),
    "phone_ring": (2.3, 2.7),
    "phone_pickup": (0.0, 0.6),
    "dial_tone": (3.0, 3.0),
    "checkpoint_soft": (0.0, 1.2),
    **{f"footstep_concrete_{i:02d}": (0.18, 0.35) for i in range(1, 7)},
}
CATEGORY_LUFS = {
    "ambience_bed": (-30.0, -26.0),
    "one_shot": (-24.0, -18.0),
    "footstep": (-28.0, -22.0),
}
PEAK_MAX_DB = -1.0
DC_MAX = 0.001
EDGE_MAX_DB = -60.0


def parse_wav(path: Path):
    raw = path.read_bytes()
    problems = []
    if len(raw) < 44:
        return None, ["file shorter than 44 bytes"]
    riff, riff_size, wave = struct.unpack("<4sI4s", raw[:12])
    fmt_id, fmt_size, fmt_tag, ch, rate, brate, balign, bits = struct.unpack("<4sIHHIIHH", raw[12:36])
    data_id, data_size = struct.unpack("<4sI", raw[36:44])
    exp = {
        "riff_id": (riff, b"RIFF"), "wave_id": (wave, b"WAVE"),
        "fmt_id": (fmt_id, b"fmt "), "fmt_size": (fmt_size, 16),
        "format_tag_pcm": (fmt_tag, 1), "channels": (ch, 1),
        "sample_rate": (rate, FS), "byte_rate": (brate, FS * 2),
        "block_align": (balign, 2), "bits_per_sample": (bits, 16),
        "data_id_at_36": (data_id, b"data"),
        "riff_size": (riff_size, len(raw) - 8),
        "data_size": (data_size, len(raw) - 44),
    }
    for k, (got, want) in exp.items():
        if got != want:
            problems.append(f"{k}: got {got!r}, want {want!r}")
    if data_size % 2:
        problems.append("odd data size")
    pcm = np.frombuffer(raw[44:44 + (data_size // 2) * 2], dtype="<i2")
    return pcm, problems


def _hf(x):
    sos = butter(4, 4000, "highpass", fs=FS, output="sos")
    return np.diff(sosfilt(sos, x), n=2)


def seam_metrics(x: np.ndarray) -> dict:
    """x float in [-1, 1). Evaluate the loop wrap point."""
    d = np.abs(np.diff(x))
    seam_delta = abs(float(x[0]) - float(x[-1]))
    p999 = float(np.percentile(d, 99.9))
    # circular high-frequency energy: filter the loop tiled 3x, keep middle copy
    n = len(x)
    hf = _hf(np.tile(x, 3))[n:2 * n]          # index 0 ~ sample just after the wrap
    hf2 = hf * hf
    w = 256
    csum = np.concatenate([[0.0], np.cumsum(np.concatenate([hf2, hf2[:w]]))])
    win = (csum[w:w + n] - csum[:n])             # window starting at each index
    seam_idx = (n - w // 2) % n                  # window centred on the wrap
    seam_e = float(win[seam_idx])
    p99 = float(np.percentile(win, 99))
    med = float(np.median(win))
    return {
        "seam_abs_delta": seam_delta,
        "seam_abs_delta_lsb": int(round(seam_delta * 32768)),
        "in_file_abs_delta_p99_9": p999,
        "seam_delta_ok": seam_delta <= p999,
        "seam_hf_energy": seam_e,
        "hf_energy_p99": p99,
        "hf_energy_median": med,
        "seam_hf_ratio_to_median": (seam_e / med) if med > 0 else None,
        "seam_hf_percentile_rank": float(np.mean(win <= seam_e) * 100.0),
        "seam_click_ok": seam_e <= p99,
        "first_sample": int(round(float(x[0]) * 32768)),
        "last_sample": int(round(float(x[-1]) * 32768)),
    }


def db(v):
    return float("-inf") if v <= 0 else 20 * np.log10(v)


def r(v, nd=2):
    if v is None:
        return None
    if isinstance(v, float) and not np.isfinite(v):
        return str(v)
    return round(float(v), nd)


def analyze(path: Path, spec: dict) -> dict:
    sid = path.stem
    checks = {}
    pcm, header_problems = parse_wav(path)
    checks["header_canonical"] = not header_problems
    res = {"id": sid, "file": path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else str(path),
           "bytes": path.stat().st_size, "header_problems": header_problems}
    if pcm is None or len(pcm) == 0:
        res["checks"] = checks
        res["pass"] = False
        return res
    loop = bool(spec.get("loop"))
    cat = spec.get("category")
    x = pcm.astype(np.float64) / 32768.0
    dur = len(pcm) / FS
    lo, hi = DURATION_WINDOWS.get(sid, (0, 1e9))
    checks["duration_in_window"] = lo - 1e-9 <= dur <= hi + 1e-9
    checks["filename_matches_id"] = sid == spec.get("id")
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    checks["sha256_matches_manifest"] = sha == spec.get("sha256")

    speak = bs1770.sample_peak_db(x)
    tpeak = bs1770.true_peak_db(x, loop=loop)
    lufs = bs1770.integrated_loudness(x, loop=loop)
    mmax = bs1770.max_momentary(x, loop=loop)
    rms_db = db(float(np.sqrt(np.mean(x * x))))
    dc = float(np.mean(x))
    clips = int(np.sum((pcm == 32767) | (pcm == -32768)))
    checks["sample_peak_le_-1dBFS"] = speak <= PEAK_MAX_DB
    checks["true_peak_le_-1dBTP"] = tpeak <= PEAK_MAX_DB
    checks["no_clipping"] = clips == 0
    checks["dc_offset_ok"] = abs(dc) < DC_MAX
    lr = CATEGORY_LUFS.get(cat)
    checks["loudness_in_category"] = bool(lr and lr[0] <= lufs <= lr[1])
    res.update({
        "category": cat, "loop": loop, "samples": int(len(pcm)),
        "duration_s": round(dur, 4),
        "sample_peak_dbfs": r(speak), "true_peak_dbtp_approx": r(tpeak),
        "rms_dbfs": r(rms_db), "integrated_lufs": r(lufs),
        "max_momentary_lufs": r(mmax),
        "category_lufs_range": list(lr) if lr else None,
        "dc_offset": r(dc, 6), "clipped_samples": clips, "sha256": sha,
    })
    if loop:
        sm = seam_metrics(x)
        checks["loop_seam_delta"] = sm["seam_delta_ok"]
        checks["loop_seam_no_click"] = sm["seam_click_ok"]
        res["loop_seam"] = {k: (bool(v) if isinstance(v, (bool, np.bool_))
                                else r(v, 6) if isinstance(v, float) else v)
                            for k, v in sm.items()}
    else:
        first_db, last_db = db(abs(x[0])), db(abs(x[-1]))
        checks["edges_silent"] = first_db <= EDGE_MAX_DB and last_db <= EDGE_MAX_DB
        res["edge_samples"] = [int(pcm[0]), int(pcm[-1])]
    checks = {k: bool(v) for k, v in checks.items()}
    res["checks"] = checks
    res["pass"] = all(checks.values())
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verify generated SFX WAVs")
    ap.add_argument("--audio-dir", type=Path, default=AUDIO_DIR)
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--report", type=Path, default=REPORT)
    args = ap.parse_args(argv)

    st = bs1770.selftest()
    manifest = json.loads(args.manifest.read_text())
    specs = {s["id"]: s for s in manifest["sounds"]}
    results, failures = [], []
    if not st["pass"]:
        failures.append("bs1770 selftest")

    expected = set(DURATION_WINDOWS)
    found = {p.stem for p in args.audio_dir.glob("*.wav")}
    missing = sorted(expected - found)
    unexpected = sorted(found - expected)
    if missing:
        failures.append(f"missing: {missing}")
    if unexpected:
        failures.append(f"unexpected wavs: {unexpected}")
    non_wav = sorted(p.name for p in args.audio_dir.iterdir() if p.suffix.lower() != ".wav")

    for sid in sorted(found & expected, key=list(DURATION_WINDOWS).index):
        res = analyze(args.audio_dir / f"{sid}.wav", specs.get(sid, {}))
        results.append(res)
        if not res["pass"]:
            failures.append(f"{sid}: " + ", ".join(k for k, v in res["checks"].items() if not v))

    hdr = f"{'id':24s} {'dur_s':>7s} {'peak':>7s} {'tp':>7s} {'rms':>7s} {'LUFS':>7s} {'dc':>9s} {'clip':>4s}  seam/edges  result"
    print(f"bs1770 selftest: measured {st['measured_lufs']} LUFS, expected {st['expected_lufs']} -> {'PASS' if st['pass'] else 'FAIL'}")
    print(hdr)
    for res in results:
        if "loop_seam" in res:
            s = res["loop_seam"]
            extra = f"d={s['seam_abs_delta_lsb']}lsb hf_rank={s['seam_hf_percentile_rank']:.1f}%"
        else:
            extra = f"edges={res.get('edge_samples')}"
        print(f"{res['id']:24s} {res.get('duration_s', 0):7.3f} {res.get('sample_peak_dbfs')!s:>7s} "
              f"{res.get('true_peak_dbtp_approx')!s:>7s} {res.get('rms_dbfs')!s:>7s} "
              f"{res.get('integrated_lufs')!s:>7s} {res.get('dc_offset')!s:>9s} "
              f"{res.get('clipped_samples')!s:>4s}  {extra}  {'PASS' if res['pass'] else 'FAIL'}")

    report = {
        "schema": "confession.audio_report/1",
        "tool": "tools/audio/analyze_sfx.py",
        "audio_dir": args.audio_dir.relative_to(REPO).as_posix() if args.audio_dir.is_relative_to(REPO) else str(args.audio_dir),
        "loudness_method": ("ITU-R BS.1770-4 K-weighting (48 kHz coefficients), 400 ms blocks, "
                            "75% overlap, -70 LUFS absolute / -10 LU relative gate, mono G=1. "
                            "Clips < 400 ms zero-padded to one block. Loops: filters primed by "
                            "one extra loop pass. True peak: 4x resample_poly oversampling "
                            "(approximation of BS.1770 Annex 2)."),
        "bs1770_selftest": st,
        "limits": {"peak_max_db": PEAK_MAX_DB, "dc_max": DC_MAX, "edge_max_db": EDGE_MAX_DB,
                   "category_lufs": CATEGORY_LUFS, "duration_windows": DURATION_WINDOWS},
        "missing": missing, "unexpected": unexpected, "non_wav_files_in_dir": non_wav,
        "files": results,
        "failures": failures,
        "pass": not failures,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    print(f"report -> {args.report}")
    if failures:
        print("FAIL:\n  " + "\n  ".join(failures))
        return 1
    print(f"ALL {len(results)} FILES PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
