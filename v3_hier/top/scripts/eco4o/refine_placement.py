"""Move only remaining failing terminal stages closer, allowing local data-cell repacking."""
import odb,os,json,csv,math
from pathlib import Path
root=Path(__file__).resolve().parents[2];src=Path(os.environ['ECO4O_SOURCE_DIR']);out=Path(os.environ['ECO4O_ITER_DIR']);out.mkdir(exist_ok=True)
db=odb.dbDatabase.create();odb.read_db(db,str(src/'soc_top.routed.odb'));b=db.getChip().getBlock();u=b.getDbUnitsPerMicron()
remaining=json.loads((src/'remaining_pins.json').read_text());macro=b.findInst('ram.u_sram_macro');targets=[]
for name in remaining:
 t=macro.findITerm(name.split('/')[-1]);_,x,y=t.getAvgXY();n=t.getNet();ds=[d for d in n.getITerms() if d.getIoType()=='OUTPUT'];assert len(ds)==1
 targets.append((t,ds[0].getInst(),x,y))
original={i.getName():dict(location=i.getLocation(),orient=str(i.getOrient()),status=str(i.getPlacementStatus())) for i in b.getInsts()}
movable=set();removed=[]
for i in list(b.getInsts()):
 if i.isBlock() or i.getMaster().getType()=='CORE_WELLTAP':continue
 x,y=i.getLocation();local=any(abs(x-sx)<55*u and abs(y-sy)<65*u for _,_,sx,sy in targets)
 if not local:continue
 if i.getMaster().getType()=='CORE_SPACER' or '__decap_' in i.getMaster().getName():
  removed.append(i.getName());odb.dbInst.destroy(i);continue
 # Preserve CTS placement; only data cells can be repacked.
 if i.getName().startswith(('clkbuf','clkload')) or any(t.getNet() and t.getNet().getSigType()=='CLOCK' for t in i.getITerms()):continue
 movable.add(i.getName())
fixed={}
def rect(i):
 r=i.getBBox();return (r.xMin(),r.yMin(),r.xMax(),r.yMax())
terminal={i.getName() for _,i,_,_ in targets}
for i in b.getInsts():
 if i.getName() in movable and i.getName() not in terminal:i.setPlacementStatus('PLACED')
 else:
  i.setPlacementStatus('FIRM')
  if i.getName() not in terminal:fixed[i.getName()]=rect(i)
placements=[]
for t,i,sx,sy in targets:
 w=i.getMaster().getWidth();h=i.getMaster().getHeight();opts=[]
 for row in b.getRows():
  r=row.getBBox();y=r.yMin();step=row.getSpacing()
  if abs(y-sy)>50*u or row.getSite().getHeight()!=h or step<=0:continue
  for k in range(max(0,math.ceil((sx-50*u-r.xMin())/step)),min(row.getSiteCount()-math.ceil(w/step),math.floor((sx+50*u-r.xMin())/step))+1):
   x=r.xMin()+k*step
   if any(x<q[2] and x+w>q[0] and y<q[3] and y+h>q[1] for q in fixed.values()):continue
   opts.append((abs(x+w*.7-sx)+abs(y+h*.5-sy),x,y,str(row.getOrient())))
 if not opts:raise RuntimeError('No local fixed target site '+i.getName())
 _,x,y,o=min(opts);i.setOrient(o);i.setLocation(x,y);i.setPlacementStatus('FIRM');fixed[i.getName()]=rect(i)
 placements.append(dict(instance=i.getName(),pin=t.getMTerm().getName(),location=[x,y],orient=o))
(out/'placement_plan.json').write_text(json.dumps(dict(original=original,removed=removed,terminal_placements=placements,movable=sorted(movable)),indent=2))
odb.write_db(db,str(out/'soc_top.seed.odb'));print('Seeded',len(targets),'terminal stages; locally movable',len(movable),'removed physical fillers/decaps',len(removed))
