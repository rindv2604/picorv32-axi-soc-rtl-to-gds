if {![info exists ::env(ECO4O_FINAL_ODB)]} {
    error "ECO4O_FINAL_ODB is required"
}
if {![info exists ::env(ECO4O_ANTENNA_REPORT)]} {
    error "ECO4O_ANTENNA_REPORT is required"
}

read_db $::env(ECO4O_FINAL_ODB)
check_antennas -report_file $::env(ECO4O_ANTENNA_REPORT)
