"""Deterministic check of a delivery mission (P1's D1/D2/D3 wording) over an aerogen sim trace.

The geometry restates AeroEval's delivery world as P1 models it for Gazebo
(`gazebo_validation/world_spec.py`): a 5x5 road grid, 16 buildings 20 m high filling each
cell inset by half of a 10 m road, depot I40. Tolerances follow P1's checks: 3 m in xy and 2 m in z.

What counts as success:
- every delivery node is visited in the order the task names it;
- each visit descends to <= 1 m + 2 m tolerance and holds >= 10 s there;
- the drone is back at the depot after the last delivery;
- no flown segment passes through a building below its roof.

`over_block` (any flight above a city block) is reported but does not fail the mission.
The world prompt forbids it, but P1's Gazebo validator accepts it.
"""
from __future__ import annotations

import math
import re

X_LINES = [-90.0, -45.0, 0.0, 45.0, 90.0]
Y_LINES = [-40.0, -10.0, 20.0, 50.0, 80.0]
NODES = {f"I{r}{c}": (X_LINES[c], Y_LINES[r]) for r in range(5) for c in range(5)}
DEPOT = "I40"
BUILDING_H, INSET = 20.0, 5.0
TOL_XY, TOL_Z, DROP_Z, HOVER_S = 3.0, 2.0, 1.0, 10.0
BOXES = [(X_LINES[i] + INSET, X_LINES[i + 1] - INSET, Y_LINES[j] + INSET, Y_LINES[j + 1] - INSET)
         for i in range(4) for j in range(4)]


def checkpoints(task: str) -> list[str]:
    """D2: pass-through nodes that must be visited before the delivery."""
    return re.findall(r"checkpoint (I\d\d)", task)


def delivery_nodes(task: str) -> list[str]:
    """Delivery stops in the order the task first names them (depot and checkpoints excluded)."""
    seen = []
    for n in re.findall(r"I\d\d", task):
        if n != DEPOT and n not in seen and n not in checkpoints(task):
            seen.append(n)
    return seen


def _states(trace):
    """(x, y, z, hold_s, tool) after each executed motion entry."""
    out = []
    for e in trace:
        if "x" in e and "z" in e and e.get("tool") not in ("arm", "point_gimbal"):
            out.append((e["x"], e["y"], e["z"], float(e.get("hover_duration") or 0.0), e["tool"]))
    return out


def _segment_hits(p, q, boxes, below=None, step=1.0):
    n = max(1, int(math.dist(p, q) / step))
    for k in range(n + 1):
        t = k / n
        x, y, z = (p[i] + t * (q[i] - p[i]) for i in range(3))
        for b in boxes:
            if b[0] <= x <= b[1] and b[2] <= y <= b[3] and z > 0.2 and (below is None or z < below):
                return (round(x, 1), round(y, 1), round(z, 1))
    return None


def check(task: str, trace: list[dict]) -> dict:
    st = _states(trace)
    stops = delivery_nodes(task)
    res = {"stops": stops, "delivered": [], "returned": False, "landed": False,
           "collision": None, "over_block": None}
    if not st:
        return {**res, "valid": False, "reason": "never_flew"}
    # hold time at the same spot accumulates over consecutive entries (go_to + hover)
    holds, run = [], 0.0
    for i, s in enumerate(st):
        same = i > 0 and math.dist(s[:3], st[i - 1][:3]) < 0.5
        run = (run if same else 0.0) + s[3]
        holds.append(run)
    dx, dy = NODES[DEPOT]
    near = lambda i, node: math.hypot(st[i][0] - NODES[node][0], st[i][1] - NODES[node][1]) <= TOL_XY
    i0 = 0
    for cp in checkpoints(task):          # D2: pass through the checkpoint first
        hit = next((i for i in range(i0, len(st)) if near(i, cp)), None)
        if hit is None:
            return {**res, "valid": False, "reason": f"checkpoint {cp} not visited first"}
        i0 = hit + 1
    out_and_back = "out-and-back" in task  # D3: back at the depot between the two trips
    for k, node in enumerate(stops):
        if out_and_back and k > 0:
            back = next((i for i in range(i0, len(st)) if near(i, DEPOT)), None)
            if back is None:
                break
            i0 = back + 1
        hit = next((i for i in range(i0, len(st))
                    if near(i, node) and st[i][2] <= DROP_Z + TOL_Z and holds[i] >= HOVER_S - 0.5), None)
        if hit is None:
            break
        res["delivered"].append(node)
        i0 = hit + 1
    if len(res["delivered"]) == len(stops):
        res["returned"] = any(math.hypot(s[0] - dx, s[1] - dy) <= TOL_XY for s in st[i0:])
    res["landed"] = st[-1][4] in ("land", "return_to_launch") or st[-1][2] <= 0.2
    pts = [(NODES[DEPOT][0], NODES[DEPOT][1], 0.0)] + [s[:3] for s in st]
    for p, q in zip(pts, pts[1:]):
        res["collision"] = res["collision"] or _segment_hits(p, q, BOXES, below=BUILDING_H)
        res["over_block"] = res["over_block"] or _segment_hits(p, q, BOXES)
    ok = len(res["delivered"]) == len(stops) and res["returned"] and not res["collision"]
    reason = ("ok" if ok else "collision" if res["collision"] else
              f"delivered {len(res['delivered'])}/{len(stops)}" if len(res["delivered"]) < len(stops)
              else "no_return")
    return {**res, "valid": ok, "reason": reason}


if __name__ == "__main__":
    import json
    import sys
    m = json.load(open(sys.argv[1]))
    print(json.dumps(check(m["task"], m["trace"]), indent=1))
