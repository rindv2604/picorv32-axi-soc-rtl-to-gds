import os
from pathlib import Path

import odb


odb_path = Path(os.environ["ECO4O_INPUT_ODB"])
db = odb.dbDatabase.create()
odb.read_db(db, str(odb_path))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()

for name in [
    "eco4g_a6_upper",
    "eco4k_a6_mid",
    "wire189",
    "wire190",
    "wire191",
    "wire192",
]:
    inst = block.findInst(name)
    if inst is None:
        continue
    print(name, inst.getMaster().getName(), [v / dbu for v in inst.getLocation()])
    for iterm in inst.getITerms():
        net = iterm.getNet()
        if net is not None and iterm.getSigType() == "SIGNAL":
            print(
                " ",
                iterm.getMTerm().getName(),
                iterm.getIoType(),
                net.getName(),
                len(net.getITerms()),
                "wire",
                bool(net.getWire()),
            )

for net_name in ["eco4g_a6_upper_net", "eco4k_a6_out_net"]:
    net = block.findNet(net_name)
    print(net_name)
    for iterm in net.getITerms():
        inst = iterm.getInst()
        print(
            " ",
            inst.getName(),
            iterm.getMTerm().getName(),
            iterm.getIoType(),
            [v / dbu for v in inst.getLocation()],
        )

macro = block.findInst("ram.u_sram_macro")
for y_um in [380.8, 383.52, 391.68, 397.12, 399.84, 402.56, 405.28, 408.0, 410.72, 541.28, 549.44, 554.88, 563.04, 568.48, 576.64, 582.08]:
    print("ROWS", y_um)
    for row in block.getRows():
        box = row.getBBox()
        if box.yMin() == round(y_um * dbu):
            print(
                " ",
                box.xMin() / dbu,
                box.xMax() / dbu,
                box.yMin() / dbu,
                box.yMax() / dbu,
                row.getSpacing() / dbu,
                str(row.getOrient()),
            )
for pin in [
    "addr0[1]",
    "addr0[2]",
    "addr0[3]",
    "addr0[4]",
    "addr0[5]",
    "addr0[6]",
    "addr0[7]",
    "addr1[6]",
]:
    sink = macro.findITerm(pin)
    print(pin, "sink", [v / dbu for v in sink.getAvgXY()])
    tag = pin.replace("[", "_").replace("]", "")
    for stage in range(1, 5):
        inst = block.findInst(f"eco4o_{tag}_s{stage}")
        print(
            f"  s{stage}",
            [v / dbu for v in inst.getLocation()],
            inst.getMaster().getName(),
        )
