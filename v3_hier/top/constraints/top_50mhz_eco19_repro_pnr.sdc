###############################################################################
# PicoRV32 AXI SoC
# 50 MHz - topology-safe PNR constraints for the ECO19 full reproduction
#
# OpenROAD repair/resizer stages may delete or replace instances.  Keep mutable
# PNR constraints on the design and top-level ports so write_sdc never retains
# stale hierarchical dbITerm handles.  Final STA continues to use the proven
# top_50mhz_eco4m_final.sdc through SIGNOFF_SDC_FILE.
###############################################################################

current_design soc_top

create_clock \
    -name clk \
    -period 20.000 \
    [get_ports {clk}]

set_clock_transition 0.150 [get_clocks {clk}]
set_clock_uncertainty 0.250 [get_clocks {clk}]

if {
    [info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] &&
    $::env(OPENLANE_SDC_IDEAL_CLOCKS)
} {
    unset_propagated_clock [get_clocks {clk}]
} else {
    set_propagated_clock [get_clocks {clk}]
}

set_input_transition -min -rise 0.150 [get_ports {resetn}]
set_input_transition -min -fall 0.150 [get_ports {resetn}]
set_input_transition -max -rise 0.500 [get_ports {resetn}]
set_input_transition -max -fall 0.500 [get_ports {resetn}]

set_output_delay \
    -min 0.000 \
    -clock [get_clocks {clk}] \
    [get_ports {trap uart_tx}]

set_output_delay \
    -max 4.000 \
    -clock [get_clocks {clk}] \
    [get_ports {trap uart_tx}]

set_load -pin_load 0.0334 [get_ports {trap}]
set_load -pin_load 0.0334 [get_ports {uart_tx}]

set_driving_cell \
    -lib_cell sky130_fd_sc_hd__inv_2 \
    -pin Y \
    [get_ports {clk}]

set_max_transition 1.500 [current_design]

# During topology-changing PNR, use the largest approved CTS exception as the
# design-wide ceiling and retain the strict 0.200 pF constraint on stable ports.
# Final signoff restores the per-output 0.200 pF policy and the two CTS limits.
set_max_capacitance 0.240 [current_design]
set_max_capacitance 0.200 [get_ports *]
set_max_fanout 16 [current_design]

set_false_path -from [get_ports {resetn}]
