set base_odb $::env(ECO4O_BASE_ODB)
set apply_tcl $::env(ECO4O_APPLY_TCL)
set out $::env(ECO4O_ITER_DIR)
set_thread_count 8
read_db $base_odb
set_routing_layers -signal met1-met5 -clock met1-met5
set_macro_extension 2
global_route -start_incremental
source $apply_tcl
check_placement -verbose
puts ECO4O_INCREMENTAL_PLACEMENT_PASS
global_route \
    -end_incremental \
    -guide_file $out/soc_top.guide \
    -congestion_iterations 100 \
    -allow_congestion \
    -verbose
write_db $out/soc_top.grt.odb
detailed_route \
    -droute_end_iter 64 \
    -or_seed 42 \
    -output_drc $out/soc_top.drc \
    -verbose 1
check_placement -verbose
write_db $out/soc_top.routed.odb
write_def $out/soc_top.routed.def
write_verilog $out/soc_top.routed.v
puts ECO4O_INCREMENTAL_ROUTE_COMPLETE
