import odb,json,hashlib,os
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=Path(os.environ['ECO4O_ITER_DIR'])
def load(p):
 d=odb.dbDatabase.create();odb.read_db(d,str(p));return d,d.getChip().getBlock()
d0,b0=load(root/'eco4m_antennafix/soc_top.eco4m_drt.odb');d1,b1=load(out/'soc_top.routed.odb')
modified=[];inserted=[];removed=[];badpg=[]
for i in b1.getInsts():
 old=b0.findInst(i.getName())
 if not old:inserted.append(i.getName())
 elif old.getMaster().getName()!=i.getMaster().getName() or old.getLocation()!=i.getLocation() or old.getOrient()!=i.getOrient(): modified.append(i.getName())
 if i.getName().startswith('eco4o_'):
  for pin,net in [('VPWR','VPWR'),('VPB','VPWR'),('VGND','VGND'),('VNB','VGND')]:
   t=i.findITerm(pin)
   if not t or not t.getNet() or t.getNet().getName()!=net:badpg.append(i.getName()+'/'+pin)
for i in b0.getInsts():
 if not b1.findInst(i.getName()):removed.append(i.getName())
macros={}
for name in ['cpu','ram.u_sram_macro']:
 a=b0.findInst(name);b=b1.findInst(name);macros[name]=dict(unchanged=a.getLocation()==b.getLocation() and a.getOrient()==b.getOrient() and a.getMaster().getName()==b.getMaster().getName(),location=b.getLocation(),orient=str(b.getOrient()))
unrouted=[]
for n in b1.getNets():
 if n.getSigType() not in ('POWER','GROUND') and len(n.getITerms())+len(n.getBTerms())>1 and not n.getWire():unrouted.append(n.getName())
# isDisconnected is OpenDB's router connectivity flag, supplemented by DRT log checks.
disconnected=[n.getName() for n in b1.getNets() if n.isDisconnected()]
data=dict(inserted=inserted,modified=modified,removed=removed,macro_checks=macros,bad_pg_connections=badpg,signal_nets_without_wire=unrouted,disconnected_flags=disconnected)
(out/'revision_audit.json').write_text(json.dumps(data,indent=2));print(json.dumps({k:v if k=='macro_checks' else len(v) for k,v in data.items()},indent=2))
