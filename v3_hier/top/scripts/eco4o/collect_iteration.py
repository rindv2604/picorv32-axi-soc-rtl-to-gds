from pathlib import Path
import os,re,json,csv
out=Path(os.environ['ECO4O_ITER_DIR']);cs=[r+'_'+p for r in ('nom','min','max') for p in ('tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95')];summary=[];pins={};remaining=set()
for c in cs:
    text=(out/f'sta_{c}.log').read_text()
    def val(p):
        m=re.search(p,text)
        if not m:raise RuntimeError(f'Missing metric {p} in {c}')
        return float(m.group(1))
    row=dict(corner=c,setup_wns=val(r'worst slack max ([-.0-9]+)'),hold_wns=val(r'worst slack min ([-.0-9]+)'),setup_tns=val(r'tns max ([-.0-9]+)'),hold_tns=val(r'tns min ([-.0-9]+)'),setup_count=int(val(r'TIMING_COUNTS setup=(\d+)')),hold_count=int(val(r'TIMING_COUNTS setup=\d+ hold=(\d+)')),slew_count=int(val(r'COUNTS slew=(\d+)')),cap_count=int(val(r'COUNTS slew=\d+ cap=(\d+)')));summary.append(row)
    for r in csv.DictReader(open(out/f'reports/{c}_pins.csv')):
        r['sram_slew']=float(r['sram_slew']);r['corner']=c
        section=text.split('SRAM_NET '+r['pin']+'\n')[1].split('SRAM_NET')[0]
        r.update({k.lower()+'_cap':float(re.search(k+r' capacitance: ([.0-9]+)',section).group(1)) for k in ('Pin','Wire','Total')})
        if r['pin'] not in pins or r['sram_slew']>pins[r['pin']]['sram_slew']:pins[r['pin']]=r
        if r['sram_slew']>0.04:remaining.add(r['pin'])
assert len(pins)==20
(out/'summary.json').write_text(json.dumps(summary,indent=2));(out/'remaining_pins.json').write_text(json.dumps(sorted(remaining),indent=2))
with open(out/'reports/sram_slew_after.csv','w') as f:
    w=csv.DictWriter(f,fieldnames=list(next(iter(pins.values()))));w.writeheader();w.writerows(pins.values())
lines=['corner,setup_wns_ns,hold_wns_ns,setup_count,hold_count,cap_count,slew_count']
for r in summary:lines.append(','.join(str(r[k]) for k in ['corner','setup_wns','hold_wns','setup_count','hold_count','cap_count','slew_count']))
lines += ['Worst setup: '+str(min(r['setup_wns'] for r in summary)),'Worst hold: '+str(min(r['hold_wns'] for r in summary)),'Remaining original SRAM pins: '+str(len(remaining))]+sorted(remaining)
(out/'reports/sta_summary.txt').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
