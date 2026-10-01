set top [file normalize [file join [file dirname [info script]] ../..]]
set out $::env(ECO4O_ITER_DIR)
set rc $::env(ECO4O_RC)
set pdk /home/rin/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71/sky130A
read_lef $pdk/libs.ref/sky130_fd_sc_hd/techlef/sky130_fd_sc_hd__${rc}.tlef
read_lef $pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_fd_sc_hd.lef
read_lef $pdk/libs.ref/sky130_fd_sc_hd/lef/sky130_ef_sc_hd.lef
read_lef $pdk/libs.ref/sky130_sram_macros/lef/sky130_sram_1kbyte_1rw1r_32x256_8.lef
read_lef $top/../macros/cpu_block/lef/cpu_block.lef
read_def $out/soc_top.routed.def
define_process_corner -ext_model_index 0 CURRENT_CORNER
extract_parasitics -ext_model_file $pdk/libs.tech/openlane/rules.openrcx.sky130A.${rc}.calibre -lef_res
write_spef $out/soc_top.${rc}.spef
puts ECO4O_EXTRACTION_COMPLETE
