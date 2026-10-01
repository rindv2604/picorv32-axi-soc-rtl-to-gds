"""Build a low-disruption ECO from the routed ECO4O-02 database.

The ECO relocates the existing final clkinv_16 stages beside eight marginal
SRAM pins, splits four long addr0 input nets, and splits the remaining long
capacitive branch.  Cells displaced from the pin-access rows are packed into
the vacated clkinv_16 sites to avoid broad detailed-placement movement.
"""

import json
import math
import os
from pathlib import Path

import odb


source = Path(os.environ["ECO4O_SOURCE_DIR"])
out = Path(os.environ["ECO4O_ITER_DIR"])
out.mkdir(parents=True, exist_ok=True)

db = odb.dbDatabase.create()
odb.read_db(db, str(source / "soc_top.routed.odb"))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
rows = list(block.getRows())
macro = block.findInst("ram.u_sram_macro")


def inst_rect(inst):
    box = inst.getBBox()
    return box.xMin(), box.yMin(), box.xMax(), box.yMax()


def is_physical_only(inst):
    master = inst.getMaster()
    return master.getType() == "CORE_SPACER" or "__decap_" in master.getName()


def connect_power(inst):
    for pin_name, net_name in (
        ("VPWR", "VPWR"),
        ("VPB", "VPWR"),
        ("VGND", "VGND"),
        ("VNB", "VGND"),
    ):
        inst.findITerm(pin_name).connect(block.findNet(net_name))


original = {
    inst.getName(): {
        "location": inst.getLocation(),
        "orient": str(inst.getOrient()),
        "status": str(inst.getPlacementStatus()),
        "cell": inst.getMaster().getName(),
    }
    for inst in block.getInsts()
}

occupied = {inst.getName(): inst_rect(inst) for inst in block.getInsts()}
fillers = {inst.getName() for inst in block.getInsts() if is_physical_only(inst)}
removed_physical = []
movable = set()
inserted = []


def overlapping_names(x_min, y_min, x_max, y_max, ignore=()):
    ignored = set(ignore)
    return [
        name
        for name, box in occupied.items()
        if name not in ignored
        and x_min < box[2]
        and x_max > box[0]
        and y_min < box[3]
        and y_max > box[1]
    ]


def remove_fillers(names, reason):
    for name in names:
        if name not in fillers:
            continue
        inst = block.findInst(name)
        removed_physical.append(
            {
                "instance": name,
                "cell": inst.getMaster().getName(),
                "location": inst.getLocation(),
                "reason": reason,
            }
        )
        odb.dbInst.destroy(inst)
        occupied.pop(name)
        fillers.remove(name)


def row_at(y, x, width):
    for row in rows:
        box = row.getBBox()
        if (
            box.yMin() == y
            and box.xMin() <= x
            and x + width <= box.xMax()
            and row.getSite().getHeight() == 2720
        ):
            return row
    raise RuntimeError(f"No legal row at x={x / dbu}, y={y / dbu}")


def reserve(inst, x_um, y_um, reason):
    x = round(x_um * dbu)
    y = round(y_um * dbu)
    width = inst.getMaster().getWidth()
    row = row_at(y, x, width)
    names = overlapping_names(x, y, x + width, y + inst.getMaster().getHeight())
    remove_fillers(names, reason)
    names = [name for name in names if name not in fillers and name in occupied]
    for name in names:
        collider = block.findInst(name)
        if (
            collider.isBlock()
            or collider.getMaster().getType() == "CORE_WELLTAP"
            or any(
                iterm.getNet() is not None and iterm.getNet().getSigType() == "CLOCK"
                for iterm in collider.getITerms()
            )
        ):
            raise RuntimeError(f"Reserved site collides with fixed {name}")
        collider.setPlacementStatus("PLACED")
        movable.add(name)
    inst.setPlacementStatus("PLACED")
    inst.setOrient(str(row.getOrient()))
    inst.setLocation(x, y)
    inst.setPlacementStatus("FIRM")
    occupied[inst.getName()] = inst_rect(inst)


def place_free(inst, target_x, target_y, reason, radius_um=100):
    width = inst.getMaster().getWidth()
    height = inst.getMaster().getHeight()
    candidates = []
    radius = radius_um * dbu
    for row in rows:
        box = row.getBBox()
        step = row.getSpacing()
        if row.getSite().getHeight() != height or step <= 0:
            continue
        if box.yMin() < target_y - radius or box.yMin() > target_y + radius:
            continue
        lo = max(0, math.ceil((target_x - radius - box.xMin()) / step))
        hi = min(
            row.getSiteCount() - math.ceil(width / step),
            math.floor((target_x + radius - box.xMin()) / step),
        )
        for index in range(lo, hi + 1):
            x = box.xMin() + index * step
            distance = abs(x + width // 2 - target_x) + abs(
                box.yMin() + height // 2 - target_y
            )
            candidates.append((distance, x, box.yMin(), row))
    for _, x, y, row in sorted(candidates, key=lambda item: item[0]):
        names = overlapping_names(x, y, x + width, y + height)
        if any(name not in fillers for name in names):
            continue
        remove_fillers(names, reason)
        inst.setOrient(str(row.getOrient()))
        inst.setLocation(x, y)
        inst.setPlacementStatus("FIRM")
        occupied[inst.getName()] = inst_rect(inst)
        return
    raise RuntimeError(f"No free legal site for {inst.getName()}")


for inst in block.getInsts():
    if not is_physical_only(inst):
        inst.setPlacementStatus("FIRM")

# The final clkinv_16 stages are right-aligned in the narrow channel so their
# output pins are close to the SRAM boundary.  This is required by extracted
# RC: a clkinv_8 in the same channel still left 8 SS-corner slew violations.
final_sites = {
    "addr0[1]": (658.72, 541.28),
    "addr0[2]": (658.72, 552.16),
    "addr0[3]": (647.68, 552.16),
    "addr0[4]": (658.72, 563.04),
    "addr0[5]": (658.72, 573.92),
    "addr0[6]": (647.68, 573.92),
    "addr0[7]": (658.72, 584.80),
    "addr1[6]": (1084.22, 394.40),
}

vacated_slots = []
for pin_name, (final_x, final_y) in final_sites.items():
    tag = pin_name.replace("[", "_").replace("]", "")
    sink = macro.findITerm(pin_name)
    old_net = sink.getNet()
    old_driver = [
        iterm for iterm in old_net.getITerms() if iterm.getIoType() == "OUTPUT"
    ]
    if len(old_driver) != 1 or old_driver[0].getInst().getName() != f"eco4o_{tag}_s4":
        raise RuntimeError(f"Unexpected terminal topology on {pin_name}")

    final = old_driver[0].getInst()
    old_x, old_y = final.getLocation()
    vacated_slots.append(
        {
            "pin": pin_name,
            "x": old_x,
            "y": old_y,
            "width": final.getMaster().getWidth(),
            "height": final.getMaster().getHeight(),
        }
    )
    reserve(final, final_x, final_y, f"Short SRAM access for {pin_name}")

# Remove the displaced cells from the occupancy map, then pack them into the
# exact legal sites vacated by the final stages.  Keep the addr1 group on the
# right side of the SRAM and the addr0 group in the left channel.
colliders = [block.findInst(name) for name in sorted(movable)]
for inst in colliders:
    occupied.pop(inst.getName())

bins = []
for slot in vacated_slots:
    row = row_at(slot["y"], slot["x"], slot["width"])
    bins.append(
        {
            **slot,
            "cursor": slot["x"],
            "remaining": slot["width"],
            "orient": str(row.getOrient()),
        }
    )

for inst in sorted(colliders, key=lambda item: item.getMaster().getWidth(), reverse=True):
    width = inst.getMaster().getWidth()
    old_x, old_y = original[inst.getName()]["location"]
    right_side = old_x > 900 * dbu
    candidates = [
        slot
        for slot in bins
        if slot["remaining"] >= width and (slot["x"] > 900 * dbu) == right_side
    ]
    if not candidates:
        raise RuntimeError(f"No vacated final-stage slot for {inst.getName()}")
    slot = min(
        candidates,
        key=lambda item: abs(item["cursor"] - old_x) + abs(item["y"] - old_y),
    )
    inst.setOrient(slot["orient"])
    inst.setLocation(slot["cursor"], slot["y"])
    inst.setPlacementStatus("FIRM")
    occupied[inst.getName()] = inst_rect(inst)
    slot["cursor"] += width
    slot["remaining"] -= width


def insert_buffer(net_name, sink_inst_name, sink_pin_name, new_name, target_x, target_y):
    old_net = block.findNet(net_name)
    sink_inst = block.findInst(sink_inst_name)
    sink = sink_inst.findITerm(sink_pin_name)
    if sink.getNet() is None or sink.getNet().getName() != old_net.getName():
        raise RuntimeError(f"Unexpected split topology for {net_name}")
    buffer_inst = odb.dbInst_create(
        block, db.findMaster("sky130_fd_sc_hd__buf_12"), new_name
    )
    connect_power(buffer_inst)
    place_free(
        buffer_inst,
        target_x,
        target_y,
        f"Split capacitive net {net_name}",
        radius_um=120,
    )
    new_net = odb.dbNet_create(block, f"{new_name}_net")
    sink.disconnect()
    sink.connect(new_net)
    buffer_inst.findITerm("A").connect(old_net)
    buffer_inst.findITerm("X").connect(new_net)
    inserted.append(
        {
            "instance": buffer_inst.getName(),
            "cell": buffer_inst.getMaster().getName(),
            "net": net_name,
            "location": buffer_inst.getLocation(),
        }
    )


for pin_index, driver_name in ((3, "wire189"), (4, "wire190"), (5, "wire191"), (6, "wire192")):
    tag = f"addr0_{pin_index}"
    stage = block.findInst(f"eco4o_{tag}_s1")
    driver = block.findInst(driver_name)
    net_name = driver.findITerm("X").getNet().getName()
    driver_x, driver_y = driver.getLocation()
    stage_x, stage_y = stage.getLocation()
    insert_buffer(
        net_name,
        stage.getName(),
        "A",
        f"eco4o_{tag}_input_split",
        (driver_x + stage_x) // 2,
        (driver_y + stage_y) // 2,
    )

upper = block.findInst("eco4g_a6_upper")
mid = block.findInst("eco4k_a6_mid")
upper_x, upper_y = upper.getLocation()
mid_x, mid_y = mid.getLocation()
current_net = "eco4g_a6_upper_net"
for split_index in range(1, 4):
    insert_buffer(
        current_net,
        mid.getName(),
        "A",
        f"eco4o_a6_cap_split_{split_index}",
        upper_x + (mid_x - upper_x) * split_index // 4,
        upper_y + (mid_y - upper_y) * split_index // 4,
    )
    current_net = f"eco4o_a6_cap_split_{split_index}_net"

plan = {
    "source": str(source / "soc_top.routed.odb"),
    "original": original,
    "inserted": inserted,
    "movable": sorted(movable),
    "removed_physical": removed_physical,
}
(out / "placement_plan.json").write_text(json.dumps(plan, indent=2) + "\n")
odb.write_db(db, str(out / "soc_top.seed.odb"))
odb.write_def(block, str(out / "soc_top.seed.def"))
print(
    f"Inserted {len(inserted)} cells; movable colliders {len(movable)}; "
    f"removed physical-only {len(removed_physical)}"
)
print("Movable:", " ".join(sorted(movable)))
