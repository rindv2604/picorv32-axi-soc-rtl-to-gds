set out $::env(ECO4O_ITER_DIR)
set_thread_count 8
read_db $out/soc_top.inserted.odb
# Insertion script places on vacant legal row sites; verify every cell.
check_placement -verbose
puts ECO4O_PLACEMENT_PASS
set block [ord::get_db_block]
set f [open $out/affected_nets.txt r]
foreach name [split [string trim [read $f]] \n] {
    set net [$block findNet $name]
    if {[$net isSpecial]} {error "Special net in ECO route list"}
    grt::add_net_to_route $net
}
close $f
set_routing_layers -signal met1-met5 -clock met1-met5
set_macro_extension 2
global_route -guide_file $out/soc_top.guide -congestion_iterations 100 -allow_congestion -verbose
write_db $out/soc_top.grt.odb
detailed_route -droute_end_iter 64 -or_seed 42 -output_drc $out/soc_top.drc -verbose 1
check_placement -verbose
write_db $out/soc_top.routed.odb
write_def $out/soc_top.routed.def
write_verilog $out/soc_top.routed.v
puts ECO4O_ROUTE_COMPLETE
