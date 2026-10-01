# Replay only signal-net routes that differ from the clean stage-46 baseline.
# The donor ODB contains 574 dbWires and zero instances/ports; eco19_routes.def
# is the human-readable representation of the same generated route delta.
set route_donor_path [file join [file dirname [info script]] eco19_route_donor.odb]
if {![file exists $route_donor_path]} {
    error "ECO19 route donor is missing: $route_donor_path"
}
set route_donor [odb::dbDatabase_create]
odb::read_db $route_donor $route_donor_path
set route_block [[$route_donor getChip] getBlock]
if {[llength [$route_block getInsts]] != 0 || [llength [$route_block getBTerms]] != 0} {
    error "ECO19 route donor must not contain instances or ports"
}
if {[llength [$route_block getNets]] != $::eco19_expected_route_net_count} {
    error "ECO19 route donor net-count mismatch"
}

set route_count 0
foreach route_net [$route_block getNets] {
    set net_name [$route_net getName]
    set target_net [$block findNet $net_name]
    if {$target_net eq "NULL"} {
        error "ECO19 route replay cannot find target net '$net_name'"
    }
    set donor_wire [$route_net getWire]
    if {$donor_wire eq "NULL"} {
        error "ECO19 route donor net '$net_name' has no dbWire"
    }
    set old_wire [$target_net getWire]
    if {$old_wire ne "NULL"} { odb::dbWire_destroy $old_wire }
    set target_wire [odb::dbWire_create $target_net]
    odb::dbWire_append $target_wire $donor_wire
    incr route_count
}
odb::dbDatabase_destroy $route_donor
if {$route_count != $::eco19_expected_route_net_count} {
    error "ECO19 route replay count mismatch"
}

# Run the same deterministic TritonRoute cleanup with a bounded iteration count.
# OpenROAD dcf36133 reports three met1 spacing markers between clk and
# clknet_2_1_0_clk_regs even on the untouched LL3.0.1-compatible frozen ECO19
# ODB.  With the fixed seed, iteration 3 removes those compatibility markers;
# the empty DRC report is enforced by verify_eco19.tcl.
set_thread_count $::env(DRT_THREADS)
detailed_route \
    -droute_end_iter 10 \
    -or_seed 42 \
    -output_drc $::env(STEP_DIR)/$::env(DESIGN_NAME).drc \
    -verbose 1

puts "ECO19_ROUTE_REPLAY_COMPLETE nets=$route_count"
