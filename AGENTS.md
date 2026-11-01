# Rules for automated game-production agents

This repo has two simultaneous tracks:
- ChatGPT / gameplay + narrative integration: `docs/GDD_v02_DIRECTORS_CUT.md`, `docs/WORLD_BIBLE_AND_SCRIPT.md`, `game/scripts/`, UE gameplay integration.
- Claude / technical art and QA: `blender/`, `production/claude_art/`, `production/reference/`, `production/qa/CLAUDE_*`.

Never simultaneously modify the same file. Work on branches. Do not rewrite the philosophical premises or add a generic AI/is-a-simulation ending.

Every claimed artifact must exist on disk. A concept image is NOT a Blender mesh or Unreal screenshot. No runtime pass without editor/runtime evidence.

Production gate: scene research with sources -> storyboard -> measured blockout -> 3 camera review -> Blender mesh/UV/tex QA -> UE import -> playable QA -> profiling -> approval.

Engine is UE 5.8 for shipping; Godot is an independent mechanics sandbox only.

No personal photos or medical/identity data in commits. Use fictionalized characters. Track licensing and full provenance for every external asset.
