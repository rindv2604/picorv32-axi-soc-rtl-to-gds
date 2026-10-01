"""Add margin to addr0[1] by upsizing and relocating its s5 stage."""

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
stage = block.findInst("eco4o_addr0_1_s5")
master = db.findMaster("sky130_fd_sc_hd__clkinv_16")
target_x = round(647.68 * dbu)
target_y = round(538.56 * dbu)


def is_physical_only(inst):
    cell = inst.getMaster().getName()
    return inst.getMaster().getType() == "CORE_SPACER" or "__decap_" in cell


for inst in block.getInsts():
    if not is_physical_only(inst):
        inst.setPlacementStatus("FIRM")

old_master = stage.getMaster().getName()
old_location = stage.getLocation()
if not stage.swapMaster(master):
    raise RuntimeError("Could not upsize addr0[1] s5")

width = stage.getMaster().getWidth()
height = stage.getMaster().getHeight()
row = next(
    (
        row
        for row in block.getRows()
        if row.getBBox().yMin() == target_y
        and row.getBBox().xMin() <= target_x
        and target_x + width <= row.getBBox().xMax()
        and row.getSite().getHeight() == height
        and (target_x - row.getBBox().xMin()) % row.getSpacing() == 0
    ),
    None,
)
if row is None:
    raise RuntimeError("Selected addr0[1] site is not legal")

colliders = []
for inst in block.getInsts():
    if inst == stage or is_physical_only(inst):
        continue
    box = inst.getBBox()
    if not (
        target_x < box.xMax()
        and target_x + width > box.xMin()
        and target_y < box.yMax()
        and target_y + height > box.yMin()
    ):
        continue
    has_clock = any(
        iterm.getNet() is not None and str(iterm.getNet().getSigType()) == "CLOCK"
        for iterm in inst.getITerms()
    )
    if (
        inst.isBlock()
        or inst.getMaster().getType() == "CORE_WELLTAP"
        or has_clock
        or inst.getName().startswith("eco4o_")
    ):
        raise RuntimeError(f"Selected site collides with fixed {inst.getName()}")
    colliders.append(inst.getName())
    inst.setPlacementStatus("PLACED")

stage.setPlacementStatus("PLACED")
stage.setOrient(str(row.getOrient()))
stage.setLocation(target_x, target_y)
stage.setPlacementStatus("FIRM")

removed = []
for inst in list(block.getInsts()):
    if not is_physical_only(inst):
        continue
    box = inst.getBBox()
    if not (
        box.xMin() < target_x + width + 120 * dbu
        and box.xMax() > target_x - 120 * dbu
        and box.yMin() < target_y + height + 120 * dbu
        and box.yMax() > target_y - 120 * dbu
    ):
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
    "instance": stage.getName(),
    "old_master": old_master,
    "new_master": stage.getMaster().getName(),
    "old_location": old_location,
    "new_location": stage.getLocation(),
    "movable_colliders": sorted(colliders),
    "removed_physical": removed,
}
(out / "addr0_1_upsize_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
odb.write_db(db, str(out / "soc_top.seed.odb"))
odb.write_def(block, str(out / "soc_top.seed.def"))
print(
    f"Upsized {stage.getName()}; movable colliders {len(colliders)}; "
    f"removed physical-only {len(removed)}"
)
print("Movable:", " ".join(sorted(colliders)))
