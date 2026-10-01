import odb,os,json
from pathlib import Path
out=Path(os.environ['ECO4O_ITER_DIR']);db=odb.dbDatabase.create();odb.read_db(db,str(out/'soc_top.legalized.odb'));b=db.getChip().getBlock();plan=json.loads((out/'placement_plan.json').read_text());affected=set();changes=[]
for i in b.getInsts():
 old=plan['original'].get(i.getName())
 if old is None:
  changes.append(dict(action='insert',instance=i.getName(),cell=i.getMaster().getName(),old_xy=None,new_xy=i.getLocation(),reason='Split long capacitive branch'))
  affected.update(t.getNet().getName() for t in i.getITerms() if t.getNet() and t.getSigType()=='SIGNAL')
 elif i.getLocation()!=old['location'] or str(i.getOrient())!=old['orient']:
  changes.append(dict(action='move',instance=i.getName(),cell=i.getMaster().getName(),old_xy=old['location'],new_xy=i.getLocation(),reason='Local repacking to reduce failing SRAM branch RC'))
  for t in i.getITerms():
   if t.getNet() and t.getSigType()=='SIGNAL':affected.add(t.getNet().getName())
 if old is not None:i.setPlacementStatus(old['status'])
for name in sorted(affected):
 n=b.findNet(name);assert not n.isSpecial()
 if n.getWire():odb.dbWire.destroy(n.getWire())
 for g in list(n.getGuides()):odb.dbGuide.destroy(g)
(out/'affected_nets.txt').write_text('\n'.join(sorted(affected))+'\n');(out/'changes.json').write_text(json.dumps(changes,indent=2));odb.write_db(db,str(out/'soc_top.inserted.odb'));odb.write_def(b,str(out/'soc_top.inserted.def'))
print('Moved',len(changes),'cells; reroute',len(affected),'signal nets')
