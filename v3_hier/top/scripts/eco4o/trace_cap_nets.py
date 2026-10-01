"""Report topology and placement for the post-ECO max-cap nets."""

import os
from pathlib import Path

import odb


source = Path(os.environ["ECO4O_SOURCE_ODB"])
db = odb.dbDatabase.create()
odb.read_db(db, str(source))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()

for inst_name, pin_name in (
    ("eco_buffer_45", "X"),
    ("cpu", "mem_axi_wdata[23]"),
):
    inst = block.findInst(inst_name)
    iterm = inst.findITerm(pin_name)
    if iterm is None:
        names = [term.getMTerm().getName() for term in inst.getITerms()]
        raise RuntimeError(f"Missing {inst_name}/{pin_name}; candidates={names}")
    net = iterm.getNet()
    print("PIN", f"{inst_name}/{pin_name}", "NET", net.getName())
    for term in net.getITerms():
        owner = term.getInst()
        ok, x, y = term.getAvgXY()
        print(
            "  ITERM",
            f"{owner.getName()}/{term.getMTerm().getName()}",
            str(term.getIoType()),
            owner.getMaster().getName(),
            f"{x / dbu:.3f}",
            f"{y / dbu:.3f}",
        )
    for term in net.getBTerms():
        print("  BTERM", term.getName(), str(term.getIoType()))
