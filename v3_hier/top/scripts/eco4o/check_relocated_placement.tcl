set out $::env(ECO4O_ITER_DIR)
read_db $out/soc_top.seed.odb
check_placement -verbose
write_db $out/soc_top.legalized.odb
puts ECO4O_RELOCATED_PLACEMENT_PASS
