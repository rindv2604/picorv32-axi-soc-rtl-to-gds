set source $::env(ECO4O_SOURCE_ODB)
set out $::env(ECO4O_ITER_DIR)

read_db $source
set inserted [repair_antennas sky130_fd_sc_hd__diode_2 \
    -iterations 5 \
    -ratio_margin 10 \
    -diode_only]
puts "ECO4O_ANTENNA_DIODES_INSERTED $inserted"

check_placement -verbose
check_antennas -report_file $out/antenna_seed.rpt
write_db $out/soc_top.antenna_seed.odb
write_def $out/soc_top.antenna_seed.def
