"""Target ECO from immutable ECO4M. Snap new cells to unoccupied legal row sites."""
import odb, csv, json, math, os
from pathlib import Path
root=Path(__file__).resolve().parents[2]; out=root/('eco4o_slewfix/iterations/'+os.environ.get('ECO4O_ITERATION','top_newcpu_eco4o_02')); out.mkdir(exist_ok=True)
db=odb.dbDatabase.create(); odb.read_db(db,str(root/'eco4m_antennafix/soc_top.eco4m_drt.odb'))
b=db.getChip().getBlock(); u=b.getDbUnitsPerMicron()
changes=[]; affected=set(); statuses={i.getName():i.getPlacementStatus() for i in b.getInsts()}
fix={'eco4k_d12_mid','eco4k_d13_mid','eco4k_a6_mid'}
def rect(i):
    r=i.getBBox(); return (r.xMin(),r.yMin(),r.xMax(),r.yMax())
occupied={i.getName():rect(i) for i in b.getInsts() if i.getName() not in fix}
fillers={i.getName() for i in b.getInsts() if i.getMaster().getType()=='CORE_SPACER' or '__decap_' in i.getMaster().getName()}
rows=list(b.getRows())
def near_place(inst,sx,sy):
    m=inst.getMaster(); w,h=m.getWidth(),m.getHeight(); candidates=[]
    for row in rows:
        box=row.getBBox(); y=box.yMin(); step=row.getSpacing()
        if abs(y-sy)>100*u or row.getSite().getHeight()!=h or step<=0: continue
        lo=max(0,math.ceil((sx-100*u-box.xMin())/step)); hi=min(row.getSiteCount()-math.ceil(w/step),math.floor((sx+100*u-box.xMin())/step))
        for j in range(lo,hi+1):
            x=box.xMin()+j*step
            dist=abs(x+w/2-sx)+abs(y+h/2-sy)
            candidates.append((dist,x,y,str(row.getOrient())))
    for _,x,y,o in sorted(candidates):
        collisions=[name for name,r in occupied.items() if x<r[2] and x+w>r[0] and y<r[3] and y+h>r[1]]
        if any(name not in fillers for name in collisions): continue
        for name in collisions:
            fi=b.findInst(name)
            changes.append(dict(action='remove_filler',instance=name,cell=fi.getMaster().getName(),old_xy=fi.getLocation(),reason='Make legal space for SRAM ECO'))
            odb.dbInst.destroy(fi); del occupied[name]; fillers.remove(name)
        inst.setOrient(o); inst.setLocation(x,y); inst.setPlacementStatus('PLACED'); occupied[inst.getName()]=rect(inst); return
    raise RuntimeError('No free site for '+inst.getName())
# Repair only the three identified pre-existing placement failures.
for name in sorted(fix):
    inst=b.findInst(name); old=inst.getLocation(); near_place(inst,*old)
    for t in inst.getITerms():
        if t.getNet() and t.getSigType()=='SIGNAL': affected.add(t.getNet().getName())
    changes.append(dict(action='move',instance=name,cell=inst.getMaster().getName(),old_xy=old,new_xy=inst.getLocation(),reason='ECO4M placement failure'))
macro=b.findInst('ram.u_sram_macro')
targets=[t for t in sorted(macro.getITerms(),key=lambda t:t.getMTerm().getName()) if t.getMTerm().getName().startswith(('addr0[','addr1[','wmask0['))]
finals={}
for t in targets:
    pin=t.getMTerm().getName(); tag=pin.replace('[','_').replace(']',''); _,sx,sy=t.getAvgXY()
    inst=odb.dbInst_create(b,db.findMaster('sky130_fd_sc_hd__clkinv_16'),'eco4o_'+tag+'_s4')
    near_place(inst,sx,sy); finals[pin]=inst
for t in targets:
    pin=t.getMTerm().getName(); oldnet=t.getNet(); tag=pin.replace('[','_').replace(']','')
    seq=[4,8,16,16]; cells=[finals[pin]]; tx,ty=cells[0].getLocation()
    for j in (2,1,0):
        inst=odb.dbInst_create(b,db.findMaster('sky130_fd_sc_hd__clkinv_'+str(seq[j])),'eco4o_'+tag+'_s'+str(j+1))
        near_place(inst,tx,ty); cells.insert(0,inst); tx,ty=inst.getLocation()
    nets=[oldnet]+[odb.dbNet_create(b,'eco4o_'+tag+'_n'+str(j+1)) for j in range(len(seq))]
    t.disconnect(); t.connect(nets[-1])
    for j,inst in enumerate(cells):
        inst.findITerm('A').connect(nets[j]); inst.findITerm('Y').connect(nets[j+1])
        for name,net in [('VPWR','VPWR'),('VPB','VPWR'),('VGND','VGND'),('VNB','VGND')]: inst.findITerm(name).connect(b.findNet(net))
        changes.append(dict(action='insert',instance=inst.getName(),cell=inst.getMaster().getName(),pin=pin,new_xy=inst.getLocation(),orient=str(inst.getOrient()),reason='Actual SRAM threshold/load probe requires four stages'))
    affected.update(n.getName() for n in nets)
# Strip only affected signal routes. Other routes remain in place as DRT obstacles.
for name in sorted(affected):
    n=b.findNet(name)
    assert n and not n.isSpecial()
    if n.getWire(): odb.dbWire.destroy(n.getWire())
    for g in list(n.getGuides()): odb.dbGuide.destroy(g)
(out/'changes.json').write_text(json.dumps(changes,indent=2)); (out/'affected_nets.txt').write_text('\n'.join(sorted(affected))+'\n')
odb.write_db(db,str(out/'soc_top.inserted.odb')); odb.write_def(b,str(out/'soc_top.inserted.def'))
print('Inserted',sum(x['action']=='insert' for x in changes),'moved',len(fix),'affected nets',len(affected))
