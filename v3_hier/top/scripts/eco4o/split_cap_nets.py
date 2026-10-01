"""Split the two long nets that became marginal after the final slew route."""

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
buffer_master = db.findMaster("sky130_fd_sc_hd__buf_12")


def is_physical_only(inst):
    cell = inst.getMaster().getName()
    return inst.getMaster().getType() == "CORE_SPACER" or "__decap_" in cell


def rect(inst):
    box = inst.getBBox()
    return box.xMin(), box.yMin(), box.xMax(), box.yMax()


occupied = {
    inst.getName(): rect(inst)
    for inst in block.getInsts()
    if not is_physical_only(inst)
}
physical = {
    inst.getName(): inst for inst in block.getInsts() if is_physical_only(inst)
}
removed = []


def overlaps(x_min, y_min, x_max, y_max):
    return [
        name
        for name, box in occupied.items()
        if x_min < box[2]
        and x_max > box[0]
        and y_min < box[3]
        and y_max > box[1]
    ]


def place_free(inst, target_x, target_y, radius_um=150):
    width = inst.getMaster().getWidth()
    height = inst.getMaster().getHeight()
    radius = radius_um * dbu
    candidates = []
    for row in rows:
        box = row.getBBox()
        step = row.getSpacing()
        if row.getSite().getHeight() != height or step <= 0:
            continue
        if abs(box.yMin() + height // 2 - target_y) > radius:
            continue
        lo = max(0, math.ceil((target_x - radius - box.xMin()) / step))
        hi = min(
            row.getSiteCount() - math.ceil(width / step),
            math.floor((target_x + radius - box.xMin()) / step),
        )
        for index in range(lo, hi + 1):
            x = box.xMin() + index * step
            y = box.yMin()
            if overlaps(x, y, x + width, y + height):
                continue
            distance = abs(x + width // 2 - target_x) + abs(
                y + height // 2 - target_y
            )
            candidates.append((distance, x, y, row))
    if not candidates:
        raise RuntimeError(f"No filler-only site for {inst.getName()}")
    _, x, y, row = min(candidates)
    for name, physical_inst in list(physical.items()):
        box = physical_inst.getBBox()
        if not (
            x < box.xMax()
            and x + width > box.xMin()
            and y < box.yMax()
            and y + height > box.yMin()
        ):
            continue
        removed.append(
            {
                "instance": name,
                "cell": physical_inst.getMaster().getName(),
                "location": physical_inst.getLocation(),
            }
        )
        odb.dbInst.destroy(physical_inst)
        del physical[name]
    inst.setOrient(str(row.getOrient()))
    inst.setLocation(x, y)
    inst.setPlacementStatus("FIRM")
    occupied[inst.getName()] = rect(inst)


def connect_power(inst):
    for pin_name, net_name in (
        ("VPWR", "VPWR"),
        ("VPB", "VPWR"),
        ("VGND", "VGND"),
        ("VNB", "VGND"),
    ):
        inst.findITerm(pin_name).connect(block.findNet(net_name))


plans = []
for driver_inst, driver_pin, new_name in (
    ("eco_buffer_45", "X", "eco4o_capfix_wdata15"),
    ("cpu", "mem_axi_wdata[23]", "eco4o_capfix_wdata23"),
):
    driver = block.findInst(driver_inst).findITerm(driver_pin)
    old_net = driver.getNet()
    loads = [term for term in old_net.getITerms() if term.getIoType() == "INPUT"]
    functional = [
        term for term in loads if term.getInst().getMaster().getType() != "CORE_ANTENNACELL"
    ]
    if len(functional) != 1:
        raise RuntimeError(f"Expected one functional load on {old_net.getName()}")
    _, driver_x, driver_y = driver.getAvgXY()
    _, load_x, load_y = functional[0].getAvgXY()
    buffer_inst = odb.dbInst_create(block, buffer_master, new_name)
    connect_power(buffer_inst)
    place_free(
        buffer_inst,
        (driver_x + load_x) // 2,
        (driver_y + load_y) // 2,
    )
    new_net = odb.dbNet_create(block, f"{new_name}_net")
    for load in loads:
        load.disconnect()
        load.connect(new_net)
    buffer_inst.findITerm("A").connect(old_net)
    buffer_inst.findITerm("X").connect(new_net)
    plans.append(
        {
            "driver": f"{driver_inst}/{driver_pin}",
            "old_net": old_net.getName(),
            "buffer": new_name,
            "location": buffer_inst.getLocation(),
            "new_net": new_net.getName(),
            "moved_loads": [
                f"{term.getInst().getName()}/{term.getMTerm().getName()}"
                for term in loads
            ],
        }
    )

(out / "cap_split_plan.json").write_text(
    json.dumps({"splits": plans, "removed_physical": removed}, indent=2) + "\n"
)
odb.write_db(db, str(out / "soc_top.reference.odb"))
odb.write_def(block, str(out / "soc_top.reference.def"))
print(f"Split {len(plans)} cap nets; removed physical-only {len(removed)}")
for plan in plans:
    print(plan)
