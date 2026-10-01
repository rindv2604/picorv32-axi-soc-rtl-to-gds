set out $::env(ECO4O_ITER_DIR)
read_db $out/soc_top.seed.odb
detailed_placement -max_displacement {100 100}
check_placement -verbose
write_db $out/soc_top.legalized.odb
puts ECO4O_LEGALIZATION_PASS
