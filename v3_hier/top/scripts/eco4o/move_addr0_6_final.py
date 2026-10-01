"""Move addr0[6] s6 into the adjacent right-hand SRAM channel site."""

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
stage = block.findInst("eco4o_addr0_6_s6")
target_x = round(658.72 * dbu)
target_y = round(579.36 * dbu)


def is_physical_only(inst):
    cell = inst.getMaster().getName()
    return inst.getMaster().getType() == "CORE_SPACER" or "__decap_" in cell


width = stage.getMaster().getWidth()
height = stage.getMaster().getHeight()
for inst in block.getInsts():
    if not is_physical_only(inst):
        inst.setPlacementStatus("FIRM")
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
    raise RuntimeError("Selected addr0[6] s6 site is not legal")

old_location = stage.getLocation()
removed = []
colliders = []
for inst in list(block.getInsts()):
    if inst == stage:
        continue
    box = inst.getBBox()
    if not (
        target_x < box.xMax()
        and target_x + width > box.xMin()
        and target_y < box.yMax()
        and target_y + height > box.yMin()
    ):
        continue
    if not is_physical_only(inst):
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
            raise RuntimeError(
                f"Selected addr0[6] s6 site collides with fixed {inst.getName()} "
                f"({inst.getMaster().getName()})"
            )
        colliders.append(inst.getName())
        inst.setPlacementStatus("PLACED")
        continue
    removed.append(
        {
            "instance": inst.getName(),
            "cell": inst.getMaster().getName(),
            "location": inst.getLocation(),
        }
    )
    odb.dbInst.destroy(inst)

stage.setPlacementStatus("PLACED")
stage.setOrient(str(row.getOrient()))
stage.setLocation(target_x, target_y)
stage.setPlacementStatus("FIRM")

plan = {
    "source": str(source),
    "instance": stage.getName(),
    "master": stage.getMaster().getName(),
    "old_location": old_location,
    "new_location": stage.getLocation(),
    "movable_colliders": sorted(colliders),
    "removed_physical": removed,
}
(out / "addr0_6_final_move.json").write_text(json.dumps(plan, indent=2) + "\n")
odb.write_db(db, str(out / "soc_top.seed.odb"))
odb.write_def(block, str(out / "soc_top.seed.def"))
print(
    f"Moved {stage.getName()} from {old_location} to {stage.getLocation()}; "
    f"movable colliders {len(colliders)}; removed physical-only {len(removed)}"
)
