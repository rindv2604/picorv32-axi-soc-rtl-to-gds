"""Remove regular signal routing while preserving special PG routing."""

import os
from pathlib import Path

import odb


source = Path(os.environ["ECO4O_SOURCE_ODB"])
out = Path(os.environ["ECO4O_ITER_DIR"])
db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()

removed = 0
for net in block.getNets():
    if net.isSpecial() or net.getSigType() in ("POWER", "GROUND", "CLOCK"):
        continue
    wire = net.getWire()
    if wire is not None:
        odb.dbWire.destroy(wire)
        removed += 1
    for guide in list(net.getGuides()):
        odb.dbGuide.destroy(guide)

for pg_name in ("VPWR", "VGND"):
    pg = block.findNet(pg_name)
    if pg is None or not list(pg.getSWires()):
        raise RuntimeError(f"PG special routing missing on {pg_name}")

odb.write_db(db, str(out / "soc_top.clean_unrouted.odb"))
odb.write_def(block, str(out / "soc_top.clean_unrouted.def"))
print("Removed regular wires from", removed, "signal nets; PG special routes preserved")
