# Structural, placement, routing, and DRT-marker guard for the replay step.

set block [ord::get_db_block]
set seen 0
foreach row $::eco19_cells {
    lassign $row name master x y orient status
    set inst [$block findInst $name]
    if {$inst eq "NULL"} { error "ECO19 verify: missing '$name'" }
    if {[[$inst getMaster] getName] ne $master} {
        error "ECO19 verify: master mismatch on '$name'"
    }
    if {[$inst getLocation] ne [list $x $y]} {
        error "ECO19 verify: location mismatch on '$name'"
    }
    if {[$inst getOrient] ne $orient} {
        error "ECO19 verify: orientation mismatch on '$name'"
    }
    incr seen
}
if {$seen != $::eco19_expected_eco_cell_count} {
    error "ECO19 verify: expected $::eco19_expected_eco_cell_count ECO cells, saw $seen"
}
foreach name $::eco19_removed_spacers {
    if {[$block findInst $name] ne "NULL"} {
        error "ECO19 verify: removed spacer '$name' is still present"
    }
}

foreach net_row $::eco19_affected_nets {
    set net_name [lindex $net_row 0]
    set expected [list]
    foreach endpoint [lindex $net_row 1] {
        if {[lindex $endpoint 0] eq "I"} {
            lappend expected "I|[lindex $endpoint 1]|[lindex $endpoint 2]"
        } else {
            lappend expected "B|[lindex $endpoint 1]"
        }
    }
    set net [$block findNet $net_name]
    if {$net eq "NULL"} { error "ECO19 verify: missing net '$net_name'" }
    set actual [list]
    foreach iterm [$net getITerms] {
        lappend actual "I|[[$iterm getInst] getName]|[[$iterm getMTerm] getName]"
    }
    foreach bterm [$net getBTerms] { lappend actual "B|[$bterm getName]" }
    if {[lsort $actual] ne [lsort $expected]} {
        error "ECO19 verify: endpoint mismatch on '$net_name'"
    }
    if {[$net getWire] eq "NULL"} {
        error "ECO19 verify: affected net '$net_name' has no detailed routing"
    }
}

check_placement -verbose
set drc_file $::env(STEP_DIR)/$::env(DESIGN_NAME).drc
if {![file exists $drc_file]} { error "ECO19 verify: DRT report was not written" }
if {[file size $drc_file] != 0} {
    error "ECO19 verify: DRT report is nonempty: $drc_file"
}
puts "ECO19_VERIFY_COMPLETE cells=$seen nets=$::eco19_expected_affected_net_count drt_markers=0"
