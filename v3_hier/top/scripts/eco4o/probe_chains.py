"""Actual SRAM sink probes, including Liberty threshold conversion; ideal wires."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[2]; out=root/'eco4o_slewfix/iterations/top_newcpu_eco4o_feasibility'
pdk=Path('/home/rin/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71/sky130A')
specs=[
    (4,8),(8,8),(8,16),(16,16),
    (2,4,8,8),(2,8,8,8),(2,8,16,8),(2,8,16,16),
    (4,8,8,8),(4,8,16,8),(4,8,16,16),
    (8,8,16,8),(8,8,16,16),(8,16,16,16),(16,16,16,16),
]
v=out/'chains.v'; lines=['module probe(input a);']
for i,seq in enumerate(specs):
    prev='a'
    for j,drive in enumerate(seq):
        n=f'n{i}_{j}'; lines += [f'wire {n};',f'sky130_fd_sc_hd__clkinv_{drive} u{i}_{j}(.A({prev}),.Y({n}));']; prev=n
    lines += [f'sky130_sram_1kbyte_1rw1r_32x256_8 ram{i}(.addr0({{7\'b0,{prev}}}));']
lines += ['endmodule']; v.write_text('\n'.join(lines)+'\n')
t=out/'chains.tcl'; t.write_text(f'read_liberty {pdk}/libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__ss_100C_1v60.lib\nread_liberty {pdk}/libs.ref/sky130_sram_macros/lib/sky130_sram_1kbyte_1rw1r_32x256_8_TT_1p8V_25C.lib\nread_verilog {v}\nlink_design probe\nset f [open {out}/chains.csv w]\nputs $f "chain,input_slew,extra_load,sram_slew"\nforeach cap {{0.0 0.001 0.002 0.003 0.004}} {{\n'+ '\n'.join(f'set_load $cap [get_nets n{i}_{len(seq)-1}]' for i,seq in enumerate(specs))+'\nforeach inslew {0.2 0.3 0.4 0.5 0.7} {\nset_input_transition $inslew [get_ports a]\n'+ '\n'.join('puts $f "'+ '-'.join(map(str,seq))+f',$inslew,$cap,[get_property [get_pins {{ram{i}/addr0[0]}}] slew_max]"' for i,seq in enumerate(specs))+'\n}\n}\nclose $f\n')
with open(out/'chains.log','w') as f: subprocess.run(['sta','-exit',str(t)],stdout=f,stderr=subprocess.STDOUT,check=True)
