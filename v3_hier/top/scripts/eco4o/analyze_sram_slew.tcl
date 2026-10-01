set top [file normalize [file join [file dirname [info script]] ../..]]
set out $top/eco4o_slewfix
set corner $::env(ECO4O_CORNER)
set rc [lindex [split $corner _] 0]
set pvt [join [lrange [split $corner _] 1 end] _]
set pdk /home/rin/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71/sky130A
read_liberty $pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__${pvt}.lib
read_liberty $pdk/libs.ref/sky130_sram_macros/lib/sky130_sram_1kbyte_1rw1r_32x256_8_TT_1p8V_25C.lib
read_verilog $top/../macros/cpu_block/nl/cpu_block.nl.v
if {[info exists ::env(ECO4O_ITER_DIR)]} {
    set out $::env(ECO4O_ITER_DIR)
    file mkdir $out/reports
    read_verilog $out/soc_top.routed.v
} else {
    read_verilog $out/results/soc_top.eco4m_from_odb.v
}
link_design soc_top
read_sdc $top/constraints/top_50mhz_eco4m_final.sdc
if {[info exists ::env(ECO4O_ITER_DIR)]} {
    read_spef $out/soc_top.$rc.spef
} else {
    read_spef $top/runs/top_newcpu_eco4m_sta_50mhz/01-openroad-rcx/$rc/soc_top.$rc.spef
}
read_spef -path cpu $top/../macros/cpu_block/spef/$rc/cpu_block.$rc.spef
set sta_report_default_digits 6
report_worst_slack -max
report_worst_slack -min
report_tns -max
report_tns -min
report_check_types -max_slew -max_capacitance -violators
puts "TIMING_COUNTS setup=[sta::endpoint_violation_count max] hold=[sta::endpoint_violation_count min]"
puts "COUNTS slew=[sta::max_slew_violation_count] cap=[sta::max_capacitance_violation_count]"
report_parasitic_annotation -report_unannotated
set f [open $out/reports/${corner}_pins.csv w]
puts $f "pin,sram_slew,driver_pin,driver_slew"
foreach bus {addr0 addr1 wmask0} {
    set count [expr {$bus eq "wmask0" ? 4 : 8}]
    for {set i 0} {$i<$count} {incr i} {
        set name [format {ram.u_sram_macro/%s[%d]} $bus $i]
        set pin [get_pins [list $name]]
        set net [get_nets -of_objects $pin]
        puts "SRAM_NET $name"
        report_net -digits 8 [get_full_name $net]
        set d [get_pins -of_objects $net -filter "direction==output"]
        puts $f "$name,[get_property $pin slew_max],[get_full_name $d],[get_property $d slew_max]"
    }
}
close $f
report_checks -path_delay max -group_path_count 1 -format full_clock_expanded
report_checks -path_delay min -group_path_count 1 -format full_clock_expanded
