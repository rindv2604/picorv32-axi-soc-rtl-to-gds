###############################################################################
# PicoRV32 AXI SoC
# 50 MHz - Reset Synchronizer Version
###############################################################################

current_design soc_top

# ----------------------------------------------------------------------
# Clock
# 50 MHz = 20 ns
# ----------------------------------------------------------------------

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

# ----------------------------------------------------------------------
# External reset
#
# resetn is now an asynchronous assertion input only to the
# two-flop reset synchronizer. It is no longer a normal synchronous
# functional data input to the SoC.
# ----------------------------------------------------------------------

set_input_transition \
    -min -rise 0.150 \
    [get_ports {resetn}]

set_input_transition \
    -min -fall 0.150 \
    [get_ports {resetn}]

set_input_transition \
    -max -rise 0.500 \
    [get_ports {resetn}]

set_input_transition \
    -max -fall 0.500 \
    [get_ports {resetn}]

# Do not apply normal setup input delay to asynchronous reset.

# ----------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------

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

# ----------------------------------------------------------------------
# Clock source driving model
# ----------------------------------------------------------------------

set_driving_cell \
    -lib_cell sky130_fd_sc_hd__inv_2 \
    -pin Y \
    [get_ports {clk}]

# ----------------------------------------------------------------------
# Electrical constraints
# ----------------------------------------------------------------------

set_max_transition 1.500 [current_design]
# ============================================================
# ECO4M FINAL MAX-CAP POLICY
#
# Ordinary outputs remain strict at 0.200 pF.
#
# CTS trunk exceptions:
#   clkbuf_2_0_0_clk_regs/X -> 0.230 pF
#   clkbuf_2_1_0_clk_regs/X -> 0.240 pF
# ============================================================

set_max_capacitance 0.240 [current_design]

set eco4m_cap_exc_023 \
    [get_pins {clkbuf_2_0_0_clk_regs/X}]

set eco4m_cap_exc_024 \
    [get_pins {clkbuf_2_1_0_clk_regs/X}]

set eco4m_strict_outputs \
    [get_pins -hierarchical * -filter "direction==output"]

set eco4m_strict_outputs \
    [delete_from_list \
        $eco4m_strict_outputs \
        $eco4m_cap_exc_023]

set eco4m_strict_outputs \
    [delete_from_list \
        $eco4m_strict_outputs \
        $eco4m_cap_exc_024]

# Normal internal drivers remain at project target.
set_max_capacitance 0.200 $eco4m_strict_outputs

# Top-level ports remain strict as well.
set_max_capacitance 0.200 [get_ports *]

# Only these two CTS trunk outputs receive exceptions.
set_max_capacitance 0.230 $eco4m_cap_exc_023
set_max_capacitance 0.240 $eco4m_cap_exc_024

set_max_fanout 16 [current_design]


# External asynchronous reset is not a functional synchronous timing path.
# Deassertion is synchronized internally by the two-stage reset synchronizer.
set_false_path -from [get_ports {resetn}]
