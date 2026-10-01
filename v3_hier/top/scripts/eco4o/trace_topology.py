import odb,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];db=odb.dbDatabase.create();odb.read_db(db,str(root/'eco4m_antennafix/soc_top.eco4m_drt.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
result=[]
for t in b.findInst('ram.u_sram_macro').getITerms():
    p=t.getMTerm().getName()
    if not p.startswith(('addr0[','addr1[','wmask0[')):continue
    cur=t; chain=[]; seen=set()
    while cur and len(chain)<30:
        net=cur.getNet(); ds=[x for x in net.getITerms() if x.getIoType()=='OUTPUT']
        if len(ds)!=1:break
        d=ds[0];i=d.getInst();c=i.getMaster().getName()
        if i.getName() in seen:break
        seen.add(i.getName()); chain.append(dict(instance=i.getName(),cell=c,output_pin=d.getMTerm().getName(),net=net.getName(),fanout=sum(x.getIoType()=='INPUT' for x in net.getITerms()),location_um=[x/u for x in i.getLocation()]))
        if not any(s in c for s in ('buf','inv')):break
        ins=[x for x in i.getITerms() if x.getIoType()=='INPUT' and x.getSigType()=='SIGNAL'];cur=ins[0] if len(ins)==1 else None
    result.append(dict(pin='ram.u_sram_macro/'+p,upstream_chain=chain))
(root/'eco4o_slewfix/reports/topology.json').write_text(json.dumps(result,indent=2))
