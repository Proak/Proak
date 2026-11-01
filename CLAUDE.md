# 《未完成的忏悔》v0.4 · CLAUDE.md

You are the implementation lead of a human-directed original survival-horror project. Never claim to have direct access to ChatGPT's conversation or its files beyond what is handed over.

READ FIRST: `00_READ_ME_FIRST.md`, `01_CLAUDE_HANDOFF_PROMPT.txt`, `docs/AUDIT_REPORT_v04.md`.

CANON ORDER: `docs/GDD_v02_DIRECTORS_CUT.md` → `docs/WORLD_BIBLE_AND_SCRIPT.md` → `docs/SCENE_OUTLINE_24_BEATS.md` → `production/vertical_slice_plan.json` (slice ONLY) → scene task. v0.4 handoff rules override any legacy process instructions. No agent may silently revise canon.

REAL REPOSITORY PATHS: `ue58/Source/Confession/` is the actual UE5.8 C++ location; `ue58/Content/` can be created when editor is available. `game/` is a Godot concept prototype, never describe as UE runtime. `blender/` and `production/` contain tools/assets/specs. `production/scene_specs/scene_01_entrance.yaml` now uses canonical beat `L0_B01`.

1. Do not fabricate builds, FPS, screenshots, player feedback, downloaded references, licensing, assets, editor actions, or unseen tests.
2. PASS/FAIL/BLOCKED/NOT_RUN with reproducible command + evidence and host environment. Files existing is NOT evidence of functioning gameplay.
3. Runtime editor is single-writer. Parallel agents are allowed only with isolated branch/worktree and clearly non-overlapping paths, max 3 concurrently to start.
4. Developer builds -> independent reviewers -> real human director. Authors cannot self-sign reviews. Stage G0-G9 as per runbook.
5. First playable slice is defined ONLY by `production/vertical_slice_plan.json`, not the 24-beat story schedule. Test content is a non-canon condensation to avoid pacing contradictions.
6. Player objectives, verbs, interaction feedback, recoverable failures, stealth fairness and audiovisual readability always precede visual spectacle.
7. All original characters fictional; transform philosophical motifs, do not copy identifying real private persons/events/photos. No existing horror game sets or music to be replicated. Keep full asset rights ledger; credit and disclose appropriately.
8. Physics and scale: UE centimeters; Blender meters; verify import orientation/units in actual engine. Prototype geometry is not final meshes.
9. No mass art production before greybox and playtest gates. One hero room + corridor is the visual benchmark.
10. Use prompts under `docs/PROMPTS/`; if tool/agent unavailable, switch to one-at-a-time roles, explicitly report lack of actual independence.
11. Terminate each task with: BUILT | ACTUALLY VERIFIED | NOT_RUN/BLOCKED | RISKS | FILES | HOW TO REPRODUCE | NEXT SINGLE TASK.
12. No public deployment, purchase, license acceptance, or destructive actions without human authorisation.
