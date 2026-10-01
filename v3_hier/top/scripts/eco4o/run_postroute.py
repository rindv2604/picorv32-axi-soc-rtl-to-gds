from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess, os
scripts=Path(__file__).resolve().parent; out=Path(os.environ['ECO4O_ITER_DIR'])
def run(args,env,log,marker=None):
    with open(log,'w') as f: subprocess.run(args,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    txt=Path(log).read_text()
    if ('Error' in txt or '[ERROR' in txt) or (marker and marker not in txt): raise RuntimeError(f'Inspect {log}')
def rcx(rc):
    run(['openroad','-exit',str(scripts/'eco4o_extract.tcl')],dict(os.environ,ECO4O_RC=rc),out/f'rcx_{rc}.log','ECO4O_EXTRACTION_COMPLETE'); print('extracted',rc,flush=True)
with ThreadPoolExecutor(max_workers=3) as p: list(p.map(rcx,['nom','min','max']))
cs=[r+'_'+p for r in ('nom','min','max') for p in ('tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95')]
def sta(c):
    run(['sta','-exit',str(scripts/'analyze_sram_slew.tcl')],dict(os.environ,ECO4O_CORNER=c),out/f'sta_{c}.log','TIMING_COUNTS'); print('STA',c,flush=True)
with ThreadPoolExecutor(max_workers=3) as p: list(p.map(sta,cs))
