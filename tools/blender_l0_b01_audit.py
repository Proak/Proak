"""Technical mesh audit for the L0_B01 Blender greybox (Blender 5.2 bpy module).

    $PY tools/blender_l0_b01_audit.py            # audits production/blender/L0_B01/L0_B01_greybox.blend
    blender -b -P tools/blender_l0_b01_audit.py

Writes production/blender/L0_B01/mesh_audit.json.

PASS/FAIL checks (technical only): object scale applied, dimensions/placement match the
layout JSON, every layout id present exactly once, UV layer present, material assigned,
non-manifold edges, flipped faces, zero-area faces.
Informational `layout_analysis` (NOT pass/fail, feeds LAYOUT_ISSUES.md): coplanar
same-facing faces (z-fight candidates), floating (unsupported) objects, door swing
interference, lights inside/near geometry, shot focal-point occlusion.
It does NOT judge art quality, UV unwrap quality, UE collision or performance.
Exit code: 0 if every PASS/FAIL check passes, 1 otherwise.
"""
import json
import math
import sys
from itertools import combinations
from pathlib import Path

import bpy  # noqa: E402  (bpy before bmesh/mathutils)
import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "production" / "blender" / "L0_B01"
BLEND = OUT / "L0_B01_greybox.blend"
LAYOUT = ROOT / "ue58" / "Content" / "Confession" / "Data" / "L0_B01_layout.json"
TOUCH_TOL = 0.0025   # m: closer than this counts as touching (supported)
COPLANAR_TOL = 1e-4  # m
DIM_TOL = 1e-4       # m


def aabb(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return ([min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)])


def gap(a, b):
    """Euclidean distance between two AABBs (0 when touching/overlapping)."""
    d = 0.0
    for i in range(3):
        g = max(a[0][i] - b[1][i], b[0][i] - a[1][i], 0.0)
        d += g * g
    return math.sqrt(d)


def overlap_vol(a, b):
    v = 1.0
    for i in range(3):
        v *= max(0.0, min(a[1][i], b[1][i]) - max(a[0][i], b[0][i]))
    return v


def inside(p, bb, eps=0.0):
    return all(bb[0][i] - eps < p[i] < bb[1][i] + eps for i in range(3))


def mesh_checks(o):
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.normal_update()
    centroid = sum((v.co for v in bm.verts), Vector()) / max(len(bm.verts), 1)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    zero = sum(1 for f in bm.faces if f.calc_area() < 1e-10)
    flipped = sum(1 for f in bm.faces if f.normal.dot(f.calc_center_median() - centroid) < 0)
    vol = bm.calc_volume(signed=True)
    tris = sum(len(f.verts) - 2 for f in bm.faces)
    bm.free()
    return dict(tris=tris, faces=len(me.polygons), verts=len(me.vertices), non_manifold_edges=nonman,
                boundary_edges=boundary, zero_area_faces=zero, flipped_faces=flipped,
                signed_volume_m3=round(vol, 6))


def expected_from_layout(layout):
    exp = {}
    for g in layout["geometry"]:
        exp[g["id"]] = {"loc": g["center"], "size": g["size"], "kind": "geometry"}
    for it in layout["interactables"]:
        if it["type"] == "door":
            w, d, h = it["leaf_size"]
            hx, hy, hz = it["hinge"]
            exp[it["id"]] = {"loc": it["hinge"], "size": it["leaf_size"], "kind": "door",
                             "aabb_center": [hx + w / 2, hy, hz + h / 2]}
        else:
            exp[it["id"]] = {"loc": it["center"], "size": it["size"], "kind": "interactable"}
    return exp


# ----------------------------------------------------------------------------- layout analysis
def coplanar_faces(boxes):
    out = []
    names = sorted(boxes)
    for a, b in combinations(names, 2):
        A, B = boxes[a], boxes[b]
        for k in range(3):
            o1, o2 = [i for i in range(3) if i != k]
            for side, sname in ((0, "min"), (1, "max")):
                if abs(A[side][k] - B[side][k]) > COPLANAR_TOL:
                    continue
                w1 = min(A[1][o1], B[1][o1]) - max(A[0][o1], B[0][o1])
                w2 = min(A[1][o2], B[1][o2]) - max(A[0][o2], B[0][o2])
                if w1 <= 1e-4 or w2 <= 1e-4:
                    continue
                # is the overlapping face patch buried inside a third visible box?
                c = [0.0, 0.0, 0.0]
                c[k] = A[side][k] + (0.002 if side == 1 else -0.002)
                c[o1] = (min(A[1][o1], B[1][o1]) + max(A[0][o1], B[0][o1])) / 2
                c[o2] = (min(A[1][o2], B[1][o2]) + max(A[0][o2], B[0][o2])) / 2
                buried = [n for n, bb in boxes.items() if n not in (a, b) and inside(c, bb)]
                out.append({"a": a, "b": b, "plane": "%s%s=%.4f" % ("xyz"[k], sname, A[side][k]),
                            "overlap_m2": round(w1 * w2, 5), "hidden_by": buried[:3]})
    return out


def floating(boxes, roots):
    names = list(boxes)
    adj = {n: set() for n in names}
    for a, b in combinations(names, 2):
        if gap(boxes[a], boxes[b]) <= TOUCH_TOL:
            adj[a].add(b)
            adj[b].add(a)
    seen = set()
    stack = [r for r in roots if r in boxes]
    seen.update(stack)
    while stack:
        n = stack.pop()
        for m in adj[n]:
            if m not in seen:
                seen.add(m)
                stack.append(m)
    unsupported = [n for n in names if n not in seen]
    comps, done = [], set()
    for n in unsupported:
        if n in done:
            continue
        comp, st = set([n]), [n]
        while st:
            x = st.pop()
            for m in adj[x]:
                if m not in comp:
                    comp.add(m)
                    st.append(m)
        done |= comp
        others = [m for m in names if m not in comp]
        best = min(((min(gap(boxes[c], boxes[m]) for c in comp), m) for m in others), default=(None, None))
        zmin = min(boxes[c][0][2] for c in comp)
        comps.append({"members": sorted(comp), "lowest_z_m": round(zmin, 4),
                      "gap_to_nearest_m": round(best[0], 4) if best[0] is not None else None,
                      "nearest": best[1]})
    return comps


def door_sweep(layout, boxes):
    res = []
    for it in layout["interactables"]:
        if it["type"] != "door":
            continue
        w, d, h = it["leaf_size"]
        hx, hy, hz = it["hinge"]
        y0, y1 = it.get("closed_yaw_deg", 0.0), it.get("open_yaw_deg", 90.0)
        hits = {}
        steps = 20
        for s in range(steps + 1):
            yaw = math.radians(y0 + (y1 - y0) * s / steps)
            c, sn = math.cos(yaw), math.sin(yaw)
            corners = [(hx + c * u - sn * v, hy + sn * u + c * v) for u in (0.0, w) for v in (-d / 2, d / 2)]
            axes = [(c, sn), (-sn, c), (1.0, 0.0), (0.0, 1.0)]
            for n, bb in boxes.items():
                if n == it["id"]:
                    continue
                if bb[1][2] <= hz + 1e-4 or bb[0][2] >= hz + h - 1e-4:
                    continue
                rect = [(bb[0][0], bb[0][1]), (bb[1][0], bb[0][1]), (bb[0][0], bb[1][1]), (bb[1][0], bb[1][1])]
                pen = float("inf")
                for ax in axes:
                    p1 = [ax[0] * x + ax[1] * y for x, y in corners]
                    p2 = [ax[0] * x + ax[1] * y for x, y in rect]
                    ov = min(max(p1), max(p2)) - max(min(p1), min(p2))
                    pen = min(pen, ov)
                if pen > 1e-4:
                    e = hits.setdefault(n, {"max_penetration_m": 0.0, "yaw_deg": []})
                    e["max_penetration_m"] = round(max(e["max_penetration_m"], pen), 4)
                    e["yaw_deg"].append(round(math.degrees(yaw), 1))
        for e in hits.values():
            e["yaw_range_deg"] = [min(e["yaw_deg"]), max(e["yaw_deg"])]
            del e["yaw_deg"]
        res.append({"door": it["id"], "closed_yaw": y0, "open_yaw": y1, "interference": hits})
    return res


def light_checks(layout, boxes):
    out = []
    for L in layout["lights"]:
        p = L["pos"]
        ins = [n for n, bb in boxes.items() if inside(p, bb)]
        near = sorted(((gap((p, p), bb), n) for n, bb in boxes.items()), key=lambda t: t[0])[:2]
        out.append({"light": L["id"], "inside": ins,
                    "nearest": [{"object": n, "distance_m": round(dd, 4)} for dd, n in near]})
    return out


def shot_checks(layout, sc):
    dg = bpy.context.evaluated_depsgraph_get()
    out = []
    for s in layout["shots"]:
        cam, aim = Vector(s["camera"]), Vector(s["aim"])
        d = aim - cam
        dist = d.length
        hit, loc, nrm, idx, ob, mat = sc.ray_cast(dg, cam, d.normalized(), distance=dist + 2.0)
        r = {"shot": s["id"], "aim_distance_m": round(dist, 3)}
        if hit:
            r["first_hit"] = ob.name
            r["first_hit_distance_m"] = round((loc - cam).length, 3)
            r["aim_occluded"] = (loc - cam).length < dist - 0.15
        else:
            r["first_hit"] = None
            r["aim_occluded"] = False
        out.append(r)
    return out


# ----------------------------------------------------------------------------- export checks
def fbx_header(path):
    try:
        from io_scene_fbx import parse_fbx
    except Exception as e:  # pragma: no cover
        return {"status": "BLOCKED", "error": repr(e)}
    root, version = parse_fbx.parse(str(path))

    def find(elem, name):
        return [e for e in elem.elems if e.id == name.encode()]

    info = {"status": "OK", "fbx_version": version}
    gs = find(root, "GlobalSettings")
    if gs:
        for p70 in find(gs[0], "Properties70"):
            for p in p70.elems:
                key = p.props[0].decode()
                if key in ("UnitScaleFactor", "OriginalUnitScaleFactor", "UpAxis", "UpAxisSign",
                           "FrontAxis", "FrontAxisSign", "CoordAxis", "CoordAxisSign"):
                    info[key] = p.props[4]
    objs = find(root, "Objects")[0]
    models = [e for e in objs.elems if e.id == b"Model"]
    geoms = [e for e in objs.elems if e.id == b"Geometry"]
    info["models"] = len(models)
    info["geometries"] = len(geoms)
    # one sample: SM_Lobby_Floor model scaling + its geometry extents in file units
    for m in models:
        nm = m.props[1].split(b"\x00")[0].decode()
        if nm == "SM_Lobby_Floor":
            for p70 in find(m, "Properties70"):
                for p in p70.elems:
                    if p.props[0] in (b"Lcl Scaling", b"Lcl Translation", b"Lcl Rotation"):
                        info["SM_Lobby_Floor_" + p.props[0].decode().replace(" ", "_")] = \
                            [round(float(x), 5) for x in p.props[4:7]]
    for g in geoms:
        nm = g.props[1].split(b"\x00")[0].decode()
        if nm == "ME_SM_Lobby_Floor":
            v = find(g, "Vertices")[0].props[0]
            xs, ys, zs = v[0::3], v[1::3], v[2::3]
            info["ME_SM_Lobby_Floor_extent_file_units"] = [round(max(a) - min(a), 5) for a in (xs, ys, zs)]
    return info


def reimport(kind, path):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    try:
        if kind == "fbx":
            bpy.ops.import_scene.fbx(filepath=str(path))
        else:
            bpy.ops.import_scene.gltf(filepath=str(path))
    except Exception as e:
        return {"status": "BLOCKED", "error": repr(e)}
    sc = bpy.context.scene
    r = {"status": "OK", "meshes": sum(1 for o in sc.objects if o.type == "MESH"),
         "lights": sum(1 for o in sc.objects if o.type == "LIGHT"),
         "cameras": sum(1 for o in sc.objects if o.type == "CAMERA"),
         "scene_unit_scale": sc.unit_settings.scale_length}
    f = bpy.data.objects.get("SM_Lobby_Floor")
    if f:
        bb = aabb(f)
        r["SM_Lobby_Floor_world_size_m"] = [round(bb[1][i] - bb[0][i], 4) for i in range(3)]
        r["SM_Lobby_Floor_world_center"] = [round((bb[1][i] + bb[0][i]) / 2, 4) for i in range(3)]
        r["SM_Lobby_Floor_object_scale"] = [round(x, 5) for x in f.scale]
    return r


# ----------------------------------------------------------------------------- main
def main():
    layout = json.loads(LAYOUT.read_text(encoding="utf-8"))
    bpy.ops.wm.open_mainfile(filepath=str(BLEND))
    sc = bpy.context.scene
    exp = expected_from_layout(layout)
    label_objs = set(bpy.data.collections["plan_labels"].all_objects) if "plan_labels" in bpy.data.collections else set()
    meshes = [o for o in sc.objects if o.type == "MESH" and o not in label_objs]

    items, fails = [], {k: [] for k in ("scale_applied", "dims_match_layout", "location_match_layout",
                                         "uv_layer_present", "material_assigned", "non_manifold_edges",
                                         "flipped_faces", "zero_area_faces")}
    for o in sorted(meshes, key=lambda x: x.name):
        mc = mesh_checks(o)
        e = exp.get(o.name)
        bb = aabb(o)
        size = [bb[1][i] - bb[0][i] for i in range(3)]
        dims_ok = e is not None and all(abs(size[i] - e["size"][i]) < DIM_TOL for i in range(3))
        loc_ok = e is not None and all(abs(o.location[i] - e["loc"][i]) < DIM_TOL for i in range(3))
        scale_ok = all(abs(s - 1.0) < 1e-6 for s in o.scale)
        uv_ok = len(o.data.uv_layers) > 0
        mat_ok = len(o.material_slots) > 0 and all(s.material for s in o.material_slots)
        it = {"name": o.name, "collection": o.users_collection[0].name if o.users_collection else None,
              "role": o.get("ue_role", "render_mesh"), "render_visible": not o.hide_render,
              "triangles": mc["tris"], "dimensions_m": [round(x, 5) for x in o.dimensions],
              "object_scale": [round(x, 6) for x in o.scale], "scale_applied": scale_ok,
              "dims_match_layout": dims_ok, "location_match_layout": loc_ok,
              "uv_layers": [u.name for u in o.data.uv_layers], "uv_layer_present": uv_ok,
              "material": o.material_slots[0].material.name if mat_ok else None,
              "non_manifold_edges": mc["non_manifold_edges"], "boundary_edges": mc["boundary_edges"],
              "flipped_faces": mc["flipped_faces"], "zero_area_faces": mc["zero_area_faces"],
              "signed_volume_m3": mc["signed_volume_m3"]}
        items.append(it)
        for k, ok in (("scale_applied", scale_ok), ("dims_match_layout", dims_ok),
                      ("location_match_layout", loc_ok), ("uv_layer_present", uv_ok),
                      ("material_assigned", mat_ok)):
            if not ok:
                fails[k].append(o.name)
        for k in ("non_manifold_edges", "flipped_faces", "zero_area_faces"):
            if mc[k]:
                fails[k].append(o.name)

    layout_ids = list(exp)
    names = [o.name for o in meshes]
    missing = sorted(set(layout_ids) - set(names))
    extra = sorted(set(names) - set(layout_ids))
    dup = sorted({n for n in layout_ids if layout_ids.count(n) > 1})

    checks = {k: {"result": "PASS" if not v else "FAIL", "failing_objects": v} for k, v in fails.items()}
    checks["layout_ids_one_to_one"] = {"result": "PASS" if not (missing or extra or dup) else "FAIL",
                                       "missing": missing, "extra": extra, "duplicate_ids_in_layout": dup}
    tot = {"mesh_objects": len(items),
           "render_visible_meshes": sum(1 for i in items if i["render_visible"]),
           "render_hidden_helpers": sum(1 for i in items if not i["render_visible"]),
           "triangles_total": sum(i["triangles"] for i in items),
           "triangles_render_visible": sum(i["triangles"] for i in items if i["render_visible"]),
           "non_manifold_edges_total": sum(i["non_manifold_edges"] for i in items),
           "flipped_faces_total": sum(i["flipped_faces"] for i in items),
           "zero_area_faces_total": sum(i["zero_area_faces"] for i in items),
           "objects_without_uv": len(fails["uv_layer_present"]),
           "objects_scale_not_applied": len(fails["scale_applied"]),
           "materials": len(bpy.data.materials), "lights": sum(1 for o in sc.objects if o.type == "LIGHT"),
           "cameras": sum(1 for o in sc.objects if o.type == "CAMERA"),
           "plan_label_objects_excluded": len(label_objs)}

    # ---- informational layout analysis on render-visible meshes (doors in closed pose)
    vis = {o.name: aabb(o) for o in meshes if not o.hide_render}
    roots = [n for n in vis if "Floor" in n or n == "SM_Street"]
    for o in meshes:  # helpers must not occlude the focal-point ray casts
        if o.hide_render:
            o.hide_viewport = True
    analysis = {"note": "informational, not part of PASS/FAIL; AABB based (all boxes axis-aligned in closed pose)",
                "coplanar_same_facing_faces": coplanar_faces(vis),
                "floating_components": floating(vis, roots),
                "door_swing_interference": door_sweep(layout, vis),
                "lights": light_checks(layout, vis),
                "shots": shot_checks(layout, sc)}

    blend_info = {"path": str(BLEND.relative_to(ROOT)), "bytes": BLEND.stat().st_size,
                  "blender_version": bpy.app.version_string}

    # ---- export checks (fresh scenes)
    exports = {}
    fbx, glb = OUT / "L0_B01_greybox.fbx", OUT / "L0_B01_greybox.glb"
    if fbx.exists():
        exports["fbx_file"] = {"bytes": fbx.stat().st_size, "header": fbx_header(fbx)}
        exports["fbx_reimport_blender"] = reimport("fbx", fbx)
    else:
        exports["fbx_file"] = {"status": "MISSING"}
    if glb.exists():
        exports["glb_file"] = {"bytes": glb.stat().st_size}
        exports["glb_reimport_blender"] = reimport("glb", glb)
    else:
        exports["glb_file"] = {"status": "MISSING"}

    passed = all(c["result"] == "PASS" for c in checks.values())
    report = {"kind": "BLENDER_REAL_RUN", "tool": "tools/blender_l0_b01_audit.py", "blend": blend_info,
              "layout": str(LAYOUT.relative_to(ROOT)), "layout_version": layout.get("layout_version"),
              "overall": "PASS" if passed else "FAIL", "checks": checks, "totals": tot,
              "exports": exports, "layout_analysis": analysis, "objects": items,
              "scope_note": "Technical geometry audit only. Says nothing about art quality, UV unwrap "
                            "quality, UE import, UE collision or runtime performance."}
    out = OUT / "mesh_audit.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"overall": report["overall"], "totals": tot,
                      "checks": {k: v["result"] for k, v in checks.items()}, "report": str(out)}, indent=1))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
