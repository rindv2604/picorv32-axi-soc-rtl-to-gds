# ECO4O SRAM Slew Closure

## 1. Objective

Close all maximum transition violations at 50 MHz while retaining the real
`0.040 ns` SRAM input limit, preserving setup and hold timing, and producing a
legal, routed, DRC-clean, antenna-clean, LVS-matched physical result. The frozen
result is `top_newcpu_eco4o_19`.

## 2. Starting Baseline

The immutable physical baseline is:

- ODB: `../eco4m_antennafix/soc_top.eco4m_drt.odb`
- DEF: `../eco4m_antennafix/soc_top.eco4m_drt.def`
- ODB SHA-256: `9113c53236d8f62f0f163cd5dde525fc373523dbfcd5b83b47826beaa06948ae`
- DEF SHA-256: `75468679f1c47b8b193dc09b9fb44bb1eec0f8ac7d804cb0c1f614c429700dc3`

Fresh baseline post-route STA gave worst setup WNS `+1.596245 ns`, worst hold
WNS `+0.087601 ns`, zero setup/hold/max-cap violations, and 20 max-slew
violations. The baseline was never overwritten; its final hashes are recorded
in `reports/baseline_final_verify.sha256`.

## 3. Tool and Environment Information

- OpenROAD: `26Q1-1989-g351788d062`
- OpenSTA: `3.0.0 83e1f9b77f`
- LibreLane: `3.0.1`
- PDK: `sky130A`, revision `8afc8346a57fe1ab7934ba5a6056ea8b43078e71`
- Standard cells: `sky130_fd_sc_hd`
- Extraction: OpenRCX `nom`, `min`, and `max` rule sets
- Signoff DRC: KLayout with the sky130A foundry rule deck
- Layout extraction/LVS: Magic and Netgen `1.5.316`

## 4. Source of the 0.040 ns Constraint

The SRAM Liberty model defines `max_transition : 0.04` on the affected
`addr0`, `addr1`, and `wmask0` input pins. This pin limit overrides the looser
top-level SDC transition limit. The SRAM Liberty, LEF, GDS, RTL, and the
`0.040 ns` constraint were not edited or relaxed. The copied final SDC remains
the 50 MHz constraint set.

## 5. Original Violating Pins

All values below are the worst value found over the nine signoff corners.

| SRAM pin | Before (ns) | ECO19 (ns) | Limit (ns) |
|---|---:|---:|---:|
| `ram.u_sram_macro/addr0[0]` | 0.216792 | 0.037114 | 0.040000 |
| `ram.u_sram_macro/addr0[1]` | 0.212742 | 0.036495 | 0.040000 |
| `ram.u_sram_macro/addr0[2]` | 0.231686 | 0.037218 | 0.040000 |
| `ram.u_sram_macro/addr0[3]` | 0.235444 | 0.039473 | 0.040000 |
| `ram.u_sram_macro/addr0[4]` | 0.240744 | 0.036413 | 0.040000 |
| `ram.u_sram_macro/addr0[5]` | 0.260583 | 0.038549 | 0.040000 |
| `ram.u_sram_macro/addr0[6]` | 0.224792 | 0.037270 | 0.040000 |
| `ram.u_sram_macro/addr0[7]` | 0.247311 | 0.036639 | 0.040000 |
| `ram.u_sram_macro/addr1[0]` | 0.235847 | 0.036529 | 0.040000 |
| `ram.u_sram_macro/addr1[1]` | 0.231386 | 0.035955 | 0.040000 |
| `ram.u_sram_macro/addr1[2]` | 0.213500 | 0.038089 | 0.040000 |
| `ram.u_sram_macro/addr1[3]` | 0.211623 | 0.037343 | 0.040000 |
| `ram.u_sram_macro/addr1[4]` | 0.219483 | 0.039415 | 0.040000 |
| `ram.u_sram_macro/addr1[5]` | 0.224291 | 0.038782 | 0.040000 |
| `ram.u_sram_macro/addr1[6]` | 0.237759 | 0.038429 | 0.040000 |
| `ram.u_sram_macro/addr1[7]` | 0.265438 | 0.038914 | 0.040000 |
| `ram.u_sram_macro/wmask0[0]` | 0.219271 | 0.037682 | 0.040000 |
| `ram.u_sram_macro/wmask0[1]` | 0.212785 | 0.037735 | 0.040000 |
| `ram.u_sram_macro/wmask0[2]` | 0.222867 | 0.037003 | 0.040000 |
| `ram.u_sram_macro/wmask0[3]` | 0.227432 | 0.038179 | 0.040000 |

The final worst SRAM input slew is `0.039473 ns` at
`ram.u_sram_macro/addr0[3]` in `max_ss_100C_1v60`, leaving `0.000527 ns` of
margin to the unchanged limit.

## 6. Root Cause Analysis

Each of the 20 SRAM pins was originally driven by a dedicated, fanout-one
`sky130_fd_sc_hd__clkdlybuf4s25_1`. The delay cell output strength, local wire
capacitance, and strict SRAM 10-90% transition requirement produced
`0.211623-0.265438 ns` terminal slews. This was a physical drive and RC problem,
not a false constraint. Direct sizing alone was insufficient at every terminal,
so the final topology uses staged local restoration close to the SRAM pins.

## 7. ECO Strategy

The ECO retained logic polarity by inserting even inverter stages, placed the
strong restoring stages close to the SRAM, and used local input splitting where
long source branches created capacitance pressure. Incremental global routing
notified the router of every connectivity change; TritonRoute then routed and
checked the modified database. Two long AXI write-data nets were split with
`buf_12` cells to remove the final max-cap violations. The final antenna audit
found reroute-induced violations, so ECO18 inserted eight diode cells and
rerouted only five affected nets. ECO19 only refilled the rows and made no logic,
placement, or routing optimization.

## 8. Inserted Cells

Relative to ECO4M, ECO19 contains 113 inserted logical/antenna cells:

| Master | Count | Purpose |
|---|---:|---|
| `sky130_fd_sc_hd__clkinv_4` | 20 | first local restoration stage |
| `sky130_fd_sc_hd__clkinv_8` | 20 | second local restoration stage |
| `sky130_fd_sc_hd__clkinv_16` | 56 | strong terminal and auxiliary restoration stages |
| `sky130_fd_sc_hd__buf_12` | 9 | branch/input splits and max-cap repair |
| `sky130_fd_sc_hd__diode_2` | 8 | final antenna repair |

ECO19 also has 112,496 physical filler cells: 74,080 `fill_8`, 12,489
`fill_4`, 12,652 `fill_2`, and 13,275 `fill_1`. These are physical row-fill
cells and do not alter logical behavior.

## 9. Moved, Replaced, and Removed Cells

Thirty-one original standard-cell instances changed location, orientation, or
master to create legal local sites and close the target nets. The CPU macro and
SRAM macro retained their original masters, locations, and orientations. A total
of 266 original `sky130_fd_sc_hd__decap_3` physical cells were removed while
creating legal ECO sites; the rows were fully refilled in ECO19. The exact names
and master counts are in `reports/eco19_revision_delta.json` and the final
physical audit is in `results/final/signoff/revision_audit.json`.

## 10. ECO Iteration History

| Revision | Result and decision |
|---|---|
| ECO4O-01/02 | Inserted the first four-stage chains; post-route still had 16 slew and 5 cap violations. |
| ECO4O-03..05 | Refined placement around the SRAM; reduced to 8 slew and 4 cap violations. |
| ECO4O-06..09 | Explored chain compaction and route preparation; ECO09 regressed to 29 slew and 9 cap violations and was not selected. |
| ECO4O-10 | Switched to true incremental GRT/DRT; 8 slew, 0 cap. |
| ECO4O-11 | Moved restoring stages closer; 7 slew, 0 cap. |
| ECO4O-12/13 | Upsized the seven limiting restoring stages; 1 marginal slew, 0 cap. |
| ECO4O-14 | Fixed `addr0[1]`; route perturbation left one marginal violation on `addr0[6]`. |
| ECO4O-15 | Relocated the final `addr0[6]` stage; slew became 0, but two long nets violated max cap. |
| ECO4O-16 | Split the two long write-data nets; setup/hold/cap/slew all became 0. |
| ECO4O-17 | Refilled rows and confirmed identical clean nine-corner STA. |
| ECO4O-18 | Inserted eight antenna diodes, rerouted five nets, obtained DRT 0 and antenna 0, and retained clean STA. |
| ECO4O-19 | Refilled the final ECO18 route, repeated extraction and all nine STA corners, then froze the design. |

Every retained candidate was legalized and routed before RC extraction and STA.

## 11. Placement and Legalization

OpenROAD `check_placement -verbose` passes on the final refilled ECO19 ODB.
Both VPWR and VGND pass `check_power_grid`. The audit reports zero bad power
connections, zero signal nets without wire, and zero disconnected-net flags.
The `cpu` and `ram.u_sram_macro` macro checks are unchanged from ECO4M.

## 12. Routing

ECO18 rerouted five antenna-affected nets after inserting the final diodes.
TritonRoute converged from 110 intermediate markers to zero at optimization
iteration 4. ECO19 preserved that routing and added fillers only. The final DRT
marker file `results/final/signoff/drt.drc` is zero bytes and contains zero
markers.

## 13. Parasitics and MMMC Timing

OpenRCX extracted `nom`, `min`, and `max` SPEF directly from the final refilled
ECO19 DEF. OpenSTA then analyzed every RC/PVT combination:

| Corner | Setup WNS (ns) | Hold WNS (ns) | Setup | Hold | Cap | Slew |
|---|---:|---:|---:|---:|---:|---:|
| `nom_tt_025C_1v80` | 9.377040 | 0.293410 | 0 | 0 | 0 | 0 |
| `nom_ss_100C_1v60` | 1.899060 | 0.834145 | 0 | 0 | 0 | 0 |
| `nom_ff_n40C_1v95` | 9.407059 | 0.091921 | 0 | 0 | 0 | 0 |
| `min_tt_025C_1v80` | 9.368733 | 0.297375 | 0 | 0 | 0 | 0 |
| `min_ss_100C_1v60` | 2.109308 | 0.829444 | 0 | 0 | 0 | 0 |
| `min_ff_n40C_1v95` | 9.407776 | 0.093988 | 0 | 0 | 0 | 0 |
| `max_tt_025C_1v80` | 9.375279 | 0.289233 | 0 | 0 | 0 | 0 |
| `max_ss_100C_1v60` | 1.604269 | 0.839239 | 0 | 0 | 0 | 0 |
| `max_ff_n40C_1v95` | 9.391746 | 0.089287 | 0 | 0 | 0 | 0 |

Worst setup WNS is `+1.604269 ns`; worst hold WNS is `+0.089287 ns`. The
complete logs, summary, and final SRAM slew table are under
`results/final/timing/`.

## 14. Physical Verification

Final evidence:

- OpenROAD placement: pass
- VPWR/VGND connectivity: pass
- Signal nets without wire: 0
- Disconnected net flags: 0
- TritonRoute markers: 0
- OpenROAD antenna: 0 violating nets and 0 violating pins
  (`results/final/signoff/antenna.openroad.log`)
- KLayout sky130A foundry DRC: 0 errors
- Magic illegal-overlap count: 0

The previously reported 18 Magic illegal-overlap errors do not exist in ECO19;
the final `Checker.IllegalOverlap` metric is zero. Magic DRC itself was disabled;
the reported full DRC result is the KLayout foundry deck.

## 15. LVS and Revision Lineage

All LVS inputs came from the frozen ECO19 revision:

- ODB source: `iterations/top_newcpu_eco4o_19/soc_top.routed.odb`
- DEF source: `iterations/top_newcpu_eco4o_19/soc_top.routed.def`
- GDS source: `../runs/top_newcpu_eco4o_19_streamout_50mhz/01-klayout-streamout/soc_top.gds`, streamed from the ECO19 DEF
- PNL source: `iterations/top_newcpu_eco4o_19/soc_top.routed.pnl.v`
- Verilog source: `iterations/top_newcpu_eco4o_19/soc_top.routed.v`
- SPICE source: `../runs/top_newcpu_eco4o_19_drc_lvs_50mhz/03-magic-spiceextraction/soc_top.spice`, extracted from the ECO19 GDS

No ECO4H logical netlist was used. Netgen reports `Circuits match uniquely`:
1,802 devices and 1,828 nets on both sides, with zero unmatched devices, nets,
or pins and zero property failures. Exact paths and hashes are in
`reports/eco19_lvs_sources.txt` and `reports/eco19_source_hashes.sha256`.

## 16. Final Artifact Inventory

The frozen deliverables are under `results/final/`:

- `soc_top.eco4o.odb`: refilled, routed ECO19 database
- `soc_top.eco4o.def`: matching ECO19 DEF
- `soc_top.nom.spef`, `soc_top.min.spef`, `soc_top.max.spef`: ECO19 extraction
- `soc_top.eco4o.nl.v`: Verilog exported from ECO19
- `soc_top.eco4o.pnl.v`: power-aware PNL exported from ECO19
- `soc_top.gds`: KLayout streamout from the ECO19 DEF
- `soc_top.spice`: Magic extraction from the ECO19 GDS
- `top_50mhz_eco4o.sdc`: unchanged 50 MHz constraints
- `timing/`: nine STA logs, summary, and final slew table
- `signoff/`: DRT, antenna, KLayout DRC, Magic-overlap metric, LVS, and audit reports

`reports/final_artifacts.sha256` hashes every final deliverable.

## 17. Scripts Used

The reusable scripts are in `../scripts/eco4o/`. The main closure path uses:

- `generate_incremental_eco.py` and `eco4o_incremental_route.tcl`
- `place_upsized_restoring_stage.py`, `upsize_addr0_1_stage.py`, and `move_addr0_6_final.py`
- `split_cap_nets.py`
- `eco4o_repair_antennas.tcl` and `eco4o_antenna_check.tcl`
- `eco4o_finalize_fill.tcl`
- `eco4o_extract.tcl`, `analyze_sram_slew.tcl`, and `run_postroute.py`
- `collect_iteration.py`, `eco4o_physical_checks.tcl`, `audit_physical_revision.py`, and `report_final_delta.py`

Iteration-specific `incremental_apply.tcl` files record the exact OpenDB changes.

## 18. Exact Final Commands

Final extraction and nine-corner STA:

```sh
ECO4O_ITER_DIR=v3_hier/top/eco4o_slewfix/iterations/top_newcpu_eco4o_19 \
  python3 v3_hier/top/scripts/eco4o/run_postroute.py
ECO4O_ITER_DIR=v3_hier/top/eco4o_slewfix/iterations/top_newcpu_eco4o_19 \
  python3 v3_hier/top/scripts/eco4o/collect_iteration.py
```

Final antenna check:

```sh
ECO4O_FINAL_ODB=v3_hier/top/eco4o_slewfix/iterations/top_newcpu_eco4o_19/soc_top.routed.odb \
ECO4O_ANTENNA_REPORT=v3_hier/top/eco4o_slewfix/iterations/top_newcpu_eco4o_19/antenna_final.rpt \
  openroad -no_init -exit v3_hier/top/scripts/eco4o/eco4o_antenna_check.tcl
```

GDS streamout:

```sh
librelane --manual-pdk --pdk-root "$PDK_VERSION_ROOT" \
  --run-tag top_newcpu_eco4o_19_streamout_50mhz \
  --from KLayout.StreamOut --to Magic.WriteLEF \
  --with-initial-state v3_hier/top/eco4o_slewfix/results/state_eco4o_clean.json \
  v3_hier/top/config_top_newcpu_eco4m_final_50mhz.json \
  v3_hier/top/config_top_newcpu_eco4o_signoff_50mhz.json
```

Foundry DRC, Magic extraction/overlap, and LVS:

```sh
librelane --manual-pdk --pdk-root "$PDK_VERSION_ROOT" \
  --run-tag top_newcpu_eco4o_19_drc_lvs_50mhz --from KLayout.DRC \
  --with-initial-state v3_hier/top/runs/top_newcpu_eco4o_19_streamout_50mhz/03-magic-writelef/state_out.json \
  v3_hier/top/config_top_newcpu_eco4m_final_50mhz.json \
  v3_hier/top/config_top_newcpu_eco4o_signoff_50mhz.json
```

For this run, `PDK_VERSION_ROOT` was
`/home/rin/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71`.

## 19. Reproduction Procedure

Verify the ECO4M hashes, preserve the baseline, and run the numbered scripts
and iteration-local apply files in order. For each routed checkpoint, run
`run_postroute.py` and `collect_iteration.py`; retain a checkpoint only after
placement, PG, routing, connectivity, and timing checks pass. Reproduce ECO18
from ECO16 using its `incremental_apply.tcl`, verify DRT and antenna zero, then
run `eco4o_finalize_fill.tcl` once to create ECO19. Repeat final extraction and
all nine corners on ECO19 before running the two signoff commands above.

## 20. Rollback Procedure

Select `../eco4m_antennafix/soc_top.eco4m_drt.odb` and its matching DEF, then
verify the hashes in `reports/baseline_final_verify.sha256`. ECO4O occupies only
the `eco4o_slewfix`, `scripts/eco4o`, and named `top_newcpu_eco4o_*` run paths;
the ECO4M baseline remains unchanged.

## 21. Remaining Problems

No open setup, hold, max-cap, max-slew, placement, PG-connectivity, signal-route,
DRT, antenna, KLayout DRC, Magic illegal-overlap, or LVS issue remains in ECO19.
The tightest numerical margin is the `0.000527 ns` SRAM slew margin at
`addr0[3]`; it is positive in extracted nine-corner STA.

## 22. Final Status

`top_newcpu_eco4o_19` is frozen. No sizing, movement, buffering, repacking, or
rerouting is permitted after this point without creating a new revision and
repeating extraction, STA, physical verification, GDS generation, and LVS.

STATUS = CLEAN
