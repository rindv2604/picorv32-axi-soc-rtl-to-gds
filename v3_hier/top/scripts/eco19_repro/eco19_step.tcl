# LibreLane/OpenROAD entry point for the deterministic accepted ECO19 replay.

source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb
source $::env(SCRIPTS_DIR)/openroad/common/set_routing_layers.tcl
source $::env(SCRIPTS_DIR)/openroad/common/set_layer_adjustments.tcl
set_macro_extension $::env(GRT_MACRO_EXTENSION)

source [file join [file dirname [info script]] apply_eco19.tcl]
source [file join [file dirname [info script]] place_eco19.tcl]
source [file join [file dirname [info script]] route_eco19.tcl]
source [file join [file dirname [info script]] verify_eco19.tcl]

write_views
