#!/usr/bin/env python3
"""Source of truth generator for the L0_B01 greybox layout (rain arcade + lobby + service landing).

Writes ue58/Content/Confession/Data/L0_B01_layout.json, which is consumed by:
  * UE runtime builder  (ue58/Source/Confession/.../ConfessionGreyboxBuilder.cpp)
  * Blender 5.2 builder (blender/l0_b01_greybox.py)
  * Geometry reachability check (tools/layout_reachability.py)

Coordinates: metres, Blender convention (+X east, +Y north toward Door_Basement_01, +Z up).
UE conversion (matches the standard Blender->FBX->UE import): UE = (x*100, -y*100, z*100).

Geometry derived from production/blockout (v0.4) with fixes recorded in FIXES below.
Story text is quoted from docs/WORLD_BIBLE_AND_SCRIPT.md; nothing here changes canon.
Run:  python3 tools/levelgen/l0_b01_layout_src.py          (writes the json)
      python3 tools/levelgen/l0_b01_layout_src.py --check  (exit 1 if json is stale)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ue58" / "Content" / "Confession" / "Data" / "L0_B01_layout.json"

FIXES = [
    "v0.4 blockout rear-wall opening was 0.90 m while the door is 1.15 m and spec clear width is 1.15 m: opening widened to 1.30 m, door leaf 1.20 m.",
    "v0.4 Frame_Empty_01 (x=6.3,y=1.0) was hidden behind archive shelf bay j=3: shelf bay removed, frame moved into the free wall bay at y=1.6.",
    "Spec scene_01_entrance.yaml lists exit at x=3.7 but blockout mesh places the basement door at x=0: geometry (x=0) kept, spec flagged in production/change_requests/CR-0001.",
    "Added the canonical rain arcade (L0_B01 '雨廊入口') south of the lobby; v0.4 blockout had only the lobby.",
    "v0.5.1 (Blender review LAYOUT_ISSUES.md): shutter moved in front of frame; landing ceiling end hidden in wall; shelves grounded with uprights; hanging details touch ceiling; counter props rest on top; real card-slot housing; entrance hinge moved off mullion; coplanar faces offset; door lamp made brightest cue; exposure bias -1 EV (lighting proposal).",
    "Added service landing behind Door_Basement_01 so the second checkpoint is reachable and the door is not a wall texture.",
]

MATERIALS = {
    # base colour is linear RGB 0-1; values are greybox intent, not final PBR.
    "terrazzo_wet":   {"color": [0.20, 0.21, 0.21], "roughness": 0.45, "metallic": 0.0},
    "concrete_wall":  {"color": [0.40, 0.40, 0.38], "roughness": 0.90, "metallic": 0.0},
    "concrete_wet":   {"color": [0.17, 0.18, 0.18], "roughness": 0.35, "metallic": 0.0},
    "plaster_civic":  {"color": [0.46, 0.47, 0.43], "roughness": 0.85, "metallic": 0.0},
    "paint_green":    {"color": [0.10, 0.16, 0.14], "roughness": 0.55, "metallic": 0.0},
    "iron_dark":      {"color": [0.05, 0.06, 0.06], "roughness": 0.50, "metallic": 0.6},
    "brass_aged":     {"color": [0.36, 0.27, 0.15], "roughness": 0.45, "metallic": 0.8},
    "paper_aged":     {"color": [0.68, 0.61, 0.47], "roughness": 0.90, "metallic": 0.0},
    "cardboard":      {"color": [0.42, 0.33, 0.22], "roughness": 0.95, "metallic": 0.0},
    "glass_dark":     {"color": [0.08, 0.10, 0.11], "roughness": 0.08, "metallic": 0.0},
    "line_ochre":     {"color": [0.50, 0.34, 0.04], "roughness": 0.60, "metallic": 0.0},
    "asphalt_wet":    {"color": [0.03, 0.035, 0.04], "roughness": 0.25, "metallic": 0.0},
    "emissive_warm":  {"color": [1.00, 0.78, 0.52], "roughness": 0.50, "metallic": 0.0, "emissive": 4.0},
    "rubber_black":   {"color": [0.02, 0.02, 0.02], "roughness": 0.80, "metallic": 0.0},
}

geometry: list[dict] = []


def box(gid: str, center, size, material: str, group: str, collision: bool = True, note: str = "") -> None:
    g = {"id": gid, "kind": "box", "center": [round(v, 4) for v in center],
         "size": [round(v, 4) for v in size], "material": material, "group": group,
         "collision": collision}
    if note:
        g["note"] = note
    geometry.append(g)


# ---------------------------------------------------------------- lobby shell (13 x 19 x 4.2)
box("SM_Lobby_Floor", (0, 0, -0.11), (13, 19, 0.22), "terrazzo_wet", "shell")
box("SM_Lobby_Ceiling", (0, 0, 4.30), (13, 19, 0.22), "plaster_civic", "shell")
box("SM_Lobby_Wall_W", (-6.62, 0, 2.1), (0.24, 19.24, 4.2), "plaster_civic", "shell")
box("SM_Lobby_Wall_E", (6.62, 0, 2.1), (0.24, 19.24, 4.2), "plaster_civic", "shell")
# south (entrance) wall: opening x in [-1.575, 1.575], z in [0, 3.3]
for s in (-1, 1):
    box(f"SM_Lobby_Wall_S_{'W' if s < 0 else 'E'}", (s * 4.1, -9.62, 2.1), (5.05, 0.24, 4.2), "concrete_wall", "shell")
box("SM_Lobby_Wall_S_Header", (0, -9.62, 3.75), (3.15, 0.24, 0.9), "concrete_wall", "shell")
# entrance frame: fixed side lights + transom, door leaf is an interactable (Door_Entrance_01)
for s in (-1, 1):
    box(f"SM_Entrance_SideLight_{'W' if s < 0 else 'E'}", (s * 1.0875, -9.62, 1.65), (0.975, 0.08, 3.3), "glass_dark", "shell",
        note="opaque in UE greybox (no translucent asset yet)")
box("SM_Entrance_Transom", (0, -9.62, 2.8), (1.2, 0.08, 1.0), "glass_dark", "shell")
box("SM_Entrance_Mullion_W", (-0.62, -9.62, 1.65), (0.05, 0.12, 3.3), "iron_dark", "detail")
box("SM_Entrance_Mullion_E", (0.62, -9.62, 1.65), (0.05, 0.12, 3.3), "iron_dark", "detail")
# north (basement) wall: opening x in [-0.65, 0.65], z in [0, 2.2]
for s in (-1, 1):
    box(f"SM_Lobby_Wall_N_{'W' if s < 0 else 'E'}", (s * 3.635, 9.62, 2.1), (5.97, 0.24, 4.2), "plaster_civic", "shell")
box("SM_Lobby_Wall_N_Header", (0, 9.62, 3.2), (1.3, 0.24, 2.0), "plaster_civic", "shell")
box("SM_DoorFrame_Basement_W", (-0.66, 9.5, 1.1), (0.04, 0.3, 2.2), "paint_green", "detail")
box("SM_DoorFrame_Basement_E", (0.66, 9.5, 1.1), (0.04, 0.3, 2.2), "paint_green", "detail")
box("SM_DoorPlate_Basement", (0, 9.48, 2.42), (0.62, 0.03, 0.22), "brass_aged", "detail", collision=False,
    note="plate reads 维修通道 / SERVICE in later art pass")

# front counter (enclosed post office counter, west)
box("SM_Counter_Base", (-3.45, -0.35, 0.50), (4.25, 1.05, 1.0), "paint_green", "prop")
box("SM_Counter_Top", (-3.45, -0.35, 1.045), (4.5, 1.2, 0.09), "brass_aged", "prop")
box("SM_Counter_Screen_Rail", (-3.5, 0.25, 2.0), (4.45, 0.13, 0.11), "iron_dark", "prop")
for s in (-1, 1):
    box(f"SM_Counter_Screen_Post_{'W' if s < 0 else 'E'}", (-3.5 + s * 2.18, 0.25, 2.45), (0.10, 0.12, 2.9), "iron_dark", "prop")
box("SM_Counter_Screen_Glass", (-3.5, 0.25, 2.95), (4.26, 0.03, 1.9), "glass_dark", "prop")
box("SM_Counter_PassSlot", (-3.4, -0.955, 1.14), (0.65, 0.11, 0.10), "paper_aged", "prop")
box("SM_Counter_LetterTray_0", (-4.75, 0.04, 1.145), (0.6, 0.55, 0.11), "iron_dark", "prop")
box("SM_Counter_LetterTray_1", (-4.75, 0.04, 1.255), (0.6, 0.55, 0.11), "iron_dark", "prop")
box("SM_CardSlot_Housing", (-4.35, -0.905, 1.24), (0.30, 0.06, 0.20), "iron_dark", "prop",
    note="CardSlot_01 housing on the counter front; the card protrudes from it")
box("SM_Desk_Clock", (-2.5, -0.5, 1.265), (0.34, 0.23, 0.35), "iron_dark", "prop",
    note="Clock_Desk_01 ticking out of sync (audio emitter clock_tick)")

# archive shelving (east). Bay j=3 removed to free the empty-frame wall (see FIXES).
for j, y in enumerate((-5.5, -3.3, -1.1, 4.4)):
    box(f"SM_Shelf_{j}_Back", (6.0, y, 1.80), (0.10, 1.82, 3.6), "iron_dark", "prop")
    for h in (0.55, 1.15, 1.80, 2.45, 3.15):
        box(f"SM_Shelf_{j}_Board_{int(h * 100)}", (5.6, y, h), (0.84, 1.76, 0.05), "iron_dark", "prop")
    for k in range(4):
        box(f"SM_Shelf_{j}_FileBox_{k}", (5.57, y - 0.65 + k * 0.42, 1.385), (0.35, 0.29, 0.42), "cardboard", "prop",
            collision=False)
    for s_, yy_ in (("S", y - 0.9), ("N", y + 0.9)):
        box(f"SM_Shelf_{j}_Upright_{s_}", (5.2, yy_, 1.8), (0.04, 0.04, 3.6), "iron_dark", "prop", collision=False)
    box(f"SM_Shelf_{j}_Collision", (5.6, y, 1.75), (0.9, 1.82, 3.5), "iron_dark", "collision", note="invisible blocker")
box("SM_EmptyFrame_Wall_Backing", (6.47, 1.6, 1.95), (0.05, 1.5, 1.85), "plaster_civic", "detail", collision=False)

# west pillars + high windows (exterior night light comes in here)
for i in range(1, 6):
    yy = -7.4 + i * 2.8
    box(f"SM_Pillar_W_{i}", (-6.25, yy, 2.1), (0.5, 0.55, 4.2), "concrete_wall", "shell")
    box(f"SM_HighWindow_Frame_{i}", (-6.48, yy + 1.4, 3.35), (0.08, 1.2, 0.9), "iron_dark", "detail", collision=False)

# ceiling lamp housings (only two are lit tonight; see lights)
for j, yy in enumerate((-5.9, -2.6, 0.7, 4.0)):
    box(f"SM_LampHousing_{j}", (-0.8, yy, 4.12), (1.2, 0.32, 0.14), "iron_dark", "detail", collision=False)
for j in range(6):
    box(f"SM_CableTrunk_{j}", (2.2, -7.2 + j * 3.0, 4.13), (0.12, 2.72, 0.12), "iron_dark", "detail", collision=False)

box("SM_NoticeBoard", (3.4, 9.47, 1.75), (1.65, 0.05, 1.0), "paper_aged", "detail", collision=False)
box("SM_Wall_Clock", (1.6, 9.47, 3.2), (0.62, 0.06, 0.62), "brass_aged", "detail", collision=False,
    note="Clock_Wall_01 stopped at 04:17")
box("SM_Wall_Phone_Bracket", (-2.4, 9.47, 1.45), (0.25, 0.06, 0.32), "iron_dark", "detail", collision=False)

# maintenance line: canon '进入后沿维修标线走' — primary navigation cue, no HUD arrow
box("SM_MaintLine_Arcade", (0.3, -13.35, 0.003), (0.08, 7.5, 0.006), "line_ochre", "detail", collision=False)
box("SM_MaintLine_Lobby", (0.3, 0.0, 0.003), (0.08, 18.9, 0.006), "line_ochre", "detail", collision=False)

# ---------------------------------------------------------------- rain arcade (canopied walkway)
box("SM_Arcade_Floor", (0.2, -13.4, -0.11), (6.8, 7.8, 0.22), "concrete_wet", "arcade")
box("SM_Arcade_Canopy", (0.3, -13.46, 3.35), (7.4, 7.68, 0.2), "concrete_wall", "arcade")
box("SM_Arcade_Wall_W", (-3.32, -13.46, 2.1), (0.24, 7.68, 4.2), "concrete_wall", "arcade")
box("SM_Arcade_Gate_S", (0.2, -17.32, 1.6), (6.8, 0.24, 3.2), "iron_dark", "arcade",
    note="closed roller gate the player came through; not interactive")
box("SM_Arcade_Parapet_E", (3.48, -13.46, 0.55), (0.25, 7.68, 1.1), "concrete_wall", "arcade")
box("SM_Arcade_Rail_E", (3.48, -13.46, 1.12), (0.06, 7.68, 0.05), "iron_dark", "detail", collision=False)
for i, yy in enumerate((-16.9, -14.2, -11.5, -9.95)):
    box(f"SM_Arcade_Column_{i}", (3.48, yy, 1.65), (0.32, 0.32, 3.3), "concrete_wall", "arcade")
# service window (closed shutter) where the night work order is left
box("SM_ServiceWindow_Frame", (-3.16, -12.8, 1.5), (0.10, 1.7, 1.25), "iron_dark", "arcade")
box("SM_ServiceWindow_Shutter", (-3.10, -12.8, 1.5), (0.02, 1.5, 1.05), "paint_green", "detail", collision=False)
box("SM_ServiceWindow_Ledge", (-3.0, -12.8, 1.02), (0.36, 1.7, 0.06), "brass_aged", "arcade")
box("SM_ServiceWindow_Lamp", (-3.1, -12.8, 2.35), (0.18, 0.30, 0.12), "emissive_warm", "detail", collision=False)
# street beyond the parapet (unreachable, visual only)
box("SM_Street", (9.0, -13.0, -0.30), (11.0, 22.0, 0.2), "asphalt_wet", "exterior", collision=False)
box("SM_StreetLamp_Pole", (8.5, -12.5, 2.9), (0.16, 0.16, 6.2), "iron_dark", "exterior", collision=False)

# ---------------------------------------------------------------- service landing behind Door_Basement_01
box("SM_Landing_Floor", (0, 11.35, -0.11), (2.6, 3.7, 0.22), "concrete_wet", "landing")
box("SM_Landing_Ceiling", (0, 11.47, 2.75), (2.6, 3.46, 0.2), "concrete_wall", "landing")
box("SM_Landing_Wall_W", (-1.42, 11.4, 1.35), (0.24, 3.6, 2.7), "concrete_wall", "landing")
box("SM_Landing_Wall_E", (1.42, 11.4, 1.35), (0.24, 3.6, 2.7), "concrete_wall", "landing")
box("SM_Landing_Wall_N", (0, 13.32, 1.35), (3.08, 0.24, 2.7), "concrete_wall", "landing")
box("SM_Landing_StairGate", (0, 12.9, 0.55), (2.4, 0.05, 1.1), "iron_dark", "landing",
    note="stair down is gated: end of current greybox (VS03 starts here)")

INTERACTABLES = [
    {"id": "Pickup_JobOrder_2147", "type": "pickup", "item": "job_order_2147",
     "center": [-2.86, -12.65, 1.056], "size": [0.21, 0.297, 0.008], "material": "paper_aged",
     "label": {"zh": "拿起工单", "en": "Take work order"},
     "document": "doc_job_order", "sound": "paper_pickup", "sets_flag": "has_job_order"},
    {"id": "Door_Entrance_01", "type": "door", "hinge": [-0.59, -9.55, 0.0], "leaf_size": [1.18, 0.06, 2.3],
     "closed_yaw_deg": 0.0, "open_yaw_deg": 95.0, "swing": "north", "material": "iron_dark",
     "requires_item": "job_order_2147", "lock_mode": "reject_once_then_release",
     "panel": [1.02, -9.70, 1.30], "previous_number": "21-46",
     "label_locked": {"zh": "刷工单", "en": "Present work order"}, "label_open": {"zh": "推门", "en": "Push door"},
     "msg_no_item": "msg_entrance_no_order", "msg_reject": "msg_entrance_reject", "msg_release": "msg_entrance_release",
     "release_delay_s": 1.4, "sets_flag_on_open": "entrance_open"},
    {"id": "Checkpoint_Lobby", "type": "checkpoint", "center": [0.0, -8.3, 1.2], "size": [3.0, 1.4, 2.4],
     "respawn": [0.0, -8.0, 0.0], "respawn_facing": [0.0, 1.0], "sets_flag": "cp_lobby"},
    {"id": "Pickup_AccessCard_21", "type": "pickup", "item": "access_card_21",
     "center": [-4.35, -0.955, 1.27], "size": [0.10, 0.04, 0.07], "material": "paper_aged",
     "label": {"zh": "从卡槽取出工号卡", "en": "Take staff card from slot"},
     "document": "doc_access_card", "sound": "card_slot", "sets_flag": "has_access_card",
     "on_pickup_event": "phone_ring_once", "pilot_light": [-4.35, -1.05, 1.38]},
    {"id": "Phone_Counter_01", "type": "phone", "center": [-1.9, -0.45, 1.14], "size": [0.24, 0.2, 0.10],
     "material": "rubber_black", "label": {"zh": "接听", "en": "Answer"},
     "ring_event": "phone_ring_once", "on_answer_msg": "msg_phone_dialtone",
     "relay_to": "Phone_Wall_01", "relay_delay_s": 2.5},
    {"id": "Phone_Wall_01", "type": "phone", "center": [-2.4, 9.42, 1.45], "size": [0.2, 0.1, 0.3],
     "material": "rubber_black", "label": {"zh": "接听", "en": "Answer"}, "on_answer_msg": "msg_phone_wall"},
    {"id": "Door_Basement_01", "type": "door", "hinge": [-0.6, 9.62, 0.0], "leaf_size": [1.2, 0.06, 2.15],
     "closed_yaw_deg": 0.0, "open_yaw_deg": 92.0, "swing": "north", "material": "paint_green",
     "requires_item": "access_card_21", "lock_mode": "item",
     "panel": [0.95, 9.48, 1.25],
     "label_locked": {"zh": "刷工号卡", "en": "Swipe staff card"}, "label_open": {"zh": "开门", "en": "Open door"},
     "msg_no_item": "msg_basement_no_card", "sets_flag_on_open": "basement_open"},
    {"id": "Checkpoint_ServiceDoor", "type": "checkpoint", "center": [0.0, 11.0, 1.2], "size": [2.2, 1.2, 2.4],
     "respawn": [0.0, 10.8, 0.0], "respawn_facing": [0.0, 1.0], "sets_flag": "cp_service"},
    {"id": "Anomaly_EmptyFrame_01", "type": "displacement_anomaly", "center": [6.40, 1.6, 1.95],
     "size": [0.07, 1.4, 1.7], "material": "brass_aged", "displace": [0.0, -0.08, 0.0],
     "seen_within_m": 4.5, "label": {"zh": "查看相框", "en": "Inspect frame"}, "document": "doc_empty_frame",
     "note": "DIRECTOR_BEAT_SHEET 关键演出01: moves 8 cm once, only after it was seen and is then out of view"},
    {"id": "Readable_Notice_01", "type": "readable", "center": [3.4, 9.44, 1.75], "size": [1.55, 0.03, 0.9],
     "material": "paper_aged", "label": {"zh": "阅读告示", "en": "Read notice"}, "document": "doc_notice"},
]

LIGHTS = [
    {"id": "L_ServiceWindow", "type": "point", "pos": [-2.75, -12.8, 2.25], "color": [1.0, 0.72, 0.45], "lumens": 900,
     "radius_m": 7.0, "shadows": True, "intent": "only warm source in the arcade; leads eye to work order"},
    {"id": "L_StreetLamp", "type": "spot", "pos": [8.4, -12.5, 5.9], "aim": [3.0, -12.5, 0.0],
     "color": [0.62, 0.74, 1.0], "lumens": 5000, "cone_deg": 55, "cone_deg_meaning": "full cone angle", "radius_m": 18.0, "shadows": True,
     "intent": "cold street spill across parapet; silhouettes columns"},
    {"id": "L_Hall_A", "type": "rect", "pos": [-0.8, -5.9, 3.98], "aim": [-0.8, -5.9, 0.0], "color": [1.0, 0.9, 0.78],
     "lumens": 900, "size_m": [1.05, 0.22], "radius_m": 10.0, "shadows": True},
    {"id": "L_Hall_C", "type": "rect", "pos": [-0.8, 0.7, 3.98], "aim": [-0.8, 0.7, 0.0], "color": [1.0, 0.9, 0.78],
     "lumens": 700, "size_m": [1.05, 0.22], "radius_m": 10.0, "shadows": True},
    {"id": "L_BasementDoor", "type": "point", "pos": [0.0, 9.1, 2.6], "color": [1.0, 0.86, 0.66], "lumens": 1600,
     "radius_m": 6.0, "shadows": True, "intent": "focal anchor: brightest navigation cue in the lobby"},
    {"id": "L_CardSlotPilot", "type": "point", "pos": [-4.35, -1.05, 1.38], "color": [1.0, 0.55, 0.2], "lumens": 35,
     "radius_m": 1.6, "shadows": False, "intent": "pilot lamp on the card slot (non-text hint)"},
    {"id": "L_Landing", "type": "point", "pos": [0.0, 12.2, 2.5], "color": [0.85, 0.9, 1.0], "lumens": 260,
     "radius_m": 4.0, "shadows": True},
]
ENVIRONMENT = {
    "skylight_intensity": 0.25, "skylight_color": [0.55, 0.62, 0.78],
    "fog_density": 0.012, "fog_color": [0.18, 0.21, 0.26],
    "exposure_bias": -1.0, "auto_exposure_min_ev100": -1.5, "auto_exposure_max_ev100": 2.0,
    "time_of_day": "pre-dawn, after rain (Act 0 precedes Act I '拂晓')",
}

AUDIO_EMITTERS = [
    {"id": "A_Rain_Arcade", "sound": "rain_loop", "pos": [3.6, -13.4, 2.0], "loop": True, "volume": 0.9, "radius_m": 22},
    {"id": "A_Rain_Lobby", "sound": "rain_loop", "pos": [0.0, -8.6, 3.0], "loop": True, "volume": 0.25, "radius_m": 9},
    {"id": "A_Hum_Cable", "sound": "hum_electrical", "pos": [2.2, 0.0, 4.0], "loop": True, "volume": 0.35, "radius_m": 9},
    {"id": "A_Clock_Desk", "sound": "clock_tick", "pos": [-2.5, -0.5, 1.3], "loop": True, "volume": 0.5, "radius_m": 5},
    {"id": "A_QueueChime", "sound": "queue_chime", "pos": [-3.6, 2.5, 2.6], "loop": False, "volume": 0.45,
     "radius_m": 30, "interval_s": [22, 38],
     "intent": "canon foreshadow '远处重复的电子叫号'; audible from the arcade through the entrance"},
]

DOCUMENTS = {
    "doc_job_order": {
        "title": {"zh": "工单 21-47", "en": "Work order 21-47"},
        "body": {"zh": "工单 21-47。夜间移交：R-Array 离线数据匣一件。进入后沿维修标线走，禁止恢复自动补发功能。接收地点：地面登记窗。",
                 "en": "Work order 21-47. Night handover: one R-Array offline data casket. Once inside, follow the maintenance line. Do not restore the automatic re-send function. Receiving point: ground-floor registration window."},
        "source": "docs/WORLD_BIBLE_AND_SCRIPT.md 第0幕 门外工单 (verbatim)"},
    "doc_notice": {
        "title": {"zh": "前台告示", "en": "Counter notice"},
        "body": {"zh": "未领取的照片保管三十日。如申请人要求销毁，请在背面签字。空白栏不视作同意。",
                 "en": "Unclaimed photographs are kept for thirty days. If the applicant requests destruction, sign on the back. A blank field is not consent."},
        "source": "docs/WORLD_BIBLE_AND_SCRIPT.md 第0幕 前台告示 (verbatim)"},
    "doc_access_card": {
        "title": {"zh": "工号卡", "en": "Staff card"},
        "body": {"zh": "临时复核员 21。", "en": "Temporary Reviewer 21."},
        "source": "GDD 主角 / 复核员21; no new canon"},
    "doc_empty_frame": {
        "title": {"zh": "空相框", "en": "Empty frame"},
        "body": {"zh": "框里没有照片。", "en": "There is no photograph in the frame."},
        "source": "scene_01 spec Frame_Empty_01; no new canon"},
}
MESSAGES = {
    "msg_entrance_no_order": {"zh": "门禁亮红灯。需要工单。", "en": "The reader blinks red. It wants a work order."},
    "msg_entrance_reject": {"zh": "门禁显示上一个号码：21-46。", "en": "The reader shows the previous number: 21-46."},
    "msg_entrance_release": {"zh": "锁舌咔哒一声松开了。", "en": "The latch clicks loose."},
    "msg_basement_no_card": {"zh": "读卡器没有反应。需要工号卡。", "en": "The card reader does nothing. It needs a staff card."},
    "msg_phone_dialtone": {"zh": "听筒里只有拨号音。", "en": "Only a dial tone."},
    "msg_phone_wall": {"zh": "没有人说话。", "en": "Nobody speaks."},
    "msg_checkpoint": {"zh": "已记录", "en": "Logged"},
    "ui_doc_close": {"zh": "[E] 放下", "en": "[E] Close"},
    "ui_current": {"zh": "当前：", "en": "Current: "},
    "msg_slice_end": {"zh": "灰盒段落结束（L0_B01 门厅）。楼梯门暂未开放。", "en": "End of greybox section (L0_B01 lobby). The stair gate is not built yet."},
}

FLOW = [
    {"id": "obj_find_order", "text": {"zh": "找到夜间工单", "en": "Find the night work order"}, "complete_on": "has_job_order"},
    {"id": "obj_enter", "text": {"zh": "进入回执局", "en": "Enter the Receipt Office"}, "complete_on": "cp_lobby"},
    {"id": "obj_card", "text": {"zh": "在前台找到工号卡", "en": "Find the staff card at the front counter"}, "complete_on": "has_access_card"},
    {"id": "obj_service_door", "text": {"zh": "打开地下维修门", "en": "Open the basement service door"}, "complete_on": "cp_service"},
    {"id": "obj_end", "text": {"zh": "（本段灰盒结束）", "en": "(End of greybox section)"}, "complete_on": ""},
]

# Scripted bot route used by the in-engine autopilot (-ConfessionAutoPlaytest) and the offline reachability check.
AUTOPILOT = [
    {"op": "goto", "to": [0.3, -14.4]},
    {"op": "goto", "to": [-2.15, -12.65]},
    {"op": "use", "target": "Pickup_JobOrder_2147", "expect_flag": "has_job_order"},
    {"op": "screenshot", "shot": "shot_arcade"},
    {"op": "goto", "to": [0.0, -10.9]},
    {"op": "use", "target": "Door_Entrance_01", "expect_flag": ""},
    {"op": "wait", "seconds": 2.2},
    {"op": "use", "target": "Door_Entrance_01", "expect_flag": "entrance_open"},
    {"op": "wait", "seconds": 1.6},
    {"op": "goto", "to": [0.0, -8.0], "expect_flag": "cp_lobby"},
    {"op": "screenshot", "shot": "shot_entrance"},
    {"op": "goto", "to": [-3.5, -2.2]},
    {"op": "use", "target": "Pickup_AccessCard_21", "expect_flag": "has_access_card"},
    {"op": "screenshot", "shot": "shot_counter"},
    {"op": "goto", "to": [0.0, -2.2]},
    {"op": "goto", "to": [0.0, 8.3]},
    {"op": "use", "target": "Door_Basement_01", "expect_flag": "basement_open"},
    {"op": "wait", "seconds": 1.6},
    {"op": "goto", "to": [0.15, 11.0], "expect_flag": "cp_service"},
    {"op": "screenshot", "shot": "shot_return"},
]

SHOTS = [
    {"id": "shot_arcade", "camera": [0.9, -16.4, 1.65], "aim": [-2.75, -12.65, 1.25],
     "intent": "service-window lamp is the only warm source; entrance visible at the end of the arcade"},
    {"id": "shot_entrance", "camera": [0.8, -8.6, 1.65], "aim": [0.0, 9.4, 1.4],
     "intent": "destination door visible on entry, access route (counter, left) readable but not obvious"},
    {"id": "shot_counter", "camera": [-2.4, -3.0, 1.65], "aim": [-4.35, -0.95, 1.3],
     "intent": "card-slot pilot lamp and desk clock readable"},
    {"id": "shot_return", "camera": [2.2, 4.8, 1.65], "aim": [6.4, 1.6, 1.9],
     "intent": "empty frame bay on the return pass"},
]


def build() -> dict:
    ids = [g["id"] for g in geometry] + [i["id"] for i in INTERACTABLES]
    assert len(ids) == len(set(ids)), "duplicate ids"
    for g in geometry:
        assert g["material"] in MATERIALS, g
        assert min(g["size"]) > 0, g
    return {
        "id": "L0_B01", "name": {"zh": "雨廊入口 / 回执局门厅", "en": "Rain Arcade / Receipt Office Lobby"},
        "schema": 1, "layout_version": "0.5.1", "units": "metres",
        "axes": "Blender: +X east, +Y north (toward Door_Basement_01), +Z up. UE: X=x*100, Y=-y*100, Z=z*100.",
        "canon_sources": ["docs/WORLD_BIBLE_AND_SCRIPT.md", "docs/SCENE_OUTLINE_24_BEATS.md#L0_B01",
                          "production/vertical_slice_plan.json#VS01-VS02", "docs/DIRECTOR_BEAT_SHEET.md"],
        "status": "GREYBOX_DATA - not art, not engine-verified",
        "fixes_vs_v04": FIXES,
        "player": {"start": [0.3, -16.2, 0.0], "facing": [0.0, 1.0], "eye_height_m": 1.65,
                   "capsule_radius_m": 0.35, "capsule_half_height_m": 0.92, "use_distance_m": 2.6},
        "materials": MATERIALS, "environment": ENVIRONMENT,
        "geometry": geometry, "interactables": INTERACTABLES, "lights": LIGHTS, "audio_emitters": AUDIO_EMITTERS,
        "documents": DOCUMENTS, "messages": MESSAGES, "flow": FLOW, "autopilot": AUTOPILOT, "shots": SHOTS,
    }


def main() -> int:
    text = json.dumps(build(), ensure_ascii=False, indent=1) + "\n"
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            print(f"STALE: {OUT.relative_to(ROOT)} differs from generator; run without --check")
            return 1
        print("layout json up to date")
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}: {len(geometry)} boxes, {len(INTERACTABLES)} interactables")
    return 0


if __name__ == "__main__":
    sys.exit(main())
