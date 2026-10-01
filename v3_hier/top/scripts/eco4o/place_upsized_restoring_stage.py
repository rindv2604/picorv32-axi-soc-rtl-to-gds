"""Place clkinv_16 s5 stages and expose only their colliders to DPL."""

import json
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
master = db.findMaster("sky130_fd_sc_hd__clkinv_16")

# Each addr0 site is on a distinct row in the narrow SRAM access channel.
# These sites avoid sequential cells, well taps, the SRAM, and existing ECO
# stages.  The only overlaps are ten ordinary combinational cells/buffers.
sites_um = {
    "addr0[2]": (647.68, 541.28),
    "addr0[3]": (645.84, 549.44),
    "addr0[4]": (647.68, 565.76),
    "addr0[5]": (647.68, 576.64),
    "addr0[6]": (645.84, 590.24),
    "addr0[7]": (647.68, 587.52),
    "addr1[6]": (1059.84, 394.40),
}


def is_physical_only(inst):
    cell = inst.getMaster().getName()
    return inst.getMaster().getType() == "CORE_SPACER" or "__decap_" in cell


def has_clock_connection(inst):
    return any(
        iterm.getNet() is not None and str(iterm.getNet().getSigType()) == "CLOCK"
        for iterm in inst.getITerms()
    )


def find_row(x, y, width, height):
    for row in rows:
        box = row.getBBox()
        if (
            box.yMin() == y
            and box.xMin() <= x
            and x + width <= box.xMax()
            and row.getSite().getHeight() == height
            and (x - box.xMin()) % row.getSpacing() == 0
        ):
            return row
    raise RuntimeError(f"No legal row for ({x}, {y}) width={width}")


pins = list(sites_um)
targets = {
    pin: block.findInst(f"eco4o_{pin.replace('[', '_').replace(']', '')}_s5")
    for pin in pins
}
if any(inst is None for inst in targets.values()):
    raise RuntimeError("Missing one or more s5 instances")
target_names = {inst.getName() for inst in targets.values()}

for inst in block.getInsts():
    if not is_physical_only(inst):
        inst.setPlacementStatus("FIRM")

placements = []
collider_names = set()
target_boxes = []
for pin, (x_um, y_um) in sites_um.items():
    inst = targets[pin]
    old_master = inst.getMaster().getName()
    old_location = inst.getLocation()
    if not inst.swapMaster(master):
        raise RuntimeError(f"Could not upsize {inst.getName()}")
    x = round(x_um * dbu)
    y = round(y_um * dbu)
    width = inst.getMaster().getWidth()
    height = inst.getMaster().getHeight()
    row = find_row(x, y, width, height)
    box = (x, y, x + width, y + height)
    for other_box in target_boxes:
        if (
            box[0] < other_box[2]
            and box[2] > other_box[0]
            and box[1] < other_box[3]
            and box[3] > other_box[1]
        ):
            raise RuntimeError(f"Target sites overlap at {pin}")
    target_boxes.append(box)
    colliders = []
    for other in block.getInsts():
        if other.getName() in target_names or is_physical_only(other):
            continue
        other_box = other.getBBox()
        if not (
            box[0] < other_box.xMax()
            and box[2] > other_box.xMin()
            and box[1] < other_box.yMax()
            and box[3] > other_box.yMin()
        ):
            continue
        if (
            other.isBlock()
            or other.getMaster().getType() == "CORE_WELLTAP"
            or has_clock_connection(other)
            or other.getName().startswith("eco4o_")
        ):
            raise RuntimeError(f"Target {pin} collides with fixed {other.getName()}")
        colliders.append(other.getName())
        collider_names.add(other.getName())
    inst.setPlacementStatus("PLACED")
    inst.setOrient(str(row.getOrient()))
    inst.setLocation(x, y)
    inst.setPlacementStatus("FIRM")
    placements.append(
        {
            "pin": pin,
            "instance": inst.getName(),
            "old_master": old_master,
            "new_master": inst.getMaster().getName(),
            "old_location": old_location,
            "new_location": inst.getLocation(),
            "colliders": colliders,
        }
    )

for name in collider_names:
    block.findInst(name).setPlacementStatus("PLACED")

removed = []
for inst in list(block.getInsts()):
    if not is_physical_only(inst):
        continue
    inst_box = inst.getBBox()
    close = any(
        inst_box.xMin() < box[2] + 120 * dbu
        and inst_box.xMax() > box[0] - 120 * dbu
        and inst_box.yMin() < box[3] + 120 * dbu
        and inst_box.yMax() > box[1] - 120 * dbu
        for box in target_boxes
    )
    if not close:
        continue
    removed.append(
        {
            "instance": inst.getName(),
            "cell": inst.getMaster().getName(),
            "location": inst.getLocation(),
        }
    )
    odb.dbInst.destroy(inst)

plan = {
    "source": str(source),
    "placements": placements,
    "movable_colliders": sorted(collider_names),
    "removed_physical": removed,
}
(out / "restoring_stage_upsize_plan.json").write_text(
    json.dumps(plan, indent=2) + "\n"
)
odb.write_db(db, str(out / "soc_top.seed.odb"))
odb.write_def(block, str(out / "soc_top.seed.def"))
print(
    f"Placed {len(placements)} clkinv_16 stages; movable colliders "
    f"{len(collider_names)}; removed physical-only {len(removed)}"
)
print("Movable:", " ".join(sorted(collider_names)))
