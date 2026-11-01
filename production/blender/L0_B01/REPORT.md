# L0_B01 Blender 5.2 greybox — report

Author: environment-artist agent (build/audit/render, commit `056ce37`). The agent's harness blocked report-file writes;
this file was transcribed by the producer from the agent's hand-back. Producer additions are marked **[producer]**.

## Host & commands
- `Blender 5.2.3 LTS | build hash e13b728c6880` as the `bpy` module (PyPI wheel), Python 3.13.18, 4 CPU cores, Cycles CPU + OIDN.
- `$PY blender/l0_b01_greybox.py` → exit 0, 331.5 s total (renders: arcade 64.5 s, entrance 70.9 s, counter 72.5 s, return 71.5 s, plan 50.4 s).
- `$PY tools/blender_l0_b01_audit.py` → exit 0, overall PASS.
- Earlier trial runs found and fixed: shared mesh data broke FBX material indices (now one mesh per object, 0 warnings);
  fixed min-EV exposure blew images out (now metered per shot).

## Build
120 layout boxes → 120 objects named by id, scale applied (real size in vertices), collections per layout group plus
`interactables`, `lights`, `cameras`, `plan_labels`; 4 shelf collision blockers hidden from render; doors pivot at hinge (closed);
world-scaled box-projection UVs (1 UV = 1 m); 14 Principled materials from the JSON; cameras 78° horizontal FOV (22.23 mm on 36 mm).

## Light units / exposure (documented assumptions)
- Blender W = lumens / 683 (same constant as Blender's glTF add-on). Physical check: 4π W point 1 m over white plane → 0.31811 vs 1/π = 0.31831.
- Exposure imitates UE histogram auto-exposure: metering render → EV100 clamped to layout `[auto_exposure_min_ev100, max]` →
  Blender exposure = log2(683 / (1.2·2^EV100)) + exposure_bias. Metered: arcade +7.61, entrance +7.60, counter +7.95, return +9.03 stops.

## Exports
- FBX 7400: `apply_unit_scale=True`, `apply_scale_options='FBX_SCALE_UNITS'`, `axis_forward='-Z'`, `axis_up='Y'`, `use_custom_props=True`;
  read back UnitScaleFactor 100, 130 models; re-import floor 13 × 19 × 0.22 m.
- GLB: 124 visible meshes, 7 lights, 4 cameras; the 2 rect (AREA) lights are dropped by the glTF exporter.
- **UE import NOT tested.**

## Audit (`mesh_audit.json`)
130 meshes (124 render-visible), 1,560 tris; non-manifold 0, flipped 0, zero-area 0, missing UV 0, unapplied scale 0;
dimensions/locations match layout ±0.1 mm; every id exactly once. Informational: 98 coplanar same-facing pairs, 24 floating groups.

## Renders (`renders/`, 1280×720, stamped "BLENDER 5.2 GREYBOX RENDER — NOT AN UNREAL SCREENSHOT")
Agent's factual descriptions are in the hand-back; issues found are in `LAYOUT_ISSUES.md`.

**[producer] My own read of the v0.5.0 renders (not an approval):**
- `shot_entrance`: the basement door is the clear focal point and the maintenance line leads to it; but the black landing-ceiling bar
  sits over the door, and the whole lobby is lifted by exposure into an even, bright grey that reads as a daytime office, not
  pre-dawn. The 13 × 19 m floor is mostly empty (empty-room risk, also visible in the reachability plot).
- `shot_arcade`: the service-window shutter renders as a black hole behind the first pickup; the arcade reads as an interior
  corridor (no rain, no street, nothing open); the entrance reads as dark slabs, not a door.

## Producer follow-up
Layout v0.5.1 (`tools/levelgen/l0_b01_layout_src.py`, see `fixes_vs_v04` in the JSON) addresses the 2 P1 and most P2 items:
shutter in front of frame, landing ceiling end inside the wall, grounded shelves with uprights, ceiling details touching the
ceiling, counter props resting on the top, a real card-slot housing with a protruding card, entrance hinge moved off the mullion,
coplanar faces offset, door lamp raised to the brightest cue (1600 lm vs hall 900/700), exposure bias −1 EV as a lighting proposal.
Not addressed: high windows are still frames on a solid wall; rain/street openness; the empty lobby floor (level-design task).

## What this is NOT
No final art, no textures/bevels, no lightmap UVs, not a Lumen match (Cycles, opaque glass, no fog), no UE import/collision/perf test,
no independent art-critic review, no director sign-off.
