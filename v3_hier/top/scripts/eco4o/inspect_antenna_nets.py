import os

import odb


db = odb.dbDatabase.create()
odb.read_db(db, os.environ["ECO4O_INSPECT_ODB"])
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()

for net_name in (
    "_0347_",
    "_0705_",
    "u_axi_interconnect.axil_wstrb_reg[3]",
    "net207",
):
    net = block.findNet(net_name)
    print(f"NET {net_name} exists={net is not None}")
    if net is None:
        continue
    for iterm in net.getITerms():
        inst = iterm.getInst()
        x, y = inst.getLocation()
        print(
            f"  {inst.getName()}/{iterm.getMTerm().getName()} "
            f"{inst.getMaster().getName()} ({x / dbu:.3f},{y / dbu:.3f}) "
            f"{iterm.getIoType()}"
        )
