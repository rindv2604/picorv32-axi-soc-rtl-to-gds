###############################################################################
# PicoRV32 AXI SoC
# 40 MHz Physical Design Constraints
###############################################################################

current_design soc_top

# ----------------------------------------------------------------------
# Clock
# ----------------------------------------------------------------------

create_clock \
    -name clk \
    -period 25.000 \
    [get_ports {clk}]

set_clock_transition 0.150 [get_clocks {clk}]
set_clock_uncertainty 0.250 [get_clocks {clk}]

# LibreLane:
#   Pre-PnR  -> ideal clock
#   Post-PnR -> propagated clock
if {
    [info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] &&
    $::env(OPENLANE_SDC_IDEAL_CLOCKS)
} {
    unset_propagated_clock [get_clocks {clk}]
} else {
    set_propagated_clock [get_clocks {clk}]
}


# ----------------------------------------------------------------------
# I/O timing
#
# 20% of 25 ns = 5 ns
# ----------------------------------------------------------------------

set_input_delay \
    5.000 \
    -clock [get_clocks {clk}] \
    [get_ports {resetn}]

set_output_delay \
    5.000 \
    -clock [get_clocks {clk}] \
    [get_ports {trap}]

set_output_delay \
    5.000 \
    -clock [get_clocks {clk}] \
    [get_ports {uart_tx}]


# ----------------------------------------------------------------------
# Output load
# ----------------------------------------------------------------------

set_load -pin_load 0.0334 [get_ports {trap}]
set_load -pin_load 0.0334 [get_ports {uart_tx}]


# ----------------------------------------------------------------------
# Input drivers
# ----------------------------------------------------------------------

set_driving_cell \
    -lib_cell sky130_fd_sc_hd__inv_2 \
    -pin Y \
    [get_ports {clk}]

set_driving_cell \
    -lib_cell sky130_fd_sc_hd__inv_2 \
    -pin Y \
    [get_ports {resetn}]


# ----------------------------------------------------------------------
# Electrical constraints
# ----------------------------------------------------------------------

set_max_transition 1.500 [current_design]
set_max_capacitance 0.200 [current_design]
set_max_fanout 16 [current_design]
