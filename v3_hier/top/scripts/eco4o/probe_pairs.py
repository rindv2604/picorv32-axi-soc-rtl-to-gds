from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]; out=root/'eco4o_slewfix/iterations/top_newcpu_eco4o_feasibility'
pdk=Path('/home/rin/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71/sky130A')
specs=[(a,b) for a in (2,4,8) for b in (4,8,16)]
v=out/'pairs.v'; v.write_text('module probe(input a, output '+','.join(f'z{i}' for i in range(len(specs)))+');\n'+'\n'.join(f'wire n{i}; sky130_fd_sc_hd__clkinv_{a} p{i}(.A(a),.Y(n{i})); sky130_fd_sc_hd__clkinv_{b} q{i}(.A(n{i}),.Y(z{i}));' for i,(a,b) in enumerate(specs))+'\nendmodule\n')
t=out/'pairs.tcl'; t.write_text(f'read_liberty {pdk}/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib\nread_verilog {v}\nlink_design probe\nset f [open {out}/pairs.csv w]\nputs $f "first,final,input_slew,load,output_slew"\nforeach load {{0.00689 0.008 0.01 0.012 0.015}} {{\nset_load $load [all_outputs]\nforeach inslew {{0.2 0.3 0.5}} {{\nset_input_transition $inslew [get_ports a]\n'+'\n'.join(f'puts $f "{a},{b},$inslew,$load,[get_property [get_pins q{i}/Y] slew_max]"' for i,(a,b) in enumerate(specs))+'\n}\n}\nclose $f\n')
with open(out/'pairs.log','w') as f: subprocess.run(['sta','-exit',str(t)],stdout=f,stderr=subprocess.STDOUT,check=True)
