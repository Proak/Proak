"""L0_B01 greybox builder for Blender 5.2 (bpy module or `blender -b -P`).

Builds the whole L0_B01 greybox from the single source of truth
`ue58/Content/Confession/Data/L0_B01_layout.json` in a fresh scene, saves an
editable .blend, exports GLB + FBX, and renders every `shots` entry plus an
orthographic top-down plan with Cycles CPU.

    PY=<venv>/bin/python
    $PY blender/l0_b01_greybox.py                 # build + save + export + render all
    $PY blender/l0_b01_greybox.py --no-render     # build + save + export only
    $PY blender/l0_b01_greybox.py --shots shot_arcade,plan_top --samples 32
    blender -b -P blender/l0_b01_greybox.py -- --no-render

This is GREYBOX data only. Renders are Blender Cycles renders, NOT Unreal screenshots.

Conventions (all documented again in production/blender/L0_B01/REPORT.md):
  * Units: metres, +X east, +Y north, +Z up (layout JSON convention, Blender native).
  * Every box -> one mesh object named by its id, origin at the box centre
    (doors: origin at the hinge), rotation 0, scale 1; real dimensions are in the
    vertices. Mesh datablocks are shared where (size, material, pivot offset) repeat.
  * UVs: world-scaled box projection, 1 UV unit = 1 metre (greybox grid friendly).
  * Light units: Blender W = lumens / 683 for point, spot and rect(area) lights.
    683 lm/W is the constant Blender's own glTF add-on uses in its physical ('SPEC')
    lighting mode (io_scene_gltf2/blender/com/conversion.py PBR_WATTS_TO_LUMENS).
    Point/spot: the add-on maps cd = W/(4*pi)*683, i.e. lm = W*683 for an isotropic
    source; spot cone does not concentrate power (Blender and UE both treat spot
    lumens/W "as if a point light"). Area: W = lm/683 into the hemisphere.
  * Emissive materials: UE emissive value treated as cd/m^2 -> Blender emission
    strength = emissive / 683 (Cycles emission strength is radiance in W/m^2/sr).
  * Sky: environment.skylight_intensity treated as cd/m^2 of a uniform sky ->
    world background strength = intensity / 683, colour = skylight_color.
  * Film exposure: per shot, a crude emulation of UE histogram auto-exposure: a
    160x90 metering pre-render (exposure 0, linear EXR), luminance in cd/m^2 =
    Y_linear * 683, mean of log2 luminance between the 10th and 90th percentile,
    EV100 = log2(L * 100 / 12.5), clamped to [auto_exposure_min_ev100,
    auto_exposure_max_ev100], then Blender exposure (stops) =
    log2(683 / (1.2 * 2^EV100)) + exposure_bias  (UE: exposure = 1/(1.2*2^EV100)).
    It is an approximation, not a match of UE's tonemapper/eye adaptation.
  * Camera: 36 mm sensor, horizontal fit, 78 deg horizontal FOV (lens ~22.2 mm).
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import bpy  # noqa: E402  (bpy must be imported before bmesh/mathutils in the bpy wheel)
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "ue58" / "Content" / "Confession" / "Data" / "L0_B01_layout.json"
OUT = ROOT / "production" / "blender" / "L0_B01"

LUMENS_PER_WATT = 683.0
HFOV_DEG = 78.0
SENSOR_MM = 36.0
CAPTION = "BLENDER 5.2 GREYBOX RENDER — NOT AN UNREAL SCREENSHOT"
PLAN_CUT_Z = 2.0          # plan: hide everything whose bottom is above this (section cut)
GROUP_ORDER = ["shell", "arcade", "landing", "detail", "prop", "exterior", "collision"]


def log(*a):
    print("[l0_b01]", *a, flush=True)


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", default=str(LAYOUT))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--no-save", action="store_true")
    ap.add_argument("--shots", default="", help="comma list of shot ids (and/or plan_top); default all")
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--plan-samples", type=int, default=24)
    ap.add_argument("--res", default="1280x720")
    ap.add_argument("--exposure", type=float, default=None, help="override film exposure (stops)")
    return ap.parse_args(argv)


# ----------------------------------------------------------------------------- scene setup
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.name = "L0_B01"
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    sc.unit_settings.length_unit = "METERS"
    return sc


def get_collection(name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(col)
    return col


def set_props(obj, entry):
    """Copy simple layout fields as custom properties; full entry as JSON string."""
    obj["layout_json"] = json.dumps(entry, ensure_ascii=False)
    for k, v in entry.items():
        if isinstance(v, (bool, int, float, str)):
            obj["l_" + k] = v


# ----------------------------------------------------------------------------- materials
def make_material(name, spec):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:  # older builds
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    col = list(spec["color"]) + [1.0]
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Roughness"].default_value = spec.get("roughness", 0.5)
    bsdf.inputs["Metallic"].default_value = spec.get("metallic", 0.0)
    if spec.get("emissive"):
        bsdf.inputs["Emission Color"].default_value = col
        bsdf.inputs["Emission Strength"].default_value = spec["emissive"] / LUMENS_PER_WATT
        mat["ue_emissive"] = spec["emissive"]
    mat.diffuse_color = col  # viewport solid colour
    mat.roughness = spec.get("roughness", 0.5)
    mat.metallic = spec.get("metallic", 0.0)
    return mat


def make_flat_emit(name, color, strength):
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = list(color) + [1.0]
    em.inputs["Strength"].default_value = strength
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    mat.diffuse_color = list(color) + [1.0]
    return mat


# ----------------------------------------------------------------------------- meshes
def _uv_for(co, n):
    ax = max(range(3), key=lambda i: abs(n[i]))
    if ax == 2:   # floor / ceiling
        return (co.x, co.y) if n.z > 0 else (-co.x, co.y)
    if ax == 0:   # east / west faces
        return (co.y, co.z) if n.x > 0 else (-co.y, co.z)
    return (-co.x, co.z) if n.y > 0 else (co.x, co.z)  # north / south faces


def box_mesh(name, size, material, offset=(0.0, 0.0, 0.0)):
    """One mesh datablock per object (not shared: Blender 5.2's FBX exporter warned about
    material indices on shared meshes in a trial run). Real size baked into vertices."""
    me = bpy.data.meshes.new("ME_" + name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0] + offset[0], v.co.y * size[1] + offset[1], v.co.z * size[2] + offset[2]))
    bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    for f in bm.faces:
        for lp in f.loops:
            lp[uv].uv = _uv_for(lp.vert.co, f.normal)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    return me


def add_box(name, center, size, material, col, offset=(0.0, 0.0, 0.0), yaw_deg=0.0):
    obj = bpy.data.objects.new(name, box_mesh(name, size, material, offset))
    obj.location = Vector(center)
    obj.rotation_euler = (0.0, 0.0, math.radians(yaw_deg))
    col.objects.link(obj)
    return obj


# ----------------------------------------------------------------------------- build
def aim_rotation(obj, target):
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def build(layout):
    sc = reset_scene()
    mats = {k: make_material(k, v) for k, v in layout["materials"].items()}
    mat_trigger = make_flat_emit("helper_trigger", (0.1, 0.9, 0.5), 1.0)
    root = get_collection("L0_B01")
    cols = {g: get_collection(g, root) for g in GROUP_ORDER}
    col_int = get_collection("interactables", root)
    col_lights = get_collection("lights", root)
    col_cams = get_collection("cameras", root)
    col_labels = get_collection("plan_labels", root)

    stats = {"geometry": 0, "collision_blockers": 0, "no_collision": 0, "interactables": 0,
             "triggers": 0, "lights": 0, "cameras": 0}

    # --- geometry boxes
    for g in layout["geometry"]:
        assert g["kind"] == "box", g
        group = g["group"]
        col = cols.get(group) or get_collection(group, root)
        obj = add_box(g["id"], g["center"], g["size"], mats[g["material"]], col)
        set_props(obj, g)
        obj["ue_collision"] = bool(g.get("collision", True))
        if group == "collision":
            # invisible blocker: kept for UE/physics, never rendered
            obj.hide_render = True
            obj.display_type = "WIRE"
            obj["ue_role"] = "collision_blocker"
            stats["collision_blockers"] += 1
        if not g.get("collision", True):
            stats["no_collision"] += 1
        stats["geometry"] += 1

    # --- interactables
    for it in layout["interactables"]:
        t = it["type"]
        if t == "door":
            w, d, h = it["leaf_size"]
            # leaf extends +X from the hinge in the closed pose (yaw 0); opens toward +Y (north)
            obj = add_box(it["id"], it["hinge"], it["leaf_size"], mats[it["material"]], col_int,
                          offset=(w / 2.0, 0.0, h / 2.0), yaw_deg=it.get("closed_yaw_deg", 0.0))
            obj["ue_role"] = "door_leaf_pivot_at_hinge"
            if "panel" in it:
                e = bpy.data.objects.new(it["id"] + "_Panel", None)
                e.empty_display_type = "PLAIN_AXES"
                e.empty_display_size = 0.1
                e.location = Vector(it["panel"])
                col_int.objects.link(e)
                e["ue_role"] = "door_access_panel_marker"
        elif t == "checkpoint" or "material" not in it:
            obj = add_box(it["id"], it["center"], it["size"], mat_trigger, col_int)
            obj.hide_render = True
            obj.display_type = "WIRE"
            obj["ue_role"] = "trigger_volume"
            stats["triggers"] += 1
        else:
            obj = add_box(it["id"], it["center"], it["size"], mats[it["material"]], col_int)
            obj["ue_role"] = "interactable_" + t
        set_props(obj, it)
        stats["interactables"] += 1

    # --- lights
    for L in layout["lights"]:
        t = L["type"]
        if t == "point":
            ld = bpy.data.lights.new(L["id"], "POINT")
            ld.shadow_soft_size = 0.05
        elif t == "spot":
            ld = bpy.data.lights.new(L["id"], "SPOT")
            ld.spot_size = math.radians(L["cone_deg"])  # interpreted as FULL cone angle
            ld.spot_blend = 0.3
            ld.shadow_soft_size = 0.08
        elif t == "rect":
            ld = bpy.data.lights.new(L["id"], "AREA")
            ld.shape = "RECTANGLE"
            ld.size, ld.size_y = L["size_m"]
        else:
            raise ValueError(t)
        ld.energy = L["lumens"] / LUMENS_PER_WATT
        ld.color = L["color"]
        ld.use_shadow = bool(L.get("shadows", True))
        for attr, val in (("use_custom_distance", True), ("cutoff_distance", L.get("radius_m", 10.0))):
            if hasattr(ld, attr):
                setattr(ld, attr, val)  # EEVEE only; Cycles has no attenuation radius
        obj = bpy.data.objects.new(L["id"], ld)
        obj.location = Vector(L["pos"])
        if "aim" in L:
            aim_rotation(obj, L["aim"])
        col_lights.objects.link(obj)
        set_props(obj, L)
        obj["blender_watts"] = ld.energy
        stats["lights"] += 1

    # --- world (dim night sky after rain)
    env = layout["environment"]
    world = bpy.data.worlds.new("W_L0_B01_night")
    if world.node_tree is None:
        world.use_nodes = True
    bg = next((n for n in world.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg is None:
        bg = world.node_tree.nodes.new("ShaderNodeBackground")
        outn = next((n for n in world.node_tree.nodes if n.type == "OUTPUT_WORLD"), None) or \
            world.node_tree.nodes.new("ShaderNodeOutputWorld")
        world.node_tree.links.new(bg.outputs[0], outn.inputs["Surface"])
    bg.inputs["Color"].default_value = list(env["skylight_color"]) + [1.0]
    bg.inputs["Strength"].default_value = env["skylight_intensity"] / LUMENS_PER_WATT
    for k, v in env.items():
        if isinstance(v, (int, float, str)):
            world["env_" + k] = v
    world["fog_note"] = "fog_density/fog_color NOT rendered in Blender greybox"
    sc.world = world

    # --- shot cameras
    for s in layout["shots"]:
        cd = bpy.data.cameras.new("CAM_" + s["id"])
        cd.sensor_fit = "HORIZONTAL"
        cd.sensor_width = SENSOR_MM
        cd.angle_x = math.radians(HFOV_DEG)
        cd.clip_start = 0.05
        cd.clip_end = 200.0
        obj = bpy.data.objects.new(s["id"], cd)
        obj.location = Vector(s["camera"])
        aim_rotation(obj, s["aim"])
        col_cams.objects.link(obj)
        set_props(obj, s)
        stats["cameras"] += 1

    # --- plan camera (orthographic, top-down) and labels (render-hidden by default)
    xs, ys = [], []
    for g in layout["geometry"]:
        if g["group"] == "exterior":
            continue
        for sgn in (-1, 1):
            xs.append(g["center"][0] + sgn * g["size"][0] / 2)
            ys.append(g["center"][1] + sgn * g["size"][1] / 2)
    for L in layout["lights"]:  # keep every light marker (e.g. the street lamp) in frame
        xs.append(L["pos"][0] + 1.0)
        ys.append(L["pos"][1])
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    span_x, span_y = max(xs) - min(xs) + 3.0, max(ys) - min(ys) + 1.5
    cd = bpy.data.cameras.new("CAM_plan_top")
    cd.type = "ORTHO"
    cd.sensor_fit = "VERTICAL"
    cd.ortho_scale = span_y
    cd.clip_start = 0.1
    cd.clip_end = 100.0
    obj = bpy.data.objects.new("plan_top", cd)
    obj.location = (cx, cy, 40.0)
    col_cams.objects.link(obj)
    obj["plan_span_m"] = [span_x, span_y]
    obj["plan_cut_z"] = PLAN_CUT_Z

    lab_int = make_flat_emit("label_interactable", (1.0, 0.85, 0.2), 1.0)
    lab_light = make_flat_emit("label_light", (0.5, 0.85, 1.0), 1.0)
    lab_trig = make_flat_emit("label_trigger", (0.3, 1.0, 0.55), 1.0)

    def label(text, x, y, mat, size=0.24, dx=0.0, dy=0.0, align="CENTER"):
        cu = bpy.data.curves.new("LBL_" + text, "FONT")
        cu.body = text
        cu.size = size
        cu.align_x = align
        cu.align_y = "CENTER"
        o = bpy.data.objects.new("LBL_" + text, cu)
        o.location = (x + dx, y + dy, 6.0)
        o.data.materials.append(mat)
        col_labels.objects.link(o)
        return o

    # label offsets keep text over the (grey) floor instead of the (white) wall tops
    offsets = {"Pickup_JobOrder_2147": (0.3, 0.3, "LEFT"), "Anomaly_EmptyFrame_01": (-0.3, 0.0, "RIGHT"),
               "Phone_Wall_01": (0.0, -0.45, "CENTER"), "Readable_Notice_01": (0.0, -0.45, "CENTER"),
               "Door_Basement_01": (0.0, 0.5, "CENTER"), "Door_Entrance_01": (0.0, 0.45, "CENTER"),
               "L_ServiceWindow": (0.3, -0.3, "LEFT")}
    for it in layout["interactables"]:
        if it["type"] == "door":
            p = [it["hinge"][0] + it["leaf_size"][0] / 2, it["hinge"][1]]
        else:
            p = it["center"]
        m = lab_trig if it["type"] == "checkpoint" else lab_int
        dx, dy, al = offsets.get(it["id"], (0.0, 0.0 if it["type"] == "checkpoint" else 0.35, "CENTER"))
        label(it["id"], p[0], p[1], m, dx=dx, dy=dy, align=al)
    for L in layout["lights"]:
        dx, dy, al = offsets.get(L["id"], (0.0, -0.3, "CENTER"))
        label(L["id"], L["pos"][0], L["pos"][1], lab_light, size=0.2, dx=dx, dy=dy, align=al)
        me = bpy.data.meshes.new("LBLM_" + L["id"])
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=0.12)
        bm.to_mesh(me)
        bm.free()
        me.materials.append(lab_light)
        o = bpy.data.objects.new("LBLM_" + L["id"], me)
        o.location = (L["pos"][0], L["pos"][1], 6.0)
        col_labels.objects.link(o)
    for o in col_labels.objects:
        o.hide_render = True
    col_labels.hide_render = True
    sc["layout_version"] = layout.get("layout_version", "")
    sc["layout_status"] = layout.get("status", "")
    return sc, stats


# ----------------------------------------------------------------------------- render setup
def setup_render(sc, layout, samples, res, exposure):
    sc.render.engine = "CYCLES"
    cy = sc.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.max_bounces = 6
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 3
    cy.transmission_bounces = 2
    cy.transparent_max_bounces = 4
    cy.sample_clamp_indirect = 5.0
    denoise = False
    try:
        import _cycles
        denoise = bool(getattr(_cycles, "with_openimagedenoise", False))
    except Exception:
        pass
    cy.use_denoising = denoise
    if denoise:
        cy.denoiser = "OPENIMAGEDENOISE"
    sc.render.threads_mode = "FIXED"
    sc.render.threads = os.cpu_count() or 4
    w, h = (int(v) for v in res.lower().split("x"))
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = exposure
    sc.view_settings.gamma = 1.0
    im = sc.render.image_settings
    im.file_format = "PNG"
    im.color_mode = "RGB"
    im.color_depth = "8"
    im.compression = 90
    # caption burnt into the pixels via Blender's stamp (note only)
    r = sc.render
    for attr in dir(r):
        if attr.startswith("use_stamp_") and isinstance(getattr(r, attr), bool):
            try:
                setattr(r, attr, False)
            except Exception:
                pass
    r.use_stamp = True
    r.use_stamp_note = True
    r.stamp_font_size = 18
    r.stamp_foreground = (1.0, 1.0, 1.0, 1.0)
    r.stamp_background = (0.0, 0.0, 0.0, 0.7)
    return denoise


def meter_exposure(sc, cam, env, scratch):
    """Emulate UE histogram auto exposure for one camera. Returns (stops, info)."""
    import numpy as np
    r, cy, im = sc.render, sc.cycles, sc.render.image_settings
    saved = (r.resolution_x, r.resolution_y, cy.samples, cy.use_denoising, r.use_stamp,
             im.file_format, im.color_depth, r.filepath, sc.view_settings.exposure)
    r.resolution_x, r.resolution_y = 160, 90
    cy.samples = 16
    cy.use_denoising = False
    r.use_stamp = False
    im.file_format = "OPEN_EXR"
    im.color_depth = "32"
    sc.view_settings.exposure = 0.0
    sc.camera = cam
    path = Path(scratch) / ("_meter_%s.exr" % cam.name)
    r.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    img = bpy.data.images.load(str(path))
    px = np.array(img.pixels[:], dtype=np.float64).reshape(-1, 4)
    bpy.data.images.remove(img)
    path.unlink()
    (r.resolution_x, r.resolution_y, cy.samples, cy.use_denoising, r.use_stamp,
     im.file_format, im.color_depth, r.filepath, sc.view_settings.exposure) = saved
    im.color_mode = "RGB"
    nits = (0.2126 * px[:, 0] + 0.7152 * px[:, 1] + 0.0722 * px[:, 2]) * LUMENS_PER_WATT
    lg = np.log2(np.maximum(nits, 1e-4))
    lo, hi = np.percentile(lg, [10, 90])
    sel = lg[(lg >= lo) & (lg <= hi)]
    l_avg = float(2 ** sel.mean())
    ev_raw = math.log2(l_avg * 100.0 / 12.5)
    ev = min(max(ev_raw, env["auto_exposure_min_ev100"]), env["auto_exposure_max_ev100"])
    stops = math.log2(LUMENS_PER_WATT / (1.2 * 2 ** ev)) + env.get("exposure_bias", 0.0)
    return stops, {"metered_avg_cd_m2": round(l_avg, 4), "ev100_unclamped": round(ev_raw, 3),
                   "ev100_used": round(ev, 3), "blender_exposure_stops": round(stops, 3)}


def render_still(sc, cam, path, note):
    sc.camera = cam
    sc.render.stamp_note_text = note
    sc.render.filepath = str(path)
    t = time.time()
    bpy.ops.render.render(write_still=True)
    return time.time() - t


def prepare_plan(sc):
    """Mutates the scene for the plan render: section cut, flat white sky, labels on."""
    for o in sc.objects:
        if o.type == "LIGHT":
            o.hide_render = True
        if o.type == "MESH" and not o.name.startswith("LBLM_"):
            zmin = min((o.matrix_world @ Vector(c)).z for c in o.bound_box)
            if zmin > PLAN_CUT_Z:
                o.hide_render = True
    hl = make_flat_emit("plan_highlight_interactable", (1.0, 0.45, 0.05), 1.0)
    trig = bpy.data.materials["helper_trigger"]
    for o in bpy.data.collections["interactables"].objects:
        if o.type != "MESH":
            continue
        if o.get("ue_role") == "trigger_volume":
            o.hide_render = False
            mod = o.modifiers.new("plan_wire", "WIREFRAME")
            mod.thickness = 0.04
            o.active_material = trig
        else:
            o.material_slots[0].link = "OBJECT"
            o.material_slots[0].material = hl
    col = bpy.data.collections["plan_labels"]
    col.hide_render = False
    for o in col.objects:
        o.hide_render = False
    bg = next(n for n in sc.world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.6
    sc.view_settings.exposure = 0.0
    sc.view_settings.view_transform = "Standard"
    cam = bpy.data.objects["plan_top"]
    span_x, span_y = cam["plan_span_m"]
    h = 1800
    sc.render.resolution_y = h
    sc.render.resolution_x = int(round(h * span_x / span_y / 2) * 2)
    sc.cycles.use_adaptive_sampling = True


# ----------------------------------------------------------------------------- exports
def select_only(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]


def export_all(sc, out):
    res = {}
    labels = set(bpy.data.collections["plan_labels"].objects)
    helpers = {o for o in sc.objects if o.get("ue_role") in ("collision_blocker", "trigger_volume")}
    meshes = [o for o in sc.objects if o.type == "MESH" and o not in labels]
    # GLB: visual review file -> render meshes + lights + shot cameras (no helpers/labels/plan cam)
    glb_objs = [o for o in meshes if o not in helpers] + \
               [o for o in sc.objects if o.type == "LIGHT"] + \
               [o for o in bpy.data.collections["cameras"].objects if o.name != "plan_top"]
    glb = out / "L0_B01_greybox.glb"
    select_only(glb_objs)
    try:
        bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True,
                                  export_apply=True, export_yup=True, export_texcoords=True,
                                  export_normals=True, export_materials="EXPORT", export_cameras=True,
                                  export_lights=True, export_extras=True,
                                  export_import_convert_lighting_mode="SPEC")
        res["glb"] = {"status": "OK", "objects": len(glb_objs), "path": str(glb)}
    except Exception as e:  # pragma: no cover
        res["glb"] = {"status": "BLOCKED", "error": repr(e)}
    # FBX: UE static-mesh handoff -> all meshes incl. collision blockers + trigger volumes
    fbx = out / "L0_B01_greybox.fbx"
    fbx_settings = dict(use_selection=True, object_types={"MESH"}, global_scale=1.0,
                        apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS",
                        axis_forward="-Z", axis_up="Y", bake_space_transform=False,
                        use_mesh_modifiers=True, mesh_smooth_type="FACE", use_tspace=False,
                        use_triangles=False, use_custom_props=True, add_leaf_bones=False,
                        bake_anim=False, path_mode="AUTO", embed_textures=False)
    select_only(meshes)
    try:
        bpy.ops.export_scene.fbx(filepath=str(fbx), **fbx_settings)
        res["fbx"] = {"status": "OK", "objects": len(meshes), "path": str(fbx),
                      "settings": {k: (sorted(v) if isinstance(v, set) else v) for k, v in fbx_settings.items()}}
    except Exception as e:  # pragma: no cover
        res["fbx"] = {"status": "BLOCKED", "error": repr(e)}
    select_only([])
    return res


# ----------------------------------------------------------------------------- main
def main():
    args = parse_args()
    t0 = time.time()
    out = Path(args.out)
    (out / "renders").mkdir(parents=True, exist_ok=True)
    log("Blender", bpy.app.version_string, "| build hash", bpy.app.build_hash.decode()
        if isinstance(bpy.app.build_hash, bytes) else bpy.app.build_hash)
    layout = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    log("layout", layout["id"], layout.get("layout_version"), "geometry", len(layout["geometry"]),
        "interactables", len(layout["interactables"]), "lights", len(layout["lights"]),
        "shots", len(layout["shots"]))
    sc, stats = build(layout)
    log("built", stats)

    env = layout["environment"]
    # default saved in the .blend: exposure for the max_ev100 clamp (bright-adapted end)
    default_ev = math.log2(LUMENS_PER_WATT / (1.2 * 2 ** env["auto_exposure_max_ev100"]))
    denoise = setup_render(sc, layout, args.samples, args.res, default_ev)
    sc.camera = bpy.data.objects[layout["shots"][0]["id"]]
    log("default film exposure (stops)", round(default_ev, 3), "denoise(OIDN)", denoise)

    runlog = {"blender_version": bpy.app.version_string, "python": sys.version.split()[0],
              "layout_version": layout.get("layout_version"), "stats": stats,
              "default_exposure_stops": default_ev, "exposure_override": args.exposure,
              "denoise_oidn": denoise, "samples": args.samples,
              "resolution": args.res, "hfov_deg": HFOV_DEG,
              "lens_mm": bpy.data.cameras["CAM_" + layout["shots"][0]["id"]].lens,
              "lights_w": {L["id"]: L["lumens"] / LUMENS_PER_WATT for L in layout["lights"]},
              "timings_s": {}}
    runlog["timings_s"]["build"] = round(time.time() - t0, 2)

    if not args.no_save:
        blend = out / "L0_B01_greybox.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True, copy=False)
        log("saved", blend, blend.stat().st_size, "bytes")
    runlog["timings_s"]["save"] = round(time.time() - t0, 2)

    if not args.no_export:
        runlog["exports"] = export_all(sc, out)
        log("exports", json.dumps(runlog["exports"]))
    runlog["timings_s"]["export"] = round(time.time() - t0, 2)

    if not args.no_render:
        want = [s for s in args.shots.split(",") if s] or [s["id"] for s in layout["shots"]] + ["plan_top"]
        renders = {}
        for s in layout["shots"]:
            if s["id"] not in want:
                continue
            p = out / "renders" / (s["id"] + ".png")
            cam = bpy.data.objects[s["id"]]
            tm = time.time()
            if args.exposure is None:
                stops, meter = meter_exposure(sc, cam, env, out / "renders")
            else:
                stops, meter = args.exposure, {"blender_exposure_stops": args.exposure, "override": True}
            meter["seconds"] = round(time.time() - tm, 1)
            sc.view_settings.exposure = stops
            dt = render_still(sc, cam, p, "%s  |  %s  |  exp %+.2f EV  |  L0_B01 v%s" % (
                CAPTION, s["id"], stops, layout.get("layout_version")))
            renders[s["id"]] = {"seconds": round(dt, 1), "bytes": p.stat().st_size, "exposure": meter}
            log("rendered", s["id"], renders[s["id"]])
        if "plan_top" in want:
            prepare_plan(sc)
            sc.cycles.samples = args.plan_samples
            p = out / "renders" / "plan_top.png"
            dt = render_still(sc, bpy.data.objects["plan_top"], p, "%s  |  plan_top (ortho, cut z>%.1f m hidden)" % (
                CAPTION, PLAN_CUT_Z))
            renders["plan_top"] = {"seconds": round(dt, 1), "bytes": p.stat().st_size,
                                   "resolution": [sc.render.resolution_x, sc.render.resolution_y]}
            log("rendered plan_top", renders["plan_top"])
        runlog["renders"] = renders
    runlog["timings_s"]["total"] = round(time.time() - t0, 2)
    tag = "build_log.json" if not args.shots else "build_log_partial.json"
    (out / tag).write_text(json.dumps(runlog, indent=2, ensure_ascii=False), encoding="utf-8")
    log("done in", runlog["timings_s"]["total"], "s")


if __name__ == "__main__":
    main()
