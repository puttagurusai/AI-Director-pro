"""Spatial packer: lawns, path edges, walls. Uses normalized footprints."""

from __future__ import annotations

import math
import random

from .logutil import log

# Packing footprints (meters). PH bboxes are often tiny/flat/wrong-axis.
FOOT = {
    "tree": (2.4, 2.4, 6.0),
    "bush": (1.4, 1.4, 1.3),
    "plant": (0.6, 0.6, 1.1),
    "rock": (1.2, 1.2, 0.8),
    "bench": (1.6, 0.55, 0.9),
    "sofa": (2.2, 0.9, 0.9),
    "coffee_table": (1.2, 0.7, 0.45),
    "dining_chair": (0.5, 0.55, 0.95),
    "desk": (1.4, 0.7, 0.75),
    "bookshelf": (0.9, 0.4, 1.8),
    "side_table": (0.5, 0.5, 0.55),
    "streetlamp": (0.4, 0.4, 4.5),
    "building_mass": (8.0, 8.0, 14.0),
    "path": (4.0, 20.0, 0.08),
    "pond": (6.0, 4.0, 0.08),
    "crate": (1.1, 1.1, 1.1),
    "module": (4.0, 4.0, 3.0),
    "animal": (1.8, 0.8, 1.4),
    "enclosure": (7.0, 9.0, 3.0),
}


def normalize_size(obj: dict) -> tuple[float, float, float]:
    cat = obj.get("category") or "mass"
    base = FOOT.get(cat)
    raw = obj.get("real_size_m") or [1, 1, 1]
    try:
        sx, sy, sz = float(raw[0]), float(raw[1]), float(raw[2])
    except Exception:
        sx, sy, sz = 1.0, 1.0, 1.0
    if base:
        # keep PH if it looks like a real prop; else use catalog footprint
        if cat in ("tree", "bush", "plant"):
            sx, sy, sz = base
        elif max(sx, sy, sz) < 0.2 or max(sx, sy) / max(min(sx, sy), 0.05) > 12:
            sx, sy, sz = base
        else:
            sx = max(sx, base[0] * 0.6)
            sy = max(sy, base[1] * 0.6)
            sz = max(sz, base[2] * 0.5)
    obj["real_size_m"] = [round(sx, 3), round(sy, 3), round(sz, 3)]
    return sx, sy, sz


def _aabb(x, y, sx, sy, yaw=0.0):
    if abs(abs(yaw) - math.pi / 2) < 0.25:
        sx, sy = sy, sx
    return x - sx / 2, y - sy / 2, x + sx / 2, y + sy / 2


def _overlap(a, b, gap=0.2) -> bool:
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0] or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def _pose(x, y, z=0.0, yaw=0.0):
    return {
        "location_m": [round(x, 3), round(y, 3), round(z, 3)],
        "rotation_euler_rad": [0.0, 0.0, round(yaw, 4)],
        "scale": [1.0, 1.0, 1.0],
        "support": "ground",
        "snap_z_pending": True,
        "infeasibility": None,
    }


class Pack:
    def __init__(self, wx, wy):
        self.wx, self.wy = wx, wy
        self.occ = []
        self.poses = {}

    def put(self, oid, x, y, sx, sy, yaw=0.0, z=0.0, gap=0.25, solid=True) -> bool:
        box = _aabb(x, y, sx, sy, yaw)
        m = 0.4
        if box[0] < m or box[1] < m or box[2] > self.wx - m or box[3] > self.wy - m:
            return False
        if solid:
            for other in self.occ:
                if _overlap(box, other, gap):
                    return False
            self.occ.append(box)
        self.poses[oid] = _pose(x, y, z, yaw)
        return True

    def spiral(self, oid, x0, y0, sx, sy, yaw=0.0, z=0.0, step=0.6, n=40, gap=0.25) -> bool:
        for k in range(0, n):
            r = step * k
            spots = [(x0, y0)] if k == 0 else [
                (x0 + r * math.cos(t * math.pi / 4), y0 + r * math.sin(t * math.pi / 4)) for t in range(8)
            ]
            for x, y in spots:
                if self.put(oid, x, y, sx, sy, yaw, z, gap=gap):
                    return True
        return False

    def force_place(self, oid, sx, sy, yaw=0.0) -> None:
        """Never leave an object unresolved — shrink gap/size then dump on the lawn."""
        for gap in (0.2, 0.08, 0.0):
            for scale in (1.0, 0.65, 0.4):
                ssx, ssy = max(0.3, sx * scale), max(0.3, sy * scale)
                step = max(0.7, min(ssx, ssy) * 0.8)
                y = ssy / 2 + 0.5
                while y < self.wy - ssy / 2:
                    x = ssx / 2 + 0.5
                    while x < self.wx - ssx / 2:
                        if self.put(oid, x, y, ssx, ssy, yaw=yaw, gap=gap):
                            return
                        x += step
                    y += step
        self.poses[oid] = _pose(min(2.0, self.wx * 0.15), min(2.0, self.wy * 0.15), yaw=yaw)


def _lawn_spots(wx, wy, path_half, count, min_d=3.4, seed=7):
    """Random points on left/right lawns with a minimum spacing (not a grid)."""
    rng = random.Random(seed)
    spots = []
    tries = 0
    while len(spots) < count and tries < count * 50:
        tries += 1
        if rng.random() < 0.5:
            x = rng.uniform(2.2, max(3.0, wx / 2 - path_half - 1.8))
        else:
            x = rng.uniform(min(wx - 2.2, wx / 2 + path_half + 1.8), wx - 2.2)
        y = rng.uniform(2.2, wy - 2.2)
        if all((x - a) ** 2 + (y - b) ** 2 >= min_d ** 2 for a, b in spots):
            spots.append((x, y))
    rng.shuffle(spots)
    return spots


def _apply_relation_skills(p: Pack, objects, by, wx, wy, path_half, domain, r=0.5, seed=1000):
    """LayoutGPT/SceneCraft skills: along, next_to, in_front_of, facing, scatter."""
    idmap = {o["id"]: o for o in objects}
    along_i = 0
    for o in objects:
        if o["id"] in p.poses:
            continue
        rels = o.get("relations") or []
        types = {r.get("type") for r in rels}
        if "along" not in types:
            continue
        sx, sy, sz = normalize_size(o)
        side = 1 if along_i % 2 == 0 else -1
        y = wy * (0.25 + 0.08 * along_i)
        y = min(wy - 3.0, max(3.0, y))
        x = wx / 2 + side * (path_half + max(sy, sx) / 2 + 0.5)
        yaw = -math.pi / 2 if side > 0 else math.pi / 2
        if p.put(o["id"], x, y, sx, sy, yaw=yaw) or p.spiral(o["id"], x, y, sx, sy, yaw=yaw):
            along_i += 1

    for o in objects:
        if o["id"] in p.poses:
            continue
        for rel in o.get("relations") or []:
            typ = rel.get("type")
            tgt = rel.get("target")
            if typ not in ("next_to", "in_front_of", "facing"):
                continue
            if tgt not in p.poses:
                continue
            sx, sy, sz = normalize_size(o)
            tl = p.poses[tgt]["location_m"]
            to = idmap.get(tgt) or {}
            tsx, tsy, _ = normalize_size(to) if to else (1.0, 1.0, 1.0)
            clr = float(rel.get("clearance_m") or 0.4)
            if typ == "in_front_of":
                x, y = tl[0], tl[1] + tsy / 2 + sy / 2 + clr
                yaw = 0.0
            elif typ == "next_to":
                x, y = tl[0] + tsx / 2 + sx / 2 + clr, tl[1]
                yaw = math.pi / 2
            else:
                x, y = tl[0], tl[1] - (tsy / 2 + sy / 2 + clr)
                yaw = math.atan2(tl[1] - y, tl[0] - x) - math.pi / 2
            if p.put(o["id"], x, y, sx, sy, yaw=yaw) or p.spiral(o["id"], x, y, sx, sy, yaw=yaw):
                break

    scatter_i = 0
    spots = _lawn_spots(wx, wy, path_half, 40, min_d=3.8 - r * 1.8, seed=seed + 31)
    rng = random.Random(seed + 5)
    for o in objects:
        if o["id"] in p.poses:
            continue
        types = {r.get("type") for r in (o.get("relations") or [])}
        if "scatter" not in types:
            continue
        sx, sy, sz = normalize_size(o)
        yaw = rng.uniform(0, 6.28)
        if scatter_i < len(spots):
            x, y = spots[scatter_i]
            scatter_i += 1
            p.put(o["id"], x, y, sx, sy, yaw=yaw, gap=0.7) or p.spiral(o["id"], x, y, sx, sy, yaw=yaw, gap=0.6)


def pack_scene(objects: list, world: dict, domain: str, randomness: float = 0.5) -> dict:
    wx = float(world["extent_x_m"])
    wy = float(world["extent_y_m"])
    r = max(0.0, min(1.0, float(randomness)))
    seed = int(1000 + r * 9000)
    for o in objects:
        normalize_size(o)
    p = Pack(wx, wy)
    by: dict[str, list] = {}
    for o in objects:
        by.setdefault(o["category"], []).append(o)

    rng = random.Random(seed)
    path_half = 2.2
    for o in by.get("path") or []:
        sx, sy = max(4.0, min(6.0, wx * 0.08)), wy * 0.90
        o["real_size_m"] = [sx, sy, 0.08]
        path_half = sx / 2
        p.put(o["id"], wx / 2, wy / 2, sx, sy, z=0.03, gap=0.0, solid=True)

    # Holodeck slots: even meter spacing along the path, both sides.
    def path_slots(n, extra=1.1):
        slots = []
        if n <= 0:
            return slots
        for i in range(n):
            t = (i + 0.5) / n
            y = 5.0 + t * (wy - 10.0) + rng.uniform(-1.5, 1.5) * r
            side = 1 if i % 2 == 0 else -1
            x = wx / 2 + side * (path_half + extra) + rng.uniform(-0.4, 0.4) * r
            yaw = -math.pi / 2 if side > 0 else math.pi / 2
            slots.append((x, max(4.0, min(wy - 4.0, y)), yaw))
        return slots

    if domain == "interior":
        for o in by.get("sofa") or []:
            sx, sy, sz = normalize_size(o)
            p.put(o["id"], wx * 0.5, sy / 2 + 0.2, sx, sy)
        sofa = next((o for o in by.get("sofa") or [] if o["id"] in p.poses), None)
        for o in by.get("coffee_table") or []:
            sx, sy, sz = normalize_size(o)
            if sofa:
                sl = p.poses[sofa["id"]]["location_m"]
                ssx, ssy, _ = normalize_size(sofa)
                p.put(o["id"], sl[0], sl[1] + ssy / 2 + sy / 2 + 0.5, sx, sy)
            else:
                p.put(o["id"], wx * 0.5, wy * 0.45, sx, sy)
        for o in by.get("bookshelf") or []:
            sx, sy, sz = normalize_size(o)
            p.put(o["id"], sx / 2 + 0.15, wy * 0.65, sx, sy, yaw=math.pi / 2)
        for i, o in enumerate(by.get("dining_chair") or []):
            sx, sy, sz = normalize_size(o)
            table = next((t for t in by.get("coffee_table") or [] if t["id"] in p.poses), None)
            if table:
                tl = p.poses[table["id"]]["location_m"]
                tsx, tsy, _ = normalize_size(table)
                sign = 1 if i % 2 == 0 else -1
                p.put(o["id"], tl[0] + sign * (tsx / 2 + sx / 2 + 0.28), tl[1], sx, sy, yaw=sign * math.pi / 2)
        for i, o in enumerate(by.get("plant") or []):
            sx, sy, sz = normalize_size(o)
            corners = [(0.7, 0.7), (wx - 0.7, 0.7), (0.7, wy - 0.7), (wx - 0.7, wy - 0.7)]
            cx, cy = corners[i % 4]
            p.put(o["id"], cx, cy, sx, sy)

    # City buildings flanking the street
    for i, o in enumerate(by.get("building_mass") or []):
        sx, sy, sz = normalize_size(o)
        side = -1 if i % 2 == 0 else 1
        p.put(o["id"], wx / 2 + side * (wx * 0.32), wy * (0.2 + 0.15 * (i // 2)), sx, sy)

    _apply_relation_skills(p, objects, by, wx, wy, path_half, domain, r=r, seed=seed)

    benches = [o for o in (by.get("bench") or []) if o["id"] not in p.poses]
    for slot, o in zip(path_slots(len(benches), extra=1.4), benches):
        sx, sy, sz = normalize_size(o)
        x, y, yaw = slot
        p.put(o["id"], x, y, sx, sy, yaw=yaw) or p.spiral(o["id"], x, y, sx, sy, yaw=yaw)

    lamps = [o for o in (by.get("streetlamp") or []) if o["id"] not in p.poses]
    for slot, o in zip(path_slots(len(lamps), extra=0.7), lamps):
        sx, sy, sz = normalize_size(o)
        x, y, yaw = slot
        p.put(o["id"], x, y, sx, sy) or p.spiral(o["id"], x, y, sx, sy)

    for o in by.get("pond") or []:
        if o["id"] in p.poses:
            continue
        sx, sy, sz = normalize_size(o)
        p.put(o["id"], wx * 0.22, wy * 0.28, sx, sy, gap=0.6)

    trees = [o for o in (by.get("tree") or []) if o["id"] not in p.poses]
    bushes = [o for o in (by.get("bush") or []) if o["id"] not in p.poses]
    rocks = [o for o in (by.get("rock") or []) if o["id"] not in p.poses]
    t_spots = _lawn_spots(wx, wy, path_half, max(len(trees), 4), min_d=5.0 - r * 2.0, seed=seed + 11)
    b_spots = _lawn_spots(wx, wy, path_half, max(len(bushes), 4), min_d=2.6 - r * 0.8, seed=seed + 23)
    rk_spots = _lawn_spots(wx, wy, path_half, max(len(rocks), 4), min_d=3.0, seed=seed + 41)
    for spots, group, gap in (
        (t_spots, trees, 0.9),
        (b_spots, bushes, 0.5),
        (rk_spots, rocks, 0.4),
    ):
        for i, o in enumerate(group):
            sx, sy, sz = normalize_size(o)
            yaw = rng.uniform(0, 6.28) * r
            if i < len(spots):
                x, y = spots[i]
                if not p.put(o["id"], x, y, sx, sy, yaw=yaw, gap=gap):
                    p.spiral(o["id"], x, y, sx, sy, yaw=yaw, gap=gap * 0.7, n=50)
            else:
                p.force_place(o["id"], sx, sy, yaw=yaw)

    for o in objects:
        if o["id"] in p.poses:
            continue
        sx, sy, sz = normalize_size(o)
        if not p.spiral(o["id"], wx * 0.3, wy * 0.5, sx, sy, n=80, gap=0.1):
            p.force_place(o["id"], sx, sy)

    _separate(p, objects, rounds=10)
    log(f"pack holodeck-slots domain={domain} placed={len(p.poses)}/{len(objects)} world={wx:.0f}x{wy:.0f}")
    return p.poses


def _separate(p: Pack, objects, rounds: int = 8) -> None:
    """LEGO-Net style: push overlapping footprints apart in XY (meters)."""
    sizes = {o["id"]: normalize_size(o)[:2] for o in objects if o["id"] in p.poses}
    ids = [i for i in p.poses if i in sizes]
    for _ in range(rounds):
        moved = False
        for i, a in enumerate(ids):
            ax, ay = p.poses[a]["location_m"][:2]
            asx, asy = sizes[a]
            ab = _aabb(ax, ay, asx, asy, p.poses[a]["rotation_euler_rad"][2])
            for b in ids[i + 1 :]:
                bx, by = p.poses[b]["location_m"][:2]
                bsx, bsy = sizes[b]
                bb = _aabb(bx, by, bsx, bsy, p.poses[b]["rotation_euler_rad"][2])
                if not _overlap(ab, bb, gap=0.15):
                    continue
                dx, dy = ax - bx, ay - by
                dist = math.hypot(dx, dy) or 0.01
                push = 0.35
                ax += (dx / dist) * push
                ay += (dy / dist) * push
                bx -= (dx / dist) * push
                by -= (dy / dist) * push
                ax = min(p.wx - 1.5, max(1.5, ax))
                ay = min(p.wy - 1.5, max(1.5, ay))
                bx = min(p.wx - 1.5, max(1.5, bx))
                by = min(p.wy - 1.5, max(1.5, by))
                p.poses[a]["location_m"][0], p.poses[a]["location_m"][1] = round(ax, 3), round(ay, 3)
                p.poses[b]["location_m"][0], p.poses[b]["location_m"][1] = round(bx, 3), round(by, 3)
                moved = True
        if not moved:
            break
