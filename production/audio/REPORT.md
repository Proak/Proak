# L0_B01 audio placeholder set — report (audio-director agent, committed by producer)

Status: 19 original procedurally generated WAVs (PCM16 mono 48 kHz). **Not listened to by a human, not tested in UE 5.8.**
The agent's harness blocked writing this file; the producer transcribed it from the agent's hand-back.

## Commands (repo root, Linux, Python 3.13.18; venv with numpy 2.5.4, scipy 1.18.1, matplotlib 3.11.2)
| step | command | exit |
|---|---|---|
| generate | `python tools/audio/gen_sfx.py` | 0 |
| analyse (first draft) | `python tools/audio/analyze_sfx.py` | **1** (clock_tick, door_release, phone_pickup below LUFS range; analyzer JSON bug) |
| fix + re-run | gen / analyze | 0 / 0 |
| spectrograms | `python tools/audio/plot_sfx.py` | 0 (revealed a footstep/rain HF generator bug -> fixed -> 0/0/0) |
| determinism | regenerate to scratch, compare sha256 | 0 (19/19 identical) |
| negative test | 5 corrupted copies through analyzer | 1 as expected; every corruption caught |

Full numbers: `production/audio/audio_report.json`; ids/uses/sha256: `sound_manifest.json`.

## Loudness targets (studio-defined)
Ambience beds -30..-26 LUFS · one-shots -24..-18 LUFS · footsteps -28..-22 LUFS · true peak <= -1 dBTP.
Meter: own mono BS.1770-4 implementation (sine self-test -23.01 LUFS vs -23.01 expected); short clips padded to one 400 ms block; true peak via 4x oversampling (approximation).

## Design notes
- phone_ring: electromechanical bell, one 1 s ring + ring-out (cadence handled by runtime).
- dial_tone: 450 Hz, 300–3400 Hz band-limited.
- clock_tick: uneven tick/tock 0.482/0.518 s, ±4 ms jitter, one 22 ms hesitation; exactly 8 s loop.
- hum_electrical: 50 Hz family, all partials periodic over 8 s. rain_loop: 1 s crossfaded loop.
- door_open: creak kept below ~3.1 kHz (no screech). checkpoint_soft: rubber stamp on wood, non-tonal.

## Limitations
- Placeholders, not a mix. No human listening, no engine playback, in-engine loop seamlessness unverified.
- Seam detector cannot distinguish good vs arbitrary cuts in broadband noise (rain); it did catch a broken hum seam.
- Ledger rows in `audio_ledger_addendum.csv` have `rights_verified=PENDING` (author cannot self-verify).

## Open canon questions for the director
1. Beat sheet says the desk clock is *stopped at 4:17*; scene spec says Clock_Wall_01 stopped at 0417 and Clock_Desk_01 *ticking out of sync*. Built: ticking desk clock (spec). Needs director confirmation.
2. Relay ring from the far phone reuses `phone_ring` with engine distance attenuation.
