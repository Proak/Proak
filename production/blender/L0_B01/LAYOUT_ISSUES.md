# L0_B01 layout issues found by the Blender greybox pass

Source: `ue58/Content/Confession/Data/L0_B01_layout.json` (layout_version 0.5.0), **not edited** by this
pass. The environment-artist agent does not own the JSON or `tools/levelgen/`; the layout owner decides fixes.

Evidence: `production/blender/L0_B01/mesh_audit.json` → `layout_analysis` (AABB-based, computed by
`tools/blender_l0_b01_audit.py`), plus the Cycles renders in `renders/` (Blender renders, NOT Unreal).
Numbers are copied from that file. Severity: P1 = visible in a review shot / readability problem,
P2 = visible somewhere a player can stand, P3 = cosmetic or only visible from outside/below.

## P1

1. **Service-window shutter is buried in its frame (coplanar faces).**
   `SM_ServiceWindow_Shutter` (x −3.15…−3.11) lies entirely inside `SM_ServiceWindow_Frame`
   (x −3.21…−3.11); their east faces are coplanar at x = −3.11 over 1.575 m². In `shot_arcade.png` the whole
   window opening renders as a flat black rectangle (Cycles self-shadowing between the coincident faces);
   in UE it will z-fight between `paint_green` and `iron_dark`. The shutter is the backdrop of the first
   pickup (`Pickup_JobOrder_2147`), so this hurts the first focal point.
   Suggested fix (owner): make the frame a hollow surround or push the shutter ≥ 1 cm proud (x ≈ −3.10).

2. **Black band directly above the basement door (landing ceiling end face flush with the lobby wall).**
   `SM_Landing_Ceiling` (y 9.50…13.20, z 2.65…2.85, x ±1.30) ends exactly on the interior face of the lobby
   north wall (y = 9.50); its south end face is coplanar with `SM_Lobby_Wall_N_W`, `_N_Header` and `_N_E`
   (0.13 + 0.26 + 0.13 m²). In `shot_entrance.png` this renders as a black horizontal bar about 2.6 m wide just
   above the lit door plate, over the door that is the lobby's focal point. In UE it will be a
   concrete/plaster z-fight band. Suggested: end the landing ceiling at y = 9.74 (behind the wall) or 9.62.

## P2

3. **Archive shelves float 0.125 m above the floor and have no uprights.**
   All four shelf assemblies (`SM_Shelf_{0..3}_*`): `SM_Shelf_n_Back` bottom at z = 0.125, lowest board at
   z = 0.525; nothing touches the floor (audit: floating component, gap 0.125 m to `SM_Lobby_Floor`). Their
   hidden collision blockers do reach z = 0, so the player collides with an invisible base. In the 1280×720
   renders the gap is subtle (a shadow strip under the back panels in `shot_return.png`); it is primarily a
   geometric finding.

3b. **`Pickup_AccessCard_21` floats 0.115 m above the counter top and is not card-sized.**
   Box 0.45 × 0.10 × 0.29 m, bottom z = 1.205, counter top surface z = 1.09; there is no card-slot housing
   geometry for it to sit in. In `shot_counter.png` it reads as a warm-lit brass block on the counter; the
   float is not obvious from that eye-height angle. (Either add a slot unit or treat this as the slot volume
   and add a real card mesh later.)

4. **Entrance door hinge sits inside the west mullion; leaf clips the mullion and west sidelight while
   swinging.** Hinge x = −0.60 is inside `SM_Entrance_Mullion_W` (x −0.645…−0.595). Door sweep 0°→95°:
   `SM_Entrance_Mullion_W` penetration up to 0.040 m over the whole swing; `SM_Entrance_SideLight_W` up to
   0.0335 m from 4.8° to 95°. Closed, the 1.20 m leaf also overlaps both mullions by 5 mm (clear width
   between mullions is 1.19 m). Suggested: hinge at (−0.595, −9.59) or leaf 1.18 m.
   `Door_Basement_01` sweep (0°→92°) has no interference.
5. **Lamp housings and cable trunks hang in the air.** `SM_LampHousing_{0..3}` top at z = 4.16, ceiling
   underside z = 4.19 (gap 0.03 m); `SM_CableTrunk_{0..5}` gap 0.10 m. No hangers. Visible on the ceiling in
   `shot_entrance.png`.
6. **Counter details float.** `SM_Counter_PassSlot` bottom 0.06 m above `SM_Counter_Top`;
   `SM_Counter_LetterTray_1` 0.05 m above tray 0 with no supports.
7. **"High windows" are frames on a solid wall.** `SM_HighWindow_Frame_{1..5}` are 0.08 m iron boxes on the
   inside face of `SM_Lobby_Wall_W`; there is no opening, glass or light behind them, although the generator
   comment says "exterior night light comes in here". No night light enters the lobby from the west.
8. **Other coplanar faces that will z-fight (player-visible).**
   - `SM_DoorFrame_Basement_W/E` jamb faces are coplanar with the wall jambs (x = ±0.65, 0.33 m² each):
     the frame is embedded in the wall instead of lining the 1.30 m opening.
   - `SM_Arcade_Canopy`, `SM_Arcade_Wall_W`, `SM_Arcade_Parapet_E`, `SM_Arcade_Rail_E` all run through the
     lobby south wall and end flush with its interior face (y = −9.50); same material (concrete) except the
     iron rail end (0.003 m²), so mostly invisible in greybox but will show once textures differ.
   - `Readable_Notice_01` and `SM_NoticeBoard` share their side/top/bottom faces (x 2.625 / 4.175, z 1.30 / 2.20).
   - Every shelf board's end faces are flush with the back panel's end faces (y ends, 0.0035 m² each).
9. **Spot `cone_deg` is ambiguous.** `L_StreetLamp.cone_deg = 55`. This Blender build interprets it as the
   FULL cone angle (Blender `spot_size`). UE's `OuterConeAngle` is a HALF angle; feeding 55 directly in UE would
   give a 110° cone. The JSON should state which.

## P3

10. `SM_StreetLamp_Pole` bottom at z = 0.0 but street surface (`SM_Street` top) is z = −0.20: pole floats 0.20 m.
11. Small deliberate-looking offsets, listed for completeness (they avoid z-fighting, not errors):
    `SM_DoorPlate_Basement`, `SM_EmptyFrame_Wall_Backing`, `SM_NoticeBoard` 5 mm off their walls;
    `Anomaly_EmptyFrame_01` 10 mm off its backing; `SM_ServiceWindow_Lamp` 10 mm off the arcade wall.
12. Wall tops at z = 4.20 coincide at the four lobby corners and where `SM_Arcade_Wall_W` meets
    `SM_Lobby_Wall_S_W`; only visible from above (black dots in `plan_top.png`), never from player height.
13. Two of four lamp housings (`_1`, `_3`) have no light; the generator comment says this is intentional
    ("only two are lit tonight").
14. `L_BasementDoor` (750 lm) is described as "brightest navigation cue in the lobby" while `L_Hall_A`
    (1500 lm) and `L_Hall_C` (1100 lm) emit more; it reads as bright mainly because it is close to the door wall.
