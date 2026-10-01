set root [file normalize [file join [file dirname [info script]] ../../..]]
read_db $root/top/eco4m_antennafix/soc_top.eco4m_drt.odb
write_verilog $root/top/eco4o_slewfix/results/soc_top.eco4m_from_odb.v
check_placement -verbose
