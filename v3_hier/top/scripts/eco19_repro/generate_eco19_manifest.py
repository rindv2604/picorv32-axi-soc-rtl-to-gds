#!/usr/bin/env python3
"""Generate the frozen ECO19 replay manifests from the reference ODB and DEF.

This is an audit-time generator.  The LibreLane flow never runs it and never
opens a complete ECO19 ODB, DEF, GDS, or netlist.  Its generated Tcl and
route-only donor are explicit accepted-ECO manifests consumed by the
reproduction flow.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import odb


HERE = Path(__file__).resolve().parent
TOP = HERE.parent.parent
REFERENCE = TOP / "eco4o_slewfix/results/final/soc_top.eco4o.ll301_compat.odb"
REFERENCE_DEF = TOP / "eco4o_slewfix/results/final/soc_top.eco4o.def"
REPRO_BASELINE_DEF = (
    TOP / "runs/top_newcpu_eco19_full_repro_v2_50mhz/46-openroad-detailedrouting/soc_top.def"
)
TCL_OUT = HERE / "eco19_manifest.tcl"
JSON_OUT = HERE / "eco19_manifest.json"
ROUTE_DEF_OUT = HERE / "eco19_routes.def"
ROUTE_ODB_OUT = HERE / "eco19_route_donor.odb"

ACCEPTED_CHECKPOINTS = [
    ("ECO4B", TOP / "eco4b_branch_work/soc_top.branch.odb"),
    ("ECO4C", TOP / "eco4c_branch_work/soc_top.eco4c.odb"),
    ("ECO4E", TOP / "eco4e_move_addr_branches/soc_top.eco4e.odb"),
    ("ECO4F", TOP / "eco4f_branch_data_21_12_13/soc_top.eco4f.odb"),
    ("ECO4G", TOP / "eco4g_bulk10/soc_top.eco4g.odb"),
    ("ECO4H", TOP / "eco4h_cpu_valid_buffers/soc_top.eco4h.odb"),
    ("ECO4I", TOP / "eco4i_clean_reroute/soc_top.eco4i_unrouted.odb"),
    ("ECO4J", TOP / "eco4j_surgical_route/soc_top.eco4j_drt_v2.odb"),
    ("ECO4K", TOP / "eco4k_capfix/soc_top.eco4k_drt_v2.odb"),
    ("ECO4L", TOP / "eco4l_clockcapfix/soc_top.eco4l_drt.odb"),
    ("ECO4M", TOP / "eco4m_antennafix/soc_top.eco4m_drt.odb"),
    ("ECO19", REFERENCE),
]

ECO19_MODIFIED_ORIGINALS = {
    "ANTENNA_121",
    "_0964_",
    "_0965_",
    "_0967_",
    "_0968_",
    "_0971_",
    "_0972_",
    "_0975_",
    "_1174_",
    "_1222_",
    "_1243_",
    "hold181",
    "wire187",
    "wire190",
    "wire192",
    "wire193",
    "wire204",
    "wire65",
    "wire66",
}


def is_accepted_eco_instance(name: str, master: str) -> bool:
    if name.startswith("eco4o_fill_"):
        return False
    if name.startswith("eco"):
        return "__fill_" not in master and "__decap_" not in master
    # A clean Classic run through DetailedRouting contains ANTENNA_1..281.
    # The frozen ECO19 database adds ANTENNA_282..313.  These 32 diodes are
    # therefore part of the complete accepted physical delta, even though
    # only ANTENNA_306..313 were introduced during the last named ECO step.
    antenna_match = re.fullmatch(r"ANTENNA_(\d+)", name)
    return antenna_match is not None and 282 <= int(antenna_match.group(1)) <= 313


def brace(value: object) -> str:
    # OpenDB bus names already contain Tcl's literal backslash before '['/']'.
    # Braced Tcl words preserve that spelling, so backslashes must not double.
    text = str(value).replace("}", "\\}")
    return "{" + text + "}"


def endpoint_key(endpoint: dict[str, str]) -> tuple[str, str, str]:
    return (
        endpoint["kind"],
        endpoint.get("instance", ""),
        endpoint.get("pin", endpoint.get("port", "")),
    )


def checkpoint_masters(path: Path) -> dict[str, str]:
    database = odb.dbDatabase.create()
    odb.read_db(database, str(path))
    block = database.getChip().getBlock()
    result = {}
    for inst in block.getInsts():
        master = inst.getMaster().getName()
        if "__fill_" in master or "__decap_" in master:
            continue
        result[inst.getName()] = master
    return result


def read_def_net_entries(path: Path) -> dict[str, str]:
    """Return complete NETS entries indexed by their escaped DEF net name."""
    entries: dict[str, str] = {}
    in_nets = False
    current_name: str | None = None
    current_lines: list[str] = []

    for line in path.read_text().splitlines(keepends=True):
        if not in_nets:
            if re.fullmatch(r"NETS\s+\d+\s*;\s*\n?", line):
                in_nets = True
            continue
        if re.fullmatch(r"END NETS\s*\n?", line):
            break

        if current_name is None:
            match = re.match(r"\s*-\s+(\S+)", line)
            if match is None:
                continue
            current_name = match.group(1)
            current_lines = [line]
        else:
            current_lines.append(line)

        if line.rstrip().endswith(";"):
            entries[current_name] = "".join(current_lines)
            current_name = None
            current_lines = []

    return entries


def read_def_component_masters(path: Path) -> dict[str, str]:
    """Return COMPONENT instance/master pairs from a routed DEF."""
    components: dict[str, str] = {}
    in_components = False
    for line in path.read_text().splitlines():
        if not in_components:
            if re.fullmatch(r"COMPONENTS\s+\d+\s*;", line):
                in_components = True
            continue
        if line == "END COMPONENTS":
            break
        match = re.match(r"\s*-\s+(\S+)\s+(\S+)", line)
        if match is not None:
            components[match.group(1)] = match.group(2)
    return components


def is_spacer_master(master: str) -> bool:
    return "__fill_" in master or "__decap_" in master


def route_clause(entry: str) -> str:
    marker = entry.find("+ ROUTED")
    return entry[marker:] if marker >= 0 else ""


def extract_route_delta() -> tuple[str, list[str]]:
    """Create a DEF containing every route that differs from stage-46 PNR."""
    reference_entries = read_def_net_entries(REFERENCE_DEF)
    baseline_entries = read_def_net_entries(REPRO_BASELINE_DEF)
    pg_nets = {"VPWR", "VGND"}
    reference_signal_names = set(reference_entries) - pg_nets
    baseline_signal_names = set(baseline_entries) - pg_nets

    unexpected_baseline_nets = sorted(baseline_signal_names - reference_signal_names)
    if unexpected_baseline_nets:
        raise RuntimeError(
            f"Stage-46 baseline has signal nets absent from ECO19: {unexpected_baseline_nets}"
        )

    route_names = reference_signal_names - baseline_signal_names
    for name in reference_signal_names & baseline_signal_names:
        if route_clause(reference_entries[name]) != route_clause(baseline_entries[name]):
            route_names.add(name)

    for name in route_names:
        if "+ ROUTED" not in reference_entries[name]:
            raise RuntimeError(f"Frozen ECO19 route-delta net {name} has no route")

    sorted_route_names = sorted(route_names)
    body = "".join(reference_entries[name] for name in sorted_route_names)
    route_def = (
        "# Generated by generate_eco19_manifest.py; do not edit by hand.\n"
        "VERSION 5.8 ;\n"
        'DIVIDERCHAR "/" ;\n'
        'BUSBITCHARS "[]" ;\n'
        "DESIGN soc_top ;\n"
        "UNITS DISTANCE MICRONS 1000 ;\n"
        f"NETS {len(sorted_route_names)} ;\n"
        f"{body}"
        "END NETS\n"
        "END DESIGN\n"
    )
    return route_def, sorted_route_names


def main() -> None:
    database = odb.dbDatabase.create()
    odb.read_db(database, str(REFERENCE))
    block = database.getChip().getBlock()

    eco_cells = []
    selected_names = set()
    for inst in block.getInsts():
        name = inst.getName()
        master = inst.getMaster().getName()
        if not is_accepted_eco_instance(name, master):
            continue
        selected_names.add(name)
        eco_cells.append(
            {
                "name": name,
                "master": master,
                "x": inst.getLocation()[0],
                "y": inst.getLocation()[1],
                "orient": str(inst.getOrient()),
                "reference_status": str(inst.getPlacementStatus()),
                "replay_status": "FIRM",
            }
        )

    original_cells = []
    for name in sorted(ECO19_MODIFIED_ORIGINALS):
        inst = block.findInst(name)
        if inst is None:
            raise RuntimeError(f"Frozen ECO19 is missing required original instance {name}")
        original_cells.append(
            {
                "name": name,
                "master": inst.getMaster().getName(),
                "x": inst.getLocation()[0],
                "y": inst.getLocation()[1],
                "orient": str(inst.getOrient()),
                "reference_status": str(inst.getPlacementStatus()),
                "replay_status": "FIRM",
            }
        )

    affected_names = set()
    for name in selected_names:
        for iterm in block.findInst(name).getITerms():
            net = iterm.getNet()
            if net is not None and net.getName() not in {"VPWR", "VGND"}:
                affected_names.add(net.getName())

    affected_nets = []
    required_anchor_instances = set()
    for net_name in sorted(affected_names):
        net = block.findNet(net_name)
        endpoints = []
        for bterm in net.getBTerms():
            endpoints.append({"kind": "B", "port": bterm.getName()})
        for iterm in net.getITerms():
            instance = iterm.getInst().getName()
            pin = iterm.getMTerm().getName()
            endpoints.append({"kind": "I", "instance": instance, "pin": pin})
            if instance not in selected_names:
                required_anchor_instances.add(instance)
        endpoints.sort(key=endpoint_key)
        affected_nets.append({"name": net_name, "endpoints": endpoints})

    resize_events = []
    prior_label, prior_path = ACCEPTED_CHECKPOINTS[0]
    prior_masters = checkpoint_masters(prior_path)
    for label, path in ACCEPTED_CHECKPOINTS[1:]:
        current_masters = checkpoint_masters(path)
        for name in sorted(prior_masters.keys() & current_masters.keys()):
            before = prior_masters[name]
            after = current_masters[name]
            if before != after:
                resize_events.append(
                    {
                        "instance": name,
                        "from_master": before,
                        "to_master": after,
                        "transition": f"{prior_label}->{label}",
                    }
                )
        prior_label = label
        prior_masters = current_masters

    eco_cells.sort(key=lambda item: item["name"])
    original_cells.sort(key=lambda item: item["name"])

    # The current full-flow baseline contains 266 extra PHY_EDGE decap_3
    # spacers that are absent from the accepted ECO19 implementation.  Record
    # their exact instance names so the replay removes only that audited delta.
    reference_components = read_def_component_masters(REFERENCE_DEF)
    baseline_components = read_def_component_masters(REPRO_BASELINE_DEF)
    reference_spacers = {
        name: master
        for name, master in reference_components.items()
        if is_spacer_master(master)
    }
    baseline_spacers = {
        name: master
        for name, master in baseline_components.items()
        if is_spacer_master(master)
    }
    retained_spacer_mismatches = sorted(
        name
        for name in reference_spacers.keys() & baseline_spacers.keys()
        if reference_spacers[name] != baseline_spacers[name]
    )
    if retained_spacer_mismatches:
        raise RuntimeError(
            "Retained spacer master mismatch: " + str(retained_spacer_mismatches)
        )
    removed_spacers = sorted(baseline_spacers.keys() - reference_spacers.keys())
    unexpected_removed_spacers = [
        name
        for name in removed_spacers
        if not name.startswith("PHY_EDGE_")
        or baseline_spacers[name] != "sky130_fd_sc_hd__decap_3"
    ]
    if unexpected_removed_spacers:
        raise RuntimeError(
            "Unexpected baseline-only spacer delta: "
            + str(unexpected_removed_spacers)
        )
    final_refill_count = len(reference_spacers.keys() - baseline_spacers.keys())

    route_def, route_net_names = extract_route_delta()
    ROUTE_DEF_OUT.write_text(route_def)

    # Build a schema-compatible donor database containing route geometry only.
    # There are no instances or ports, so this cannot substitute for a design
    # checkpoint; route_eco19.tcl can only append its dbWires to existing nets.
    route_net_name_set = set(route_net_names)
    for inst in list(block.getInsts()):
        odb.dbInst.destroy(inst)
    for bterm in list(block.getBTerms()):
        odb.dbBTerm.destroy(bterm)
    for net in list(block.getNets()):
        if net.getName() not in route_net_name_set:
            odb.dbNet.destroy(net)
    missing_route_wires = sorted(
        name
        for name in route_net_names
        if block.findNet(name) is None or block.findNet(name).getWire() is None
    )
    if missing_route_wires:
        raise RuntimeError(f"Route donor is missing dbWires: {missing_route_wires}")
    if block.getInsts() or block.getBTerms():
        raise RuntimeError("Route donor unexpectedly retains instances or ports")
    odb.write_db(database, str(ROUTE_ODB_OUT))

    manifest = {
        "format": "eco19-repro-manifest-v2",
        "reference_sha256": hashlib.sha256(REFERENCE.read_bytes()).hexdigest(),
        "reference_def_sha256": hashlib.sha256(REFERENCE_DEF.read_bytes()).hexdigest(),
        "repro_baseline_def_sha256": hashlib.sha256(
            REPRO_BASELINE_DEF.read_bytes()
        ).hexdigest(),
        "accepted_eco_cell_count": len(eco_cells),
        "accepted_eco_master_counts": dict(
            sorted(Counter(cell["master"] for cell in eco_cells).items())
        ),
        "modified_original_count": len(original_cells),
        "removed_spacer_count": len(removed_spacers),
        "removed_spacer_instances": removed_spacers,
        "accepted_resize_event_count": len(resize_events),
        "accepted_resize_events": resize_events,
        "affected_net_count": len(affected_nets),
        "required_anchor_instance_count": len(required_anchor_instances),
        "accepted_eco_cells": eco_cells,
        "modified_original_cells": original_cells,
        "affected_nets": affected_nets,
        "required_anchor_instances": sorted(required_anchor_instances),
        "refill": {
            "prefix": "eco4o_fill_",
            "expected_inserted_count": final_refill_count,
            "expected_final_instance_count": len(reference_components),
            "masters": [
                "sky130_fd_sc_hd__fill_8",
                "sky130_fd_sc_hd__fill_4",
                "sky130_fd_sc_hd__fill_2",
                "sky130_fd_sc_hd__fill_1",
            ],
        },
        "routing": {
            "mode": (
                "route-only dbWire replay followed by bounded deterministic "
                "TritonRoute cleanup and DRC validation"
            ),
            "affected_route_def": ROUTE_DEF_OUT.name,
            "route_delta_net_count": len(route_net_names),
            "affected_route_def_sha256": hashlib.sha256(
                route_def.encode("utf8")
            ).hexdigest(),
            "route_donor_odb": ROUTE_ODB_OUT.name,
            "route_donor_odb_sha256": hashlib.sha256(
                ROUTE_ODB_OUT.read_bytes()
            ).hexdigest(),
            "route_donor_instance_count": 0,
            "route_donor_port_count": 0,
        },
        "accepted_checkpoint_chain": [label for label, _ in ACCEPTED_CHECKPOINTS],
    }
    JSON_OUT.write_text(json.dumps(manifest, indent=2) + "\n")

    lines = [
        "# Generated by generate_eco19_manifest.py; do not edit by hand.",
        "# Runtime input is this explicit manifest, never a frozen ECO19 design view.",
        f"set ::eco19_manifest_reference_sha256 {brace(manifest['reference_sha256'])}",
        f"set ::eco19_expected_eco_cell_count {len(eco_cells)}",
        f"set ::eco19_expected_affected_net_count {len(affected_nets)}",
        f"set ::eco19_expected_route_net_count {len(route_net_names)}",
        f"set ::eco19_expected_removed_spacer_count {len(removed_spacers)}",
        f"set ::eco19_expected_refill_count {final_refill_count}",
        f"set ::eco19_expected_final_instance_count {len(reference_components)}",
        "set ::eco19_removed_spacers {",
    ]
    for name in removed_spacers:
        lines.append(f"    {brace(name)}")
    lines.extend([
        "}",
        "set ::eco19_cells {",
    ])
    for cell in eco_cells:
        lines.append(
            "    {"
            + " ".join(
                brace(cell[key])
                for key in ("name", "master", "x", "y", "orient", "replay_status")
            )
            + "}"
        )
    lines.extend(["}", "set ::eco19_modified_originals {"])
    for cell in original_cells:
        lines.append(
            "    {"
            + " ".join(
                brace(cell[key])
                for key in ("name", "master", "x", "y", "orient", "replay_status")
            )
            + "}"
        )
    lines.extend(["}", "set ::eco19_required_anchor_instances {"])
    for name in sorted(required_anchor_instances):
        lines.append(f"    {brace(name)}")
    lines.extend(["}", "set ::eco19_affected_nets {"])
    for net in affected_nets:
        endpoint_items = []
        for endpoint in net["endpoints"]:
            if endpoint["kind"] == "I":
                endpoint_items.append(
                    "{" + " ".join(
                        [brace("I"), brace(endpoint["instance"]), brace(endpoint["pin"])]
                    ) + "}"
                )
            else:
                endpoint_items.append(
                    "{" + " ".join([brace("B"), brace(endpoint["port"])]) + "}"
                )
        lines.append(
            "    {" + brace(net["name"]) + " {" + " ".join(endpoint_items) + "}}"
        )
    lines.extend(["}", ""])
    TCL_OUT.write_text("\n".join(lines))
    print(
        f"wrote {TCL_OUT}: {len(eco_cells)} ECO cells, "
        f"{len(original_cells)} original placements/masters, "
        f"{len(removed_spacers)} removed baseline spacers, "
        f"{len(affected_nets)} affected nets, "
        f"{len(route_net_names)} route-delta nets"
    )


if __name__ == "__main__":
    main()
