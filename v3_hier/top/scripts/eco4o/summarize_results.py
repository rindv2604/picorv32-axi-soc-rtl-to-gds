from pathlib import Path
import csv,re,json
root=Path(__file__).resolve().parents[2]; out=root/'eco4o_slewfix'
geo=list(csv.DictReader(open(out/'reports/geometry.csv')))
cs=[r+'_'+p for r in ('nom','min','max') for p in ('tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95')]
rows=[]
for g in geo:
    vals=[]
    for c in cs:
        pins={r['pin']:r for r in csv.DictReader(open(out/f'reports/{c}_pins.csv'))}
        vals.append((float(pins[g['pin']]['sram_slew']),c,pins[g['pin']]))
    slew,c,p=max(vals)
    txt=(out/f'logs/top_newcpu_eco4o_baseline_{c}.log').read_text()
    sect=txt.split('SRAM_NET '+g['pin']+'\n')[1].split('SRAM_NET')[0]
    caps={label:re.search(label+r' capacitance: ([0-9.]+)',sect).group(1) for label in ['Pin','Wire','Total']}
    g.update(total_cap=caps['Total'],wire_cap=caps['Wire'],pin_cap=caps['Pin'],driver_slew=p['driver_slew'],sram_slew=slew,limit=0.04,worst_corner=c,classification='delay-cell output drive; wire load; strict SRAM 10-90% slew requirement')
    g['buffer_chain']=g['driver_instance']+':'+g['driver_cell']+' (terminal delay buffer; full upstream chain in topology report)'
    rows.append(g)
with open(out/'reports/sram_slew_before.csv','w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
summary=[]
for c in cs:
    txt=(out/f'logs/top_newcpu_eco4o_baseline_{c}.log').read_text()
    get=lambda pat:re.search(pat,txt).group(1)
    summary.append(dict(corner=c,setup_wns=get(r'worst slack max ([-.0-9]+)'),hold_wns=get(r'worst slack min ([-.0-9]+)'),setup_tns=get(r'tns max ([-.0-9]+)'),hold_tns=get(r'tns min ([-.0-9]+)'),slew=get(r'COUNTS slew=(\d+)'),cap=get(r'COUNTS slew=\d+ cap=(\d+)')))
(out/'reports/baseline_summary.json').write_text(json.dumps(summary,indent=2))
print('Baseline SRAM slew range',min(r['sram_slew'] for r in rows),max(r['sram_slew'] for r in rows))
print('Baseline setup WNS',min(float(r['setup_wns']) for r in summary),'hold WNS',min(float(r['hold_wns']) for r in summary))
