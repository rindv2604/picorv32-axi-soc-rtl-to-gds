"""Generate ideal-wire one-cell / two-inverter STA probes from actual Liberty cells."""
from pathlib import Path
import re, subprocess, os
root=Path(__file__).resolve().parents[2]; out=root/'eco4o_slewfix/iterations/top_newcpu_eco4o_feasibility'
out.mkdir(exist_ok=True)
pdk=Path('/home/rin/.ciel/ciel/sky130/versions/8afc8346a57fe1ab7934ba5a6056ea8b43078e71/sky130A')
for pvt in ['tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95']:
    lib=pdk/f'libs.ref/sky130_fd_sc_hd/lib/sky130_fd_sc_hd__{pvt}.lib'
    cells=re.findall(r'cell\s*\("(sky130_fd_sc_hd__(?:buf|clkbuf|inv|clkinv|clkdlybuf4s25)_\d+)"\)',lib.read_text())
    ports=[]; instances=[]; specs=[]
    for i,c in enumerate(cells):
        port='Y' if '__inv_' in c or '__clkinv_' in c else 'X'
        instances.append(f'{c} u{i} (.A(a), .{port}(z{i}));'); ports.append(f'z{i}'); specs.append((c,f'u{i}/{port}'))
    # Real non-inverting alternative: two inverters of the same drive strength.
    for c in cells:
        if '__inv_' not in c and '__clkinv_' not in c: continue
        i=len(ports); ports.append(f'z{i}'); instances += [f'wire n{i};',f'{c} p{i} (.A(a), .Y(n{i}));',f'{c} q{i} (.A(n{i}), .Y(z{i}));']; specs.append((c+'__pair',f'q{i}/Y'))
    v=out/f'{pvt}.v'; v.write_text('module probe(input a, output '+','.join(ports)+');\n'+'\n'.join(instances)+'\nendmodule\n')
    tcl=out/f'{pvt}.tcl'
    tcl.write_text(f'read_liberty {{{lib}}}\nread_verilog {{{v}}}\nlink_design probe\nset_load 0.00689 [all_outputs]\n'+
        f'set f [open {{{out}/{pvt}.csv}} w]\nputs $f "cell,input_slew_ns,load_pf,output_rise_ns,output_fall_ns,worst_ns"\n'+
        'foreach inslew {0.0 0.01 0.04 0.1 0.2} {\nset_input_transition $inslew [get_ports a]\n'+
        '\n'.join(f'puts $f "{c},$inslew,0.00689,[get_property [get_pins {pin}] slew_max_rise],[get_property [get_pins {pin}] slew_max_fall],[get_property [get_pins {pin}] slew_max]"' for c,pin in specs)+'\n}\nclose $f\n')
    with open(out/f'{pvt}.log','w') as log: subprocess.run(['sta','-exit',str(tcl)],stdout=log,stderr=subprocess.STDOUT,check=True)
    print('Probed',pvt,len(specs),'topologies',flush=True)
