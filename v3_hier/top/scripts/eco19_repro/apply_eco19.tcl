# Apply the complete accepted ECO4A-through-ECO19 logical/physical delta.
# No frozen ECO19 design view is read here.

source [file join [file dirname [info script]] eco19_manifest.tcl]

set block [ord::get_db_block]
set db [ord::get_db]

if {[$block getName] ne "soc_top"} {
    error "ECO19 replay requires design soc_top; found [$block getName]"
}

# Fail before mutation when the deterministic post-DRT anchor names changed.
foreach name $::eco19_required_anchor_instances {
    if {[$block findInst $name] eq "NULL"} {
        error "ECO19 baseline mismatch: required anchor instance '$name' is absent"
    }
}
foreach row $::eco19_cells {
    lassign $row name master x y orient status
    if {[$block findInst $name] ne "NULL"} {
        error "ECO19 baseline mismatch: accepted ECO instance '$name' already exists"
    }
    if {[$db findMaster $master] eq "NULL"} {
        error "ECO19 replay cannot find master '$master' for '$name'"
    }
}
foreach name $::eco19_removed_spacers {
    set inst [$block findInst $name]
    if {$inst eq "NULL"} {
        error "ECO19 baseline mismatch: removable spacer '$name' is absent"
    }
    if {[[$inst getMaster] getType] ne "CORE_SPACER"} {
        error "ECO19 baseline mismatch: '$name' is not a CORE_SPACER"
    }
}

# Original nets are strict anchors.  Only manifest-owned eco* nets may be made.
foreach net_row $::eco19_affected_nets {
    set net_name [lindex $net_row 0]
    if {[$block findNet $net_name] eq "NULL"} {
        if {![string match "eco*" $net_name]} {
            error "ECO19 baseline mismatch: required original net '$net_name' is absent"
        }
        odb::dbNet_create $block $net_name
    }
}

# Remove the exact audited stage-46 spacer delta.  These PHY_EDGE decap_3
# instances do not exist in frozen ECO19; all retained spacers remain intact.
set removed_spacers 0
foreach name $::eco19_removed_spacers {
    odb::dbInst_destroy [$block findInst $name]
    incr removed_spacers
}
if {$removed_spacers != $::eco19_expected_removed_spacer_count} {
    error "ECO19 replay removed-spacer count mismatch"
}

# Recreate every accepted ECO cell with its frozen master and legal site.
foreach row $::eco19_cells {
    lassign $row name master x y orient status
    set inst [odb::dbInst_create $block [$db findMaster $master] $name]
    $inst setPlacementStatus PLACED
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus $status
}

# Reapply the accepted master/placement changes to pre-existing instances.
foreach row $::eco19_modified_originals {
    lassign $row name master x y orient status
    set inst [$block findInst $name]
    if {$inst eq "NULL"} {
        error "ECO19 baseline mismatch: modified original '$name' is absent"
    }
    if {[[$inst getMaster] getName] ne $master} {
        if {![$inst swapMaster [$db findMaster $master]]} {
            error "ECO19 replay failed to swap '$name' to '$master'"
        }
    }
    $inst setPlacementStatus PLACED
    $inst setOrient $orient
    $inst setLocation $x $y
    $inst setPlacementStatus $status
}

# Connect power pins on new ECO cells.  write_views/global_connect will verify
# and refresh the same global connections at the end of the LibreLane step.
set vpwr [$block findNet VPWR]
set vgnd [$block findNet VGND]
foreach row $::eco19_cells {
    set inst [$block findInst [lindex $row 0]]
    foreach pin {VPWR VPB} {
        set iterm [$inst findITerm $pin]
        if {$iterm ne "NULL"} { $iterm connect $vpwr }
    }
    foreach pin {VGND VNB} {
        set iterm [$inst findITerm $pin]
        if {$iterm ne "NULL"} { $iterm connect $vgnd }
    }
}

# Replace complete membership on every ECO-affected signal net.  This captures
# all inserted-buffer topology and every accepted sink rewire, including macro
# pins and top-level ports.  Existing detailed wire on each changed net is
# removed so the incremental router owns its replacement.
foreach net_row $::eco19_affected_nets {
    set net_name [lindex $net_row 0]
    set endpoints [lindex $net_row 1]
    set net [$block findNet $net_name]
    set wire [$net getWire]
    if {$wire ne "NULL"} { odb::dbWire_destroy $wire }
    foreach iterm [$net getITerms] { $iterm disconnect }
    foreach bterm [$net getBTerms] { $bterm disconnect }
    foreach endpoint $endpoints {
        set kind [lindex $endpoint 0]
        if {$kind eq "I"} {
            set inst_name [lindex $endpoint 1]
            set pin_name [lindex $endpoint 2]
            set inst [$block findInst $inst_name]
            if {$inst eq "NULL"} {
                error "ECO19 replay missing endpoint instance '$inst_name' on '$net_name'"
            }
            set iterm [$inst findITerm $pin_name]
            if {$iterm eq "NULL"} {
                error "ECO19 replay missing endpoint '$inst_name/$pin_name'"
            }
            $iterm connect $net
        } elseif {$kind eq "B"} {
            set port_name [lindex $endpoint 1]
            set bterm [$block findBTerm $port_name]
            if {$bterm eq "NULL"} {
                error "ECO19 replay missing top-level port '$port_name'"
            }
            $bterm connect $net
        } else {
            error "ECO19 manifest contains unknown endpoint kind '$kind'"
        }
    }
}

puts "ECO19_APPLY_COMPLETE cells=$::eco19_expected_eco_cell_count nets=$::eco19_expected_affected_net_count removed_spacers=$removed_spacers"
