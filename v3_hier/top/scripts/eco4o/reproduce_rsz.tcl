set top [file normalize [file join [file dirname [info script]] ../..]]
set pdk /home/rin/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71/sky130A
read_liberty $pdk/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib
read_liberty $pdk/libs.ref/sky130_sram_macros/lib/sky130_sram_1kbyte_1rw1r_32x256_8_TT_1p8V_25C.lib
read_liberty $top/../macros/cpu_block/lib/max_ss_100C_1v60/cpu_block__max_ss_100C_1v60.lib
read_db $top/eco4m_antennafix/soc_top.eco4m_drt.odb
read_sdc $top/constraints/top_50mhz_eco4m_final.sdc
read_spef $top/runs/top_newcpu_eco4m_sta_50mhz/01-openroad-rcx/max/soc_top.max.spef
set_wire_rc -signal -layer met2
set_wire_rc -clock -layer met5
# Diagnostic only. No physical state is written by this script.
repair_design -verbose
