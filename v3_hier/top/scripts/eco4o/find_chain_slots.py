"""Report legal free intervals beside the SRAM after removing addr0 ECO cells."""

import os
from pathlib import Path

import odb


odb_path = Path(os.environ["ECO4O_INPUT_ODB"])
db = odb.dbDatabase.create()
odb.read_db(db, str(odb_path))
block = db.getChip().getBlock()
dbu = block.getDbUnitsPerMicron()


def is_removable(inst):
    master = inst.getMaster()
    return (
        inst.getName().startswith("eco4o_addr0_")
        or master.getType() == "CORE_SPACER"
        or "__decap_" in master.getName()
    )


masters = [
    db.findMaster("sky130_fd_sc_hd__clkinv_4"),
    db.findMaster("sky130_fd_sc_hd__clkinv_8"),
    db.findMaster("sky130_fd_sc_hd__clkinv_16"),
    db.findMaster("sky130_fd_sc_hd__clkinv_16"),
]
print("CHAIN_WIDTH_UM", sum(master.getWidth() for master in masters) / dbu)

for row in sorted(block.getRows(), key=lambda item: item.getBBox().yMin()):
    row_box = row.getBBox()
    if not (500 * dbu <= row_box.yMin() <= 620 * dbu):
        continue
    if not (row_box.xMin() == 645840 and row_box.xMax() == 669760):
        continue
    occupied = []
    for inst in block.getInsts():
        if is_removable(inst):
            continue
        box = inst.getBBox()
        if (
            box.xMin() < row_box.xMax()
            and box.xMax() > row_box.xMin()
            and box.yMin() < row_box.yMax()
            and box.yMax() > row_box.yMin()
        ):
            occupied.append(
                (max(box.xMin(), row_box.xMin()), min(box.xMax(), row_box.xMax()), inst)
            )
    occupied.sort(key=lambda item: item[0])
    cursor = row_box.xMin()
    free = []
    for x_min, x_max, _ in occupied:
        if x_min > cursor:
            free.append((cursor, x_min))
        cursor = max(cursor, x_max)
    if cursor < row_box.xMax():
        free.append((cursor, row_box.xMax()))
    print(
        "ROW",
        row_box.yMin() / dbu,
        str(row.getOrient()),
        "FREE",
        [(a / dbu, b / dbu, (b - a) / dbu) for a, b in free],
        "BLOCKED",
        [
            (a / dbu, b / dbu, inst.getName(), inst.getMaster().getName())
            for a, b, inst in occupied
        ],
    )

print("ADDR1_WINDOW")
window_x_min = 1060 * dbu
window_x_max = 1130 * dbu
for row in sorted(block.getRows(), key=lambda item: item.getBBox().yMin()):
    row_box = row.getBBox()
    if not (375 * dbu <= row_box.yMin() <= 415 * dbu):
        continue
    if row_box.xMin() > window_x_min or row_box.xMax() < window_x_max:
        continue
    occupied = []
    for inst in block.getInsts():
        master = inst.getMaster()
        removable = (
            inst.getName().startswith("eco4o_addr1_6_")
            or master.getType() == "CORE_SPACER"
            or "__decap_" in master.getName()
        )
        if removable:
            continue
        box = inst.getBBox()
        if (
            box.xMin() < window_x_max
            and box.xMax() > window_x_min
            and box.yMin() < row_box.yMax()
            and box.yMax() > row_box.yMin()
        ):
            occupied.append(
                (max(box.xMin(), window_x_min), min(box.xMax(), window_x_max), inst)
            )
    occupied.sort(key=lambda item: item[0])
    cursor = window_x_min
    free = []
    for x_min, x_max, _ in occupied:
        if x_min > cursor:
            free.append((cursor, x_min))
        cursor = max(cursor, x_max)
    if cursor < window_x_max:
        free.append((cursor, window_x_max))
    print(
        "ROW",
        row_box.yMin() / dbu,
        str(row.getOrient()),
        "FREE",
        [(a / dbu, b / dbu, (b - a) / dbu) for a, b in free],
        "BLOCKED",
        [
            (a / dbu, b / dbu, inst.getName(), inst.getMaster().getName())
            for a, b, inst in occupied
        ],
    )
