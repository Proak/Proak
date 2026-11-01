# CR-0001 · L0_B01 exit door coordinates (spec vs mesh)

- Raised by: Producer/Integration (Claude), 2026-11-01
- Affects: `production/scene_specs/scene_01_entrance.yaml` (read-only for integration; owner = Level Design)
- Observation: spec says `exit: {x: 3.7, y: 8.4}` and `shot_entrance.aim_m: [3.5, 6.8, 1.7]`, but the v0.4 blockout mesh
  (`production/scripts/build_scene01_blockout.py`) places `SM_Basement_Door` at x=0, y=9.32, and its wall opening is only
  0.90 m wide (spec clear width 115 cm).
- Integration decision for the greybox (reversible): keep the mesh position x=0, widen opening to 1.30 m.
  Data lives in `tools/levelgen/l0_b01_layout_src.py` -> `ue58/Content/Confession/Data/L0_B01_layout.json`.
- Requested decision (Level Design + human director): accept x=0 (door on the central axis, visible from the
  entrance) and update the spec, or move the door to x=3.7 and the layout follows.
- Status: OPEN
