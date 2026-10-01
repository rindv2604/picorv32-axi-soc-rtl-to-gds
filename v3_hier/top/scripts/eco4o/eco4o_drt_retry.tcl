set input_odb $::env(ECO4O_INPUT_ODB)
set out $::env(ECO4O_ITER_DIR)
set_thread_count 8
read_db $input_odb
check_placement -verbose
detailed_route \
    -droute_end_iter 64 \
    -or_seed 314159 \
    -output_drc $out/soc_top.drc \
    -verbose 1
check_placement -verbose
write_db $out/soc_top.routed.odb
write_def $out/soc_top.routed.def
write_verilog $out/soc_top.routed.v
puts ECO4O_DRT_RETRY_COMPLETE
