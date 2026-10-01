# Recreate ECO19's final physical-only refill, then let LibreLane write normal
# ODB/DEF/NL/PNL views.  The apply step already removed the exact audited
# baseline-only spacer delta; accepted retained decaps/taps remain intact.

source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
source [file join [file dirname [info script]] eco19_manifest.tcl]

filler_placement -prefix eco4o_fill_ {
    sky130_fd_sc_hd__fill_8
    sky130_fd_sc_hd__fill_4
    sky130_fd_sc_hd__fill_2
    sky130_fd_sc_hd__fill_1
}

set refill_count 0
foreach inst [[ord::get_db_block] getInsts] {
    if {[string match "eco4o_fill_*" [$inst getName]]} { incr refill_count }
}
if {$refill_count != $::eco19_expected_refill_count} {
    error "ECO19 refill count mismatch: expected $::eco19_expected_refill_count, got $refill_count"
}
set final_instance_count [llength [[ord::get_db_block] getInsts]]
if {$final_instance_count != $::eco19_expected_final_instance_count} {
    error "ECO19 final instance-count mismatch: expected $::eco19_expected_final_instance_count, got $final_instance_count"
}
check_placement -verbose

# Validate the actual refilled database.  In OpenROAD dcf36133 the filler-aware
# region query exposes two residual spacing markers on the same clk/clknet pair
# handled by the bounded compatibility cleanup in route_eco19.tcl.
set post_refill_drc $::env(STEP_DIR)/$::env(DESIGN_NAME).post_refill.drc
set post_refill_drt_threads 4
if {[info exists ::env(DRT_THREADS)]} {
    set post_refill_drt_threads $::env(DRT_THREADS)
}
set_thread_count $post_refill_drt_threads
detailed_route \
    -droute_end_iter 10 \
    -or_seed 42 \
    -output_drc $post_refill_drc \
    -verbose 1
if {![file exists $post_refill_drc]} {
    error "ECO19 post-refill DRT report was not written"
}
if {[file size $post_refill_drc] != 0} {
    error "ECO19 post-refill DRT report is nonempty: $post_refill_drc"
}
puts "ECO19_REFILL_COMPLETE prefix=eco4o_fill_ cells=$refill_count total_instances=$final_instance_count"
puts "ECO19_POST_REFILL_DRT_COMPLETE drt_markers=0"
write_views
