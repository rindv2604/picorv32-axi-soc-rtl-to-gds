import odb, csv
from pathlib import Path
root=Path(__file__).resolve().parents[2]
db=odb.dbDatabase.create(); odb.read_db(db,str(root/'eco4m_antennafix/soc_top.eco4m_drt.odb'))
b=db.getChip().getBlock(); u=b.getDbUnitsPerMicron(); macro=b.findInst('ram.u_sram_macro')
rows=[]
for t in macro.getITerms():
    name=t.getMTerm().getName()
    if not name.startswith(('addr0[','addr1[','wmask0[')): continue
    n=t.getNet(); drivers=[x for x in n.getITerms() if x.getIoType()=='OUTPUT']; loads=[x for x in n.getITerms() if x.getIoType()=='INPUT']
    for d in drivers:
        inst=d.getInst(); _,sx,sy=t.getAvgXY(); _,dx,dy=d.getAvgXY()
        chain=[]; cur=inst; seen=set()
        while cur.getName() not in seen and ('__buf_' in cur.getMaster().getName() or '__inv_' in cur.getMaster().getName()):
            seen.add(cur.getName()); chain.append(cur.getName()+':'+cur.getMaster().getName())
            ins=[x for x in cur.getITerms() if x.getIoType()=='INPUT' and x.getSigType()=='SIGNAL']
            prev=[x for x in ins[0].getNet().getITerms() if x.getIoType()=='OUTPUT'] if ins else []
            if len(prev)!=1: break
            cur=prev[0].getInst()
        rows.append(dict(pin='ram.u_sram_macro/'+name,net=n.getName(),driver_pin=inst.getName()+'/'+d.getMTerm().getName(),driver_instance=inst.getName(),driver_cell=inst.getMaster().getName(),fanout=len(loads),distance=(abs(sx-dx)+abs(sy-dy))/u,driver_x=dx/u,driver_y=dy/u,sink_x=sx/u,sink_y=sy/u,buffer_chain=' <- '.join(chain),shared=len(loads)>1,routed=n.getWire() is not None))
with open(root/'eco4o_slewfix/reports/geometry.csv','w') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(sorted(rows,key=lambda x:x['pin']))
print('Measured',len(rows),'SRAM input nets; macro origin/orientation',macro.getOrigin(),macro.getOrient())
