"""Move the existing s5 restoring stages beside s6 without moving logic."""

import json
import math
import os
from pathlib import Path

import odb


source = Path(os.environ["ECO4O_SOURCE_ODB"])
out = Path(os.environ["ECO4O_ITER_DIR"])
out.mkdir(parents=True, exist_ok=True)

db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
rows = list(block.getRows())


def rect(inst):
    box = inst.getBBox()
    return box.xMin(), box.yMin(), box.xMax(), box.yMax()


def is_physical_only(inst):
    master = inst.getMaster()
    return master.getType() == "CORE_SPACER" or "__decap_" in master.getName()


pins = [f"addr0[{index}]" for index in range(1, 8)] + ["addr1[6]"]
stages = {
    pin: block.findInst(
        f"eco4o_{pin.replace('[', '_').replace(']', '')}_s5"
    )
    for pin in pins
}
finals = {
    pin: block.findInst(
        f"eco4o_{pin.replace('[', '_').replace(']', '')}_s6"
    )
    for pin in pins
}
if any(inst is None for inst in list(stages.values()) + list(finals.values())):
    raise RuntimeError("Missing restoring-stage instance")

occupied = {
    inst.getName(): rect(inst)
    for inst in block.getInsts()
    if inst not in stages.values()
}
fillers = {
    inst.getName()
    for inst in block.getInsts()
    if is_physical_only(inst) and inst not in stages.values()
}
removed = []
moves = []


def overlaps(x_min, y_min, x_max, y_max):
    return [
        name
        for name, box in occupied.items()
        if x_min < box[2]
        and x_max > box[0]
        and y_min < box[3]
        and y_max > box[1]
    ]


for pin in pins:
    inst = stages[pin]
    final = finals[pin]
    width = inst.getMaster().getWidth()
    height = inst.getMaster().getHeight()
    final_box = rect(final)
    target_x = final_box[0] - width
    target_y = final_box[1]
    candidates = []
    for row in rows:
        row_box = row.getBBox()
        step = row.getSpacing()
        if row.getSite().getHeight() != height or step <= 0:
            continue
        if abs(row_box.yMin() - target_y) > 60 * dbu:
            continue
        lo = max(0, math.ceil((target_x - 35 * dbu - row_box.xMin()) / step))
        hi = min(
            row.getSiteCount() - math.ceil(width / step),
            math.floor((target_x + 35 * dbu - row_box.xMin()) / step),
        )
        for index in range(lo, hi + 1):
            x = row_box.xMin() + index * step
            names = overlaps(x, row_box.yMin(), x + width, row_box.yMin() + height)
            if any(name not in fillers for name in names):
                continue
            distance = abs(x + width - final_box[0]) + 4 * abs(
                row_box.yMin() - final_box[1]
            )
            candidates.append((distance, x, row_box.yMin(), row, names))
    if not candidates:
        raise RuntimeError(f"No filler-only site near s6 for {pin}")
    _, x, y, row, names = min(candidates, key=lambda item: item[0])
    for name in names:
        if name not in fillers:
            continue
        filler = block.findInst(name)
        removed.append(
            {
                "instance": name,
                "cell": filler.getMaster().getName(),
                "location": filler.getLocation(),
            }
        )
        odb.dbInst.destroy(filler)
        occupied.pop(name)
        fillers.remove(name)
    old_location = inst.getLocation()
    inst.setPlacementStatus("PLACED")
    inst.setOrient(str(row.getOrient()))
    inst.setLocation(x, y)
    inst.setPlacementStatus("FIRM")
    occupied[inst.getName()] = rect(inst)
    moves.append(
        {
            "pin": pin,
            "instance": inst.getName(),
            "old_location": old_location,
            "new_location": inst.getLocation(),
            "final_location": final.getLocation(),
        }
    )

(out / "restoring_stage_moves.json").write_text(
    json.dumps({"moves": moves, "removed_physical": removed}, indent=2) + "\n"
)
odb.write_db(db, str(out / "soc_top.reference.odb"))
odb.write_def(block, str(out / "soc_top.reference.def"))
print(f"Moved {len(moves)} restoring stages; removed {len(removed)} physical-only cells")
for move in moves:
    print(move)
