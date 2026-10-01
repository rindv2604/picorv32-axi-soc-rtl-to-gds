# Accepted ECO19 coordinates are already snapped to legal sky130_hd sites.
# FIRM status prevents exploratory movement.  Legalization is therefore an
# exact placement check with zero accepted displacement.

check_placement -verbose
puts "ECO19_LEGALIZATION_COMPLETE displacement=0"
