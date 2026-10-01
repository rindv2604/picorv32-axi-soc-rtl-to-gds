"""Compact the failing SRAM chains and split one long capacitive branch."""

import json
import math
import os
from pathlib import Path

import odb


root = Path(__file__).resolve().parents[2]
source = Path(os.environ["ECO4O_SOURCE_DIR"])
out = Path(os.environ["ECO4O_ITER_DIR"])
out.mkdir(parents=True, exist_ok=True)

db = odb.dbDatabase.create()
odb.read_db(db, str(source / "soc_top.routed.odb"))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()
macro = block.findInst("ram.u_sram_macro")
rows = list(block.getRows())


def rect(inst):
    box = inst.getBBox()
    return box.xMin(), box.yMin(), box.xMax(), box.yMax()


def signal_nets(inst):
    return {
        iterm.getNet().getName()
        for iterm in inst.getITerms()
        if iterm.getNet() is not None and iterm.getSigType() == "SIGNAL"
    }


original = {
    inst.getName(): {
        "location": inst.getLocation(),
        "orient": str(inst.getOrient()),
        "status": str(inst.getPlacementStatus()),
        "cell": inst.getMaster().getName(),
    }
    for inst in block.getInsts()
}

target_pins = [f"addr0[{i}]" for i in range(1, 8)]
target_instances = set()
target_plan = []
target_boxes = []
used_rows = set()


def is_clock_instance(inst):
    return inst.getName().startswith(("clkbuf", "clkload")) or any(
        iterm.getNet() is not None and iterm.getNet().getSigType() == "CLOCK"
        for iterm in inst.getITerms()
    )


unavoidable = [
    (inst.getName(), rect(inst))
    for inst in block.getInsts()
    if inst.isBlock()
    or inst.getMaster().getType() == "CORE_WELLTAP"
    or is_clock_instance(inst)
]


def aligned_x(row, desired):
    box = row.getBBox()
    step = row.getSpacing()
    return box.xMin() + round((desired - box.xMin()) / step) * step


def select_group(instances, target_y, mode, target_x=None):
    width = sum(inst.getMaster().getWidth() for inst in instances)
    candidates = []
    for row in rows:
        box = row.getBBox()
        key = (box.xMin(), box.xMax(), box.yMin())
        if (
            row.getSite().getHeight() != 2720
            or row.getSpacing() <= 0
            or key in used_rows
            or (
                target_x is not None
                and mode != "anchor"
                and not (box.xMin() <= target_x < box.xMax())
            )
        ):
            continue
        if mode == "left":
            start_x = box.xMin()
        elif mode == "right":
            start_x = box.xMax() - width
        elif mode == "anchor":
            start_x = aligned_x(row, target_x)
        else:
            raise RuntimeError(f"Unknown placement mode {mode}")
        if start_x < box.xMin() or start_x + width > box.xMax():
            continue
        planned = []
        x = start_x
        blocked = False
        for inst in instances:
            candidate = (x, box.yMin(), x + inst.getMaster().getWidth(), box.yMax())
            if any(
                candidate[0] < fixed[2]
                and candidate[2] > fixed[0]
                and candidate[1] < fixed[3]
                and candidate[3] > fixed[1]
                for _, fixed in unavoidable
            ) or any(
                candidate[0] < fixed[2]
                and candidate[2] > fixed[0]
                and candidate[1] < fixed[3]
                and candidate[3] > fixed[1]
                for fixed in target_boxes
            ):
                blocked = True
                break
            planned.append((inst, x))
            x += inst.getMaster().getWidth()
        if not blocked:
            candidates.append(
                (
                    abs(box.yMin() + 1360 - target_y),
                    abs((start_x + width / 2) - (target_x or start_x + width / 2)),
                    row,
                    planned,
                )
            )
    if not candidates:
        raise RuntimeError(f"No legal reserved row for {[i.getName() for i in instances]}")
    _, _, row, planned = min(candidates, key=lambda item: (item[0], item[1]))
    box = row.getBBox()
    used_rows.add((box.xMin(), box.xMax(), box.yMin()))
    return row, planned


for pin_name in target_pins:
    tag = pin_name.replace("[", "_").replace("]", "")
    sink = macro.findITerm(pin_name)
    _, sink_x, sink_y = sink.getAvgXY()
    chain = [block.findInst(f"eco4o_{tag}_s{i}") for i in range(1, 5)]
    input_net = chain[0].findITerm("A").getNet()
    drivers = [iterm for iterm in input_net.getITerms() if iterm.getIoType() == "OUTPUT"]
    if len(drivers) != 1:
        raise RuntimeError(f"Expected one original driver for {pin_name}")
    original_driver = drivers[0].getInst()
    ordered = [original_driver] + chain
    if pin_name.startswith("addr0"):
        channel_x = int(660 * dbu)
        final_row, final_plan = select_group(
            ordered[3:], sink_y, "right", channel_x
        )
        input_row, input_plan = select_group(
            ordered[:3], sink_y, "left", channel_x
        )
        groups = [(final_row, final_plan), (input_row, input_plan)]
    else:
        # The addr1[6] pin is on the lower edge. Use the unobstructed row below it
        # and lay the logical chain right-to-left so the last output is closest.
        final_output_offset = 10.35 * dbu
        row, planned = select_group(
            list(reversed(ordered)),
            int(397.12 * dbu),
            "anchor",
            sink_x - final_output_offset,
        )
        groups = [(row, planned)]

    for row, planned in groups:
        y = row.getBBox().yMin()
        for inst, x in planned:
            inst.setOrient(str(row.getOrient()))
            inst.setLocation(x, y)
            inst.setPlacementStatus("FIRM")
            target_instances.add(inst.getName())
            target_boxes.append(rect(inst))
            target_plan.append(
                {
                    "pin": pin_name,
                    "instance": inst.getName(),
                    "cell": inst.getMaster().getName(),
                    "location": [x, y],
                    "orient": str(row.getOrient()),
                }
            )
            x += inst.getMaster().getWidth()

# Split the 228-um eco4g_a6_upper -> eco4k_a6_mid branch.
upper_net = block.findNet("eco4g_a6_upper_net")
mid = block.findInst("eco4k_a6_mid")
mid_a = mid.findITerm("A")
if mid_a.getNet() is None or mid_a.getNet().getName() != upper_net.getName():
    raise RuntimeError("Unexpected eco4g_a6_upper topology")
split = odb.dbInst_create(
    block,
    db.findMaster("sky130_fd_sc_hd__buf_6"),
    "eco4o_a6_cap_split",
)
split_net = odb.dbNet_create(block, "eco4o_a6_cap_split_net")
mid_a.disconnect()
mid_a.connect(split_net)
split.findITerm("A").connect(upper_net)
split.findITerm("X").connect(split_net)
for pin, net_name in [
    ("VPWR", "VPWR"),
    ("VPB", "VPWR"),
    ("VGND", "VGND"),
    ("VNB", "VGND"),
]:
    split.findITerm(pin).connect(block.findNet(net_name))
split_row, split_plan = select_group(
    [split], int(535.0 * dbu), "anchor", int(664.0 * dbu)
)
_, split_x = split_plan[0]
split_y = split_row.getBBox().yMin()
split.setOrient(str(split_row.getOrient()))
split.setLocation(split_x, split_y)
split.setPlacementStatus("FIRM")
target_instances.add(split.getName())
target_boxes.append(rect(split))
target_plan.append(
    {
        "pin": "eco4g_a6_upper_net",
        "instance": split.getName(),
        "cell": split.getMaster().getName(),
        "location": [split_x, split_y],
        "orient": str(split_row.getOrient()),
    }
)

# Repack only data cells in the local regions needed by the reserved chains.
movable = set()
removed_physical = []
for inst in list(block.getInsts()):
    if inst.getName() in target_instances or inst.isBlock():
        continue
    box = rect(inst)
    local = any(
        box[0] < target[2] + 20 * dbu
        and box[2] > target[0] - 20 * dbu
        and box[1] < target[3] + 8 * dbu
        and box[3] > target[1] - 8 * dbu
        for target in target_boxes
    )
    if not local:
        inst.setPlacementStatus("FIRM")
        continue
    master = inst.getMaster()
    if master.getType() == "CORE_SPACER" or "__decap_" in master.getName():
        removed_physical.append(
            {
                "instance": inst.getName(),
                "cell": master.getName(),
                "location": inst.getLocation(),
            }
        )
        odb.dbInst.destroy(inst)
        continue
    if master.getType() == "CORE_WELLTAP" or is_clock_instance(inst):
        inst.setPlacementStatus("FIRM")
        continue
    inst.setPlacementStatus("PLACED")
    movable.add(inst.getName())

plan = {
    "source": str(source / "soc_top.routed.odb"),
    "original": original,
    "target_plan": target_plan,
    "target_instances": sorted(target_instances),
    "movable": sorted(movable),
    "removed_physical": removed_physical,
    "inserted": [split.getName()],
}
(out / "placement_plan.json").write_text(json.dumps(plan, indent=2))
odb.write_db(db, str(out / "soc_top.seed.odb"))
print(
    "Reserved",
    len(target_instances),
    "instances; movable",
    len(movable),
    "removed fillers/decaps",
    len(removed_physical),
)
