#!/usr/bin/env python3
"""Offline geometric verification of a greybox layout (no engine).

Checks, using the same JSON the UE runtime builds from:
  1. player start is clear for the capsule
  2. every autopilot 'goto' segment is collision-free for the capsule (doors closed until opened in-route)
  3. every 'use' target is within use distance from where the bot stands, with clear line of sight
  4. checkpoint 'goto' points actually overlap their checkpoint volumes
  5. grid flood-fill: every required interactable stays reachable at every flow stage (soft-lock check)
  6. door clear width with the leaf open >= capsule diameter + margin

This is an approximation (axis-aligned boxes, 2D capsule footprint, AABB of the open leaf).
It does NOT replace an in-engine run (-ConfessionAutoPlaytest), it catches data errors before one.

usage: python3 tools/layout_reachability.py [layout.json] [--png out.png] [--json out.json]
exit code 0 = all checks pass, 1 = failures
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "ue58" / "Content" / "Confession" / "Data" / "L0_B01_layout.json"

CAPSULE_TOP = 1.84
STEP = 0.40  # MaxStepHeight 40 cm: boxes whose top is below this are walkable
DOOR_CLEAR_MIN = 1.13  # production/scene_specs/scene_01_entrance.yaml human_scale.door_clear_width_cm=115 (2 cm tolerance)


def aabb(center, size):
    return [center[i] - size[i] / 2 for i in range(3)], [center[i] + size[i] / 2 for i in range(3)]


def door_leaf_aabb(d, open_):
    hx, hy, _ = d["hinge"]
    w, t, h = d["leaf_size"]
    yaw = math.radians(d["open_yaw_deg"] if open_ else d["closed_yaw_deg"])
    # leaf extends from hinge along (cos, sin); thickness across
    ex, ey = math.cos(yaw), math.sin(yaw)
    nx, ny = -ey, ex
    pts = []
    for a in (0.0, w):
        for b in (-t / 2, t / 2):
            pts.append((hx + ex * a + nx * b, hy + ey * a + ny * b))
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return [min(xs), min(ys), 0.0], [max(xs), max(ys), h]


class World:
    def __init__(self, layout):
        self.L = layout
        self.static = []  # (id, min, max)
        for g in layout["geometry"]:
            if not g.get("collision", True):
                continue
            mn, mx = aabb(g["center"], g["size"])
            self.static.append((g["id"], mn, mx))
        self.inter = {i["id"]: i for i in layout["interactables"]}
        for i in layout["interactables"]:
            if i["type"] in ("pickup", "readable", "phone", "displacement_anomaly"):
                mn, mx = aabb(i["center"], i["size"])
                self.static.append((i["id"], mn, mx))
            if i["type"] == "door" and "panel" in i:
                p = i["panel"]
                self.static.append((i["id"] + ".panel", [p[0] - .06, p[1] - .02, p[2] - .09], [p[0] + .06, p[1] + .02, p[2] + .09]))
        self.open_doors: set[str] = set()
        self.taken: set[str] = set()

    def boxes(self):
        for b in self.static:
            if b[0] in self.taken:
                continue
            yield b
        for i in self.inter.values():
            if i["type"] == "door":
                mn, mx = door_leaf_aabb(i, i["id"] in self.open_doors)
                yield (i["id"], mn, mx)

    def blockers2d(self):
        out = []
        for bid, mn, mx in self.boxes():
            if mx[2] <= STEP or mn[2] >= CAPSULE_TOP:
                continue
            out.append((bid, mn[0], mn[1], mx[0], mx[1]))
        return out

    def circle_hits(self, x, y, r):
        hits = []
        for bid, x0, y0, x1, y1 in self.blockers2d():
            cx, cy = min(max(x, x0), x1), min(max(y, y0), y1)
            if (cx - x) ** 2 + (cy - y) ** 2 < r * r - 1e-9:
                hits.append(bid)
        return hits

    def floor_under(self, x, y):
        for g in self.L["geometry"]:
            if g["group"] in ("shell", "arcade", "landing") and g["center"][2] < 0 and g.get("collision", True):
                mn, mx = aabb(g["center"], g["size"])
                if mn[0] <= x <= mx[0] and mn[1] <= y <= mx[1]:
                    return True
        return False

    def ray_blocked(self, a, b, ignore):
        for bid, mn, mx in self.boxes():
            if bid in ignore or bid.startswith(tuple(ignore)):
                continue
            t0, t1 = 0.0, 1.0
            ok = True
            for k in range(3):
                d = b[k] - a[k]
                if abs(d) < 1e-12:
                    if a[k] < mn[k] or a[k] > mx[k]:
                        ok = False
                        break
                    continue
                ta, tb = (mn[k] - a[k]) / d, (mx[k] - a[k]) / d
                if ta > tb:
                    ta, tb = tb, ta
                t0, t1 = max(t0, ta), min(t1, tb)
                if t0 > t1:
                    ok = False
                    break
            if ok and t1 > 1e-6 and t0 < 0.999:
                return bid
        return None


def aim_point(i):
    if i["type"] == "door":
        mn, mx = door_leaf_aabb(i, False)
        return [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2, (mn[2] + mx[2]) / 2]
    return list(i["center"])


def flood(world, start, r, res=0.05):
    xs = [b[1] for b in world.blockers2d()] + [b[3] for b in world.blockers2d()]
    ys = [b[2] for b in world.blockers2d()] + [b[4] for b in world.blockers2d()]
    x0, x1, y0, y1 = min(xs) - 1, max(xs) + 1, min(ys) - 1, max(ys) + 1
    nx, ny = int((x1 - x0) / res) + 1, int((y1 - y0) / res) + 1
    blk = world.blockers2d()
    free = bytearray(nx * ny)
    for j in range(ny):
        y = y0 + j * res
        for i in range(nx):
            x = x0 + i * res
            if not world.floor_under(x, y):
                continue
            hit = False
            for _, bx0, by0, bx1, by1 in blk:
                cx, cy = min(max(x, bx0), bx1), min(max(y, by0), by1)
                if (cx - x) ** 2 + (cy - y) ** 2 < r * r:
                    hit = True
                    break
            if not hit:
                free[j * nx + i] = 1
    si, sj = int(round((start[0] - x0) / res)), int(round((start[1] - y0) / res))
    seen = bytearray(nx * ny)
    if not free[sj * nx + si]:
        return None
    q = deque([(si, sj)])
    seen[sj * nx + si] = 1
    while q:
        i, j = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < nx and 0 <= b < ny and free[b * nx + a] and not seen[b * nx + a]:
                seen[b * nx + a] = 1
                q.append((a, b))
    return dict(seen=seen, free=free, x0=x0, y0=y0, nx=nx, ny=ny, res=res)


def reachable_within(fl, p, radius):
    """Is any reached grid cell within `radius` (horizontal) of p?"""
    res = fl["res"]
    ci, cj = int((p[0] - fl["x0"]) / res), int((p[1] - fl["y0"]) / res)
    k = int(radius / res) + 1
    for j in range(max(0, cj - k), min(fl["ny"], cj + k + 1)):
        for i in range(max(0, ci - k), min(fl["nx"], ci + k + 1)):
            if fl["seen"][j * fl["nx"] + i]:
                x, y = fl["x0"] + i * res, fl["y0"] + j * res
                if (x - p[0]) ** 2 + (y - p[1]) ** 2 <= radius * radius:
                    return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("layout", nargs="?", default=str(DEFAULT))
    ap.add_argument("--png", default=str(ROOT / "production" / "qa" / "L0_B01_reachability.png"))
    ap.add_argument("--json", default=str(ROOT / "production" / "qa" / "L0_B01_reachability.json"))
    args = ap.parse_args()
    L = json.loads(Path(args.layout).read_text(encoding="utf-8"))
    P = L["player"]
    r = P["capsule_radius_m"]
    eye = P["eye_height_m"]
    use = P["use_distance_m"]
    W = World(L)
    checks, fails = [], []

    def record(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            fails.append(f"{name}: {detail}")

    pos = list(P["start"][:2])
    hits = W.circle_hits(pos[0], pos[1], r)
    record("start_clear", not hits and W.floor_under(*pos), f"start {pos} hits {hits}")
    path = [tuple(pos)]
    flags: set[str] = set()
    items: set[str] = set()

    for n, op in enumerate(L["autopilot"]):
        kind = op["op"]
        if kind == "goto":
            tx, ty = op["to"]
            dist = math.hypot(tx - pos[0], ty - pos[1])
            steps = max(1, int(dist / 0.02))
            bad = None
            for s in range(steps + 1):
                x = pos[0] + (tx - pos[0]) * s / steps
                y = pos[1] + (ty - pos[1]) * s / steps
                h = W.circle_hits(x, y, r)
                if h or not W.floor_under(x, y):
                    bad = (round(x, 3), round(y, 3), h or ["no floor"])
                    break
            record(f"op{n}_goto_{tx}_{ty}", bad is None, f"blocked at {bad}" if bad else f"{dist:.2f} m clear")
            pos = [tx, ty]
            path.append((tx, ty))
            for i in W.inter.values():
                if i["type"] == "checkpoint":
                    mn, mx = aabb(i["center"], i["size"])
                    cx, cy = min(max(tx, mn[0]), mx[0]), min(max(ty, mn[1]), mx[1])
                    if (cx - tx) ** 2 + (cy - ty) ** 2 <= r * r:
                        flags.add(i["sets_flag"])
            if op.get("expect_flag"):
                record(f"op{n}_flag_{op['expect_flag']}", op["expect_flag"] in flags,
                       "checkpoint volume overlapped" if op["expect_flag"] in flags else "standing point misses volume")
        elif kind == "use":
            i = W.inter[op["target"]]
            ap_ = aim_point(i)
            e = [pos[0], pos[1], eye]
            d = math.dist(e, ap_)
            record(f"op{n}_use_{i['id']}_distance", d <= use, f"{d:.2f} m (limit {use})")
            blocker = W.ray_blocked(e, ap_, {i["id"]})
            record(f"op{n}_use_{i['id']}_line_of_sight", blocker is None, f"blocked by {blocker}" if blocker else "clear")
            if i["type"] == "pickup":
                items.add(i["item"])
                flags.add(i.get("sets_flag", ""))
                W.taken.add(i["id"])
            if i["type"] == "door":
                need = i.get("requires_item", "")
                if need and need not in items:
                    record(f"op{n}_door_item", False, f"{need} not held")
                if i.get("lock_mode") == "reject_once_then_release":
                    if i["id"] + ".released" in flags:
                        W.open_doors.add(i["id"])
                        flags.add(i.get("sets_flag_on_open", ""))
                    else:
                        flags.add(i["id"] + ".released")
                else:
                    W.open_doors.add(i["id"])
                    flags.add(i.get("sets_flag_on_open", ""))
            if op.get("expect_flag"):
                record(f"op{n}_flag_{op['expect_flag']}", op["expect_flag"] in flags, "")

    # door clear width with leaf open, and the closed leaf must fit its opening
    def free_run(world, hx, hy, w):
        run, best = 0.0, 0.0
        for k in range(-80, int(w * 100) + 80):
            if not world.circle_hits(hx + k / 100.0, hy, 0.001):
                run += 0.01
                best = max(best, run)
            else:
                run = 0.0
        return best
    for i in W.inter.values():
        if i["type"] != "door":
            continue
        hx, hy, _ = i["hinge"]
        w = i["leaf_size"][0]
        W_open = World(L)
        W_open.open_doors = set(W.inter)
        clear = free_run(W_open, hx, hy, w)
        record(f"door_clear_width_{i['id']}", clear >= DOOR_CLEAR_MIN, f"{clear:.2f} m free with leaf open (need {DOOR_CLEAR_MIN:.2f})")
        W_none = World(L)
        W_none.inter = {k: v for k, v in W.inter.items() if v["type"] != "door"}
        opening = free_run(W_none, hx, hy, w)
        record(f"door_leaf_fits_opening_{i['id']}", w <= opening + 0.02, f"leaf {w:.2f} m, opening {opening:.2f} m")

    # soft-lock flood fill with all critical doors open (end state) and closed (start state)
    W_end = World(L)
    W_end.open_doors = {i for i, v in W.inter.items() if v["type"] == "door"}
    fl = flood(W_end, P["start"], r)
    record("flood_start_cell_free", fl is not None, "")
    if fl:
        for i in W.inter.values():
            if i["type"] in ("pickup", "door", "phone", "readable"):
                ok = reachable_within(fl, aim_point(i), use - 0.3)
                record(f"reachable_{i['id']}", ok, "a reachable cell lies within use distance" if ok else "unreachable")
            if i["type"] == "checkpoint":
                mn, mx = aabb(i["center"], i["size"])
                ok = reachable_within(fl, [(mn[0] + mx[0]) / 2, (mn[1] + mx[1]) / 2], max(mx[0] - mn[0], mx[1] - mn[1]) / 2)
                record(f"reachable_{i['id']}", ok, "")
    W_start = World(L)
    fl0 = flood(W_start, P["start"], r)
    if fl0:
        # with doors closed the player must NOT be able to skip into the lobby
        lobby_pt = [0.0, -5.0]
        record("closed_entrance_blocks_lobby", not reachable_within(fl0, lobby_pt, 0.3), "")
        record("job_order_reachable_from_start", reachable_within(fl0, aim_point(W.inter["Pickup_JobOrder_2147"]), use - 0.3), "")

    report = {"kind": "OFFLINE_GEOMETRY_CHECK_NOT_ENGINE", "layout": f"{L['id']} v{L['layout_version']}",
              "capsule_radius_m": r, "checks_total": len(checks), "failures": fails, "result": "PASS" if not fails else "FAIL",
              "checks": checks}
    Path(args.json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.json).write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    try:
        from PIL import Image, ImageDraw
        S = 40
        xs = [b[1] for b in W_end.blockers2d()] + [b[3] for b in W_end.blockers2d()]
        ys = [b[2] for b in W_end.blockers2d()] + [b[4] for b in W_end.blockers2d()]
        bx0, bx1, by0, by1 = min(xs) - 0.5, max(xs) + 0.5, min(ys) - 0.5, max(ys) + 0.5
        im = Image.new("RGB", (int((bx1 - bx0) * S), int((by1 - by0) * S) + 40), (22, 24, 26))
        dr = ImageDraw.Draw(im)
        X = lambda x: (x - bx0) * S
        Y = lambda y: (by1 - y) * S + 40
        if fl:
            for j in range(0, fl["ny"], 2):
                for i2 in range(0, fl["nx"], 2):
                    if fl["seen"][j * fl["nx"] + i2]:
                        x, y = fl["x0"] + i2 * fl["res"], fl["y0"] + j * fl["res"]
                        dr.point((X(x), Y(y)), fill=(40, 70, 52))
        for bid, x0, y0, x1, y1 in W_end.blockers2d():
            col = (190, 150, 80) if bid in W.inter or bid.endswith(".panel") else (120, 124, 128)
            dr.rectangle((X(x0), Y(y1), X(x1), Y(y0)), outline=col, fill=None)
        for i in W.inter.values():
            if i["type"] == "checkpoint":
                mn, mx = aabb(i["center"], i["size"])
                dr.rectangle((X(mn[0]), Y(mx[1]), X(mx[0]), Y(mn[1])), outline=(90, 160, 230))
        for a, b in zip(path, path[1:]):
            dr.line((X(a[0]), Y(a[1]), X(b[0]), Y(b[1])), fill=(230, 90, 70), width=2)
        dr.text((8, 8), f"{L['id']} offline reachability ({report['result']}) - green = capsule-reachable floor, red = bot route. NOT AN ENGINE CAPTURE",
                fill=(220, 220, 210))
        im.save(args.png)
    except ImportError:
        pass

    print(json.dumps({k: report[k] for k in ("kind", "layout", "checks_total", "result", "failures")}, ensure_ascii=False, indent=1))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
