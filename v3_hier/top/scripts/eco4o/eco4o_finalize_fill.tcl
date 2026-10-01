set source $::env(ECO4O_SOURCE_ODB)
set out $::env(ECO4O_ITER_DIR)
read_db $source
filler_placement -prefix eco4o_fill_ {
    sky130_fd_sc_hd__fill_8
    sky130_fd_sc_hd__fill_4
    sky130_fd_sc_hd__fill_2
    sky130_fd_sc_hd__fill_1
}
add_global_connection -net VPWR -inst_pattern {^eco4o_fill_.*} -pin_pattern {^VPWR$} -power
add_global_connection -net VPWR -inst_pattern {^eco4o_fill_.*} -pin_pattern {^VPB$} -power
add_global_connection -net VGND -inst_pattern {^eco4o_fill_.*} -pin_pattern {^VGND$} -ground
add_global_connection -net VGND -inst_pattern {^eco4o_fill_.*} -pin_pattern {^VNB$} -ground
global_connect
check_placement -verbose
puts ECO4O_FINAL_FILL_PLACEMENT_PASS
foreach net {VPWR VGND} {
    check_power_grid -net $net -error_file $out/${net}_connectivity.rpt
    puts "ECO4O_FINAL_FILL_PG_PASS $net"
}
write_db $out/soc_top.routed.odb
write_def $out/soc_top.routed.def
write_verilog $out/soc_top.routed.v
write_verilog -include_pwr_gnd $out/soc_top.routed.pnl.v
puts ECO4O_FINAL_FILL_COMPLETE
