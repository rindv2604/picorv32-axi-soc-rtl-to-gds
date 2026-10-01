# ECO4O Frozen State

## Frozen revision

`top_newcpu_eco4o_19` is the final physical candidate. It was frozen after
refill, RC extraction, nine-corner STA, placement and PG checks, DRT and antenna
checks. No optimization or routing change was made after the freeze point.

## Acceptance status

| Check | ECO19 result | Evidence |
|---|---:|---|
| Worst setup WNS | +1.604269 ns | `results/final/timing/summary.json` |
| Worst hold WNS | +0.089287 ns | `results/final/timing/summary.json` |
| Setup violations | 0 | nine-corner STA |
| Hold violations | 0 | nine-corner STA |
| Max-cap violations | 0 | nine-corner STA |
| Max-slew violations | 0 | nine-corner STA |
| Worst SRAM slew | 0.039473 ns | `max_ss_100C_1v60`, limit 0.040000 ns |
| DRT markers | 0 | `results/final/signoff/drt.drc` |
| Antenna violating nets/pins | 0 / 0 | `results/final/signoff/antenna.openroad.log` |
| KLayout DRC errors | 0 | `results/final/signoff/drc.klayout.json` |
| Magic illegal overlaps | 0 | `results/final/signoff/metrics.json` |
| LVS errors | 0 | `results/final/signoff/lvs.netgen.rpt` |

The 18 Magic illegal-overlap errors reported in an earlier revision are absent
from ECO19. The final metric is zero.

## Nine-corner timing

| Corner | Setup WNS (ns) | Hold WNS (ns) | Setup/Hold/Cap/Slew violations |
|---|---:|---:|---:|
| `nom_tt_025C_1v80` | 9.377040 | 0.293410 | 0 / 0 / 0 / 0 |
| `nom_ss_100C_1v60` | 1.899060 | 0.834145 | 0 / 0 / 0 / 0 |
| `nom_ff_n40C_1v95` | 9.407059 | 0.091921 | 0 / 0 / 0 / 0 |
| `min_tt_025C_1v80` | 9.368733 | 0.297375 | 0 / 0 / 0 / 0 |
| `min_ss_100C_1v60` | 2.109308 | 0.829444 | 0 / 0 / 0 / 0 |
| `min_ff_n40C_1v95` | 9.407776 | 0.093988 | 0 / 0 / 0 / 0 |
| `max_tt_025C_1v80` | 9.375279 | 0.289233 | 0 / 0 / 0 / 0 |
| `max_ss_100C_1v60` | 1.604269 | 0.839239 | 0 / 0 / 0 / 0 |
| `max_ff_n40C_1v95` | 9.391746 | 0.089287 | 0 / 0 / 0 / 0 |

## Final deliverables

All paths are relative to this directory.

| View | File | SHA-256 |
|---|---|---|
| ODB | `results/final/soc_top.eco4o.odb` | `e1853eea3031b47ae5e87817494676ac747a0615915f5248ae207c83553c3867` |
| DEF | `results/final/soc_top.eco4o.def` | `f82fd321961291eca90c903d25d33f3e051683cb4360f12f4c9a88e09f2fc506` |
| Verilog | `results/final/soc_top.eco4o.nl.v` | `00a4c5e58cb5c87d4d209a8f18852729c0007df5dc99d92bea5ff53486c11ba1` |
| Power netlist | `results/final/soc_top.eco4o.pnl.v` | `825fe02a7a29a78fb755627aac969c165926ff10d773522f6136b90b63525da8` |
| GDS | `results/final/soc_top.gds` | `13a155e5e76090a9fa94cb5d2507b5681f9c30ffd6c78ee532678321f1b79815` |
| Extracted SPICE | `results/final/soc_top.spice` | `d42a0d3e7112607e0edc57abf62175594afaaac5ec6fa788f34f91d50d1e0bc1` |
| Nominal SPEF | `results/final/soc_top.nom.spef` | see `reports/final_artifacts.sha256` |
| Minimum SPEF | `results/final/soc_top.min.spef` | see `reports/final_artifacts.sha256` |
| Maximum SPEF | `results/final/soc_top.max.spef` | see `reports/final_artifacts.sha256` |

The ODB, DEF, Verilog, PNL, and all SPEFs are direct ECO19 outputs. The GDS is
streamed from the ECO19 DEF. Magic extracted the SPICE from that GDS.

## LVS lineage

The exact pre-LVS source declaration is in `reports/eco19_lvs_sources.txt` and
the source hashes are in `reports/eco19_source_hashes.sha256`. Netgen compared
the ECO19-derived GDS/SPICE against the PNL exported from ECO19. No ECO4H
logical netlist was used. Both sides contain 1,802 devices and 1,828 nets;
Netgen reports `Circuits match uniquely`.

## Baseline protection

The ECO4M baseline remains unchanged:

- ODB SHA-256: `9113c53236d8f62f0f163cd5dde525fc373523dbfcd5b83b47826beaa06948ae`
- DEF SHA-256: `75468679f1c47b8b193dc09b9fb44bb1eec0f8ac7d804cb0c1f614c429700dc3`

Any later physical change requires a new revision name and complete rerun of
RC extraction, nine-corner STA, DRT, antenna, foundry DRC, Magic overlap, and
LVS.

STATUS = CLEAN
