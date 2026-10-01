"""Rank nearby legal sites for the addr0[6] final stage."""

import math
import os
from pathlib import Path

import odb


source = Path(os.environ["ECO4O_SOURCE_ODB"])
db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
stage = block.findInst("eco4o_addr0_6_s6")
sink = block.findInst("ram.u_sram_macro").findITerm("addr0[6]")
_, sink_x, sink_y = sink.getAvgXY()
width = stage.getMaster().getWidth()
height = stage.getMaster().getHeight()


def is_physical_only(inst):
    cell = inst.getMaster().getName()
    return inst.getMaster().getType() == "CORE_SPACER" or "__decap_" in cell


nearby = []
for inst in block.getInsts():
    if inst == stage or is_physical_only(inst):
        continue
    box = inst.getBBox()
    if (
        box.xMin() < sink_x + width
        and box.xMax() > sink_x - 60 * dbu
        and box.yMin() < sink_y + 60 * dbu
        and box.yMax() > sink_y - 60 * dbu
    ):
        nearby.append(inst)


candidates = []
for row in block.getRows():
    row_box = row.getBBox()
    step = row.getSpacing()
    if row.getSite().getHeight() != height or step <= 0:
        continue
    if abs(row_box.yMin() - sink_y) > 50 * dbu:
        continue
    lo = max(0, math.ceil((sink_x - 50 * dbu - width - row_box.xMin()) / step))
    hi = min(
        row.getSiteCount() - math.ceil(width / step),
        math.floor((sink_x - row_box.xMin()) / step),
    )
    for index in range(lo, hi + 1):
        x = row_box.xMin() + index * step
        y = row_box.yMin()
        colliders = []
        rejected = []
        for inst in nearby:
            box = inst.getBBox()
            if not (
                x < box.xMax()
                and x + width > box.xMin()
                and y < box.yMax()
                and y + height > box.yMin()
            ):
                continue
            has_clock = any(
                iterm.getNet() is not None
                and str(iterm.getNet().getSigType()) == "CLOCK"
                for iterm in inst.getITerms()
            )
            if (
                inst.isBlock()
                or inst.getMaster().getType() == "CORE_WELLTAP"
                or has_clock
                or inst.getName().startswith("eco4o_")
            ):
                rejected.append(inst)
            else:
                colliders.append(inst)
        if rejected:
            continue
        distance = abs(sink_x - (x + width)) + abs(
            sink_y - (y + height // 2)
        )
        score = distance + len(colliders) * 50 * dbu
        candidates.append((score, distance, x, y, row, colliders))

print(
    "SINK",
    f"{sink_x / dbu:.3f}",
    f"{sink_y / dbu:.3f}",
    "OLD",
    *(f"{value / dbu:.3f}" for value in stage.getLocation()),
)
for _, distance, x, y, row, colliders in sorted(candidates)[:40]:
    print(
        "SITE",
        f"{x / dbu:.3f}",
        f"{y / dbu:.3f}",
        str(row.getOrient()),
        "DIST",
        f"{distance / dbu:.3f}",
        "COLLIDERS",
        ",".join(f"{inst.getName()}:{inst.getMaster().getName()}" for inst in colliders)
        or "none",
    )
