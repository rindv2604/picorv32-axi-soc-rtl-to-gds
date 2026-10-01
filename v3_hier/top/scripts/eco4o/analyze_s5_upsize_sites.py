"""Rank legal clkinv_16 sites for the marginal s5 stages.

This is a read-only placement analysis.  Physical-only cells may be removed,
but macros, taps, clock-connected cells, and the rest of the ECO chain are
treated as fixed obstacles.  Ordinary standard cells are reported as movable
colliders so the implementation script can reserve a site before legalization.
"""

import math
import os
from pathlib import Path

import odb


source = Path(os.environ["ECO4O_SOURCE_ODB"])
db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
rows = list(block.getRows())
master = db.findMaster("sky130_fd_sc_hd__clkinv_16")
pins = [f"addr0[{index}]" for index in range(1, 8)] + ["addr1[6]"]
targets = {
    pin: block.findInst(f"eco4o_{pin.replace('[', '_').replace(']', '')}_s5")
    for pin in pins
}
trial_sites = {
    "addr0[1]": (645.84, 535.84),
    "addr0[2]": (645.84, 557.60),
    "addr0[3]": (645.84, 563.04),
    "addr0[4]": (658.72, 590.24),
    "addr0[5]": (658.72, 601.12),
    "addr0[6]": (645.84, 603.84),
    "addr0[7]": (645.84, 614.72),
    "addr1[6]": (1059.84, 394.40),
}
finals = {
    pin: block.findInst(f"eco4o_{pin.replace('[', '_').replace(']', '')}_s6")
    for pin in pins
}


def is_physical_only(inst):
    cell = inst.getMaster().getName()
    return inst.getMaster().getType() == "CORE_SPACER" or "__decap_" in cell


def has_clock_connection(inst):
    return any(
        iterm.getNet() is not None and str(iterm.getNet().getSigType()) == "CLOCK"
        for iterm in inst.getITerms()
    )


target_names = {inst.getName() for inst in targets.values()}
logical = [
    inst
    for inst in block.getInsts()
    if inst.getName() not in target_names and not is_physical_only(inst)
]

for pin in pins:
    stage = targets[pin]
    final = finals[pin]
    old_x, old_y = stage.getLocation()
    final_box = final.getBBox()
    goal_x = final_box.xMin() - master.getWidth()
    goal_y = final_box.yMin()
    search_x_min = goal_x - 80 * dbu
    search_x_max = goal_x + 80 * dbu + master.getWidth()
    search_y_min = goal_y - 80 * dbu
    search_y_max = goal_y + 80 * dbu + master.getHeight()
    nearby = []
    for inst in logical:
        box = inst.getBBox()
        if (
            box.xMin() < search_x_max
            and box.xMax() > search_x_min
            and box.yMin() < search_y_max
            and box.yMax() > search_y_min
        ):
            nearby.append(inst)
    candidates = []
    trial_x = round(trial_sites[pin][0] * dbu)
    trial_y = round(trial_sites[pin][1] * dbu)
    trial_colliders = []
    for inst in block.getInsts():
        if inst.getName() in target_names or is_physical_only(inst):
            continue
        box = inst.getBBox()
        if (
            trial_x < box.xMax()
            and trial_x + master.getWidth() > box.xMin()
            and trial_y < box.yMax()
            and trial_y + master.getHeight() > box.yMin()
        ):
            trial_colliders.append(
                f"{inst.getName()}:{inst.getMaster().getName()}:{inst.getMaster().getType()}"
                f":clock={has_clock_connection(inst)}"
            )
    print(
        f"TRIAL {pin} {trial_x / dbu:.3f} {trial_y / dbu:.3f} COLLIDERS "
        + (",".join(trial_colliders) or "none")
    )
    for row in rows:
        row_box = row.getBBox()
        step = row.getSpacing()
        if row.getSite().getHeight() != master.getHeight() or step <= 0:
            continue
        if abs(row_box.yMin() - goal_y) > 80 * dbu:
            continue
        lo = max(0, math.ceil((goal_x - 80 * dbu - row_box.xMin()) / step))
        hi = min(
            row.getSiteCount() - math.ceil(master.getWidth() / step),
            math.floor((goal_x + 80 * dbu - row_box.xMin()) / step),
        )
        for index in range(lo, hi + 1):
            x = row_box.xMin() + index * step
            y = row_box.yMin()
            x_max = x + master.getWidth()
            y_max = y + master.getHeight()
            colliders = []
            rejected = False
            for inst in nearby:
                box = inst.getBBox()
                if not (
                    x < box.xMax()
                    and x_max > box.xMin()
                    and y < box.yMax()
                    and y_max > box.yMin()
                ):
                    continue
                if (
                    inst.isBlock()
                    or inst.getMaster().getType() == "CORE_WELLTAP"
                    or has_clock_connection(inst)
                    or inst.getName().startswith("eco4o_")
                ):
                    rejected = True
                    break
                colliders.append(inst)
            if rejected:
                continue
            distance_to_final = abs(x + master.getWidth() - final_box.xMin()) + 4 * abs(
                y - final_box.yMin()
            )
            move_distance = abs(x - old_x) + abs(y - old_y)
            collider_width = sum(inst.getMaster().getWidth() for inst in colliders)
            score = (
                len(colliders) * 500 * dbu
                + collider_width * 10
                + distance_to_final * 4
                + move_distance
            )
            candidates.append(
                (
                    score,
                    distance_to_final,
                    move_distance,
                    x,
                    y,
                    row,
                    colliders,
                )
            )
    print(f"PIN {pin} OLD {old_x / dbu:.3f} {old_y / dbu:.3f}")
    best_by_row = {}
    for item in sorted(candidates, key=lambda value: value[0]):
        best_by_row.setdefault(item[4], item)
    for item in sorted(best_by_row.values(), key=lambda value: value[0])[:30]:
        _, distance, movement, x, y, row, colliders = item
        print(
            "  SITE",
            f"{x / dbu:.3f}",
            f"{y / dbu:.3f}",
            str(row.getOrient()),
            "FINAL_DIST",
            f"{distance / dbu:.3f}",
            "MOVE",
            f"{movement / dbu:.3f}",
            "COLLIDERS",
            ",".join(
                f"{inst.getName()}:{inst.getMaster().getName()}" for inst in colliders
            )
            or "none",
        )
