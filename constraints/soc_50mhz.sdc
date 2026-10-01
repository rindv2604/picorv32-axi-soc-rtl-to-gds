###############################################################################
# PicoRV32 AXI SoC
# 50 MHz Physical Design Constraints
###############################################################################

current_design soc_top

# Clock: 50 MHz = 20 ns
create_clock \
    -name clk \
    -period 20.000 \
    [get_ports {clk}]

set_clock_transition 0.150 [get_clocks {clk}]
set_clock_uncertainty 0.250 [get_clocks {clk}]

# Pre-PnR: ideal clock
# Post-PnR: propagated clock
if {
    [info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] &&
    $::env(OPENLANE_SDC_IDEAL_CLOCKS)
} {
    unset_propagated_clock [get_clocks {clk}]
} else {
    set_propagated_clock [get_clocks {clk}]
}

# I/O timing
# 20% of 20 ns = 4 ns
set_input_delay \
    4.000 \
    -clock [get_clocks {clk}] \
    [get_ports {resetn}]

set_output_delay \
    4.000 \
    -clock [get_clocks {clk}] \
    [get_ports {trap}]

set_output_delay \
    4.000 \
    -clock [get_clocks {clk}] \
    [get_ports {uart_tx}]

# Output load
set_load -pin_load 0.0334 [get_ports {trap}]
set_load -pin_load 0.0334 [get_ports {uart_tx}]

# Input driving cells
set_driving_cell \
    -lib_cell sky130_fd_sc_hd__inv_2 \
    -pin Y \
    [get_ports {clk}]

set_driving_cell \
    -lib_cell sky130_fd_sc_hd__inv_2 \
    -pin Y \
    [get_ports {resetn}]

# Electrical constraints
set_max_transition 1.500 [current_design]
set_max_capacitance 0.200 [current_design]
set_max_fanout 16 [current_design]
