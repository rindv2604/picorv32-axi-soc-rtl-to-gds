"""Generate Tcl that reapplies a reference ECO while GRT's listener is active."""

import os
from pathlib import Path

import odb


base_path = Path(os.environ["ECO4O_BASE_ODB"])
eco_path = Path(os.environ["ECO4O_REFERENCE_ODB"])
output = Path(os.environ["ECO4O_APPLY_TCL"])


def load(path):
    db = odb.dbDatabase.create()
    odb.read_db(db, str(path))
    return db, db.getChip().getBlock()


def braced(value):
    return "{" + str(value).replace("}", "\\}") + "}"


base_db, base = load(base_path)
eco_db, eco = load(eco_path)
base_insts = {inst.getName(): inst for inst in base.getInsts()}
eco_insts = {inst.getName(): inst for inst in eco.getInsts()}
base_nets = {net.getName(): net for net in base.getNets()}
eco_nets = {net.getName(): net for net in eco.getNets()}

removed = sorted(set(base_insts) - set(eco_insts))
inserted = sorted(set(eco_insts) - set(base_insts))
moved = []
for name in sorted(set(base_insts) & set(eco_insts)):
    old = base_insts[name]
    new = eco_insts[name]
    if (
        old.getLocation() != new.getLocation()
        or str(old.getOrient()) != str(new.getOrient())
        or old.getMaster().getName() != new.getMaster().getName()
    ):
        moved.append(name)

new_nets = sorted(set(eco_nets) - set(base_nets))
changed_connections = []
for name in sorted(set(base_insts) & set(eco_insts)):
    old = base_insts[name]
    new = eco_insts[name]
    old_pins = {
        iterm.getMTerm().getName(): (
            iterm.getNet().getName() if iterm.getNet() is not None else None
        )
        for iterm in old.getITerms()
    }
    for iterm in new.getITerms():
        pin = iterm.getMTerm().getName()
        new_net = iterm.getNet().getName() if iterm.getNet() is not None else None
        if old_pins.get(pin) != new_net:
            changed_connections.append((name, pin, new_net))

lines = [
    "set block [ord::get_db_block]",
    "set db [ord::get_db]",
]
for name in removed:
    lines.append(f"odb::dbInst_destroy [$block findInst {braced(name)}]")
for net_name in new_nets:
    lines.append(f"odb::dbNet_create $block {braced(net_name)}")
for name in inserted:
    inst = eco_insts[name]
    master = inst.getMaster().getName()
    x, y = inst.getLocation()
    lines.extend(
        [
            f"set inst [odb::dbInst_create $block [$db findMaster {braced(master)}] {braced(name)}]",
            "$inst setPlacementStatus PLACED",
            f"$inst setOrient {braced(str(inst.getOrient()))}",
            f"$inst setLocation {x} {y}",
            f"$inst setPlacementStatus {braced(str(inst.getPlacementStatus()))}",
        ]
    )
for name in moved:
    inst = eco_insts[name]
    x, y = inst.getLocation()
    lines.append(f"set inst [$block findInst {braced(name)}]")
    if base_insts[name].getMaster().getName() != inst.getMaster().getName():
        lines.append(
            f"$inst swapMaster [$db findMaster {braced(inst.getMaster().getName())}]"
        )
    lines.extend(
        [
            "$inst setPlacementStatus PLACED",
            f"$inst setOrient {braced(str(inst.getOrient()))}",
            f"$inst setLocation {x} {y}",
            f"$inst setPlacementStatus {braced(str(inst.getPlacementStatus()))}",
        ]
    )
for name, pin, net_name in changed_connections:
    lines.extend(
        [
            f"set iterm [[$block findInst {braced(name)}] findITerm {braced(pin)}]",
            "$iterm disconnect",
        ]
    )
    if net_name is not None:
        lines.append(f"$iterm connect [$block findNet {braced(net_name)}]")
for name in inserted:
    inst = eco_insts[name]
    for iterm in inst.getITerms():
        net = iterm.getNet()
        if net is None:
            continue
        pin = iterm.getMTerm().getName()
        lines.append(
            f"[[$block findInst {braced(name)}] findITerm {braced(pin)}] "
            f"connect [$block findNet {braced(net.getName())}]"
        )

lines.append(
    f'puts "ECO4O_INCREMENTAL_APPLY moved={len(moved)} inserted={len(inserted)} '
    f'removed={len(removed)} new_nets={len(new_nets)} changed_connections={len(changed_connections)}"'
)
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text("\n".join(lines) + "\n")
print(lines[-1])
