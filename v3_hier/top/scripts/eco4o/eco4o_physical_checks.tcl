set out $::env(ECO4O_ITER_DIR)
read_db $out/soc_top.routed.odb
check_placement -verbose
puts ECO4O_PLACEMENT_PASS
foreach net {VPWR VGND} {
    if {[catch {check_power_grid -net $net -error_file $out/${net}_connectivity.rpt} err]} {
        puts "ECO4O_PG_CHECK_FAILED $net: $err"
    } else {puts "ECO4O_PG_CHECK_PASS $net"}
}
write_verilog -include_pwr_gnd $out/soc_top.routed.pnl.v
puts ECO4O_PNL_EXPORTED
