"""Upsize only the remaining marginal s5 restoring stages."""

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
master = db.findMaster("sky130_fd_sc_hd__clkinv_16")
pins = [f"addr0[{index}]" for index in range(2, 8)] + ["addr1[6]"]
targets = []

for inst in block.getInsts():
    if not inst.isBlock() and inst.getMaster().getType() != "CORE_SPACER":
        inst.setPlacementStatus("FIRM")

for pin in pins:
    tag = pin.replace("[", "_").replace("]", "")
    inst = block.findInst(f"eco4o_{tag}_s5")
    if inst is None:
        raise RuntimeError(f"Missing s5 for {pin}")
    old_master = inst.getMaster().getName()
    if not inst.swapMaster(master):
        raise RuntimeError(f"Could not upsize {inst.getName()}")
    inst.setPlacementStatus("PLACED")
    targets.append(
        {
            "pin": pin,
            "instance": inst.getName(),
            "old_master": old_master,
            "new_master": inst.getMaster().getName(),
            "initial_location": inst.getLocation(),
        }
    )

target_locations = [block.findInst(item["instance"]).getLocation() for item in targets]
removed = []
for inst in list(block.getInsts()):
    cell = inst.getMaster().getName()
    physical_only = inst.getMaster().getType() == "CORE_SPACER" or "__decap_" in cell
    if not physical_only:
        continue
    x, y = inst.getLocation()
    if not any(abs(x - tx) <= 80 * dbu and abs(y - ty) <= 80 * dbu for tx, ty in target_locations):
        continue
    removed.append(
        {"instance": inst.getName(), "cell": cell, "location": inst.getLocation()}
    )
    odb.dbInst.destroy(inst)

(out / "restoring_stage_upsize.json").write_text(
    json.dumps({"targets": targets, "removed_physical": removed}, indent=2) + "\n"
)
odb.write_db(db, str(out / "soc_top.seed.odb"))
odb.write_def(block, str(out / "soc_top.seed.def"))
print(f"Upsized {len(targets)} s5 cells; removed {len(removed)} local physical-only cells")
