"""Prepare ECO routing while retaining existing detailed wires as ECO context."""

import json
import os
from pathlib import Path

import odb


source = Path(os.environ["ECO4O_SOURCE_ODB"])
plan_dir = Path(os.environ["ECO4O_PLAN_DIR"])
out = Path(os.environ["ECO4O_ITER_DIR"])
out.mkdir(parents=True, exist_ok=True)

db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
plan = json.loads((plan_dir / "placement_plan.json").read_text())
affected = set()
changes = []

for inst in block.getInsts():
    old = plan["original"].get(inst.getName())
    if old is None:
        changes.append(
            {
                "action": "insert",
                "instance": inst.getName(),
                "cell": inst.getMaster().getName(),
                "new_xy": inst.getLocation(),
            }
        )
        affected.update(
            iterm.getNet().getName()
            for iterm in inst.getITerms()
            if iterm.getNet() is not None and iterm.getSigType() == "SIGNAL"
        )
    elif inst.getLocation() != old["location"] or str(inst.getOrient()) != old["orient"]:
        changes.append(
            {
                "action": "move",
                "instance": inst.getName(),
                "cell": inst.getMaster().getName(),
                "old_xy": old["location"],
                "new_xy": inst.getLocation(),
            }
        )
        affected.update(
            iterm.getNet().getName()
            for iterm in inst.getITerms()
            if iterm.getNet() is not None and iterm.getSigType() == "SIGNAL"
        )
    if old is not None:
        inst.setPlacementStatus(old["status"])

(out / "affected_nets.txt").write_text("\n".join(sorted(affected)) + "\n")
(out / "changes.json").write_text(json.dumps(changes, indent=2) + "\n")
odb.write_db(db, str(out / "soc_top.inserted.odb"))
odb.write_def(block, str(out / "soc_top.inserted.def"))
print(f"Retained wires; changed {len(changes)} cells; ECO-route {len(affected)} nets")
