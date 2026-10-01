from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess, os
root=Path(__file__).resolve().parents[2]
cs=[r+'_'+p for r in ('nom','min','max') for p in ('tt_025C_1v80','ss_100C_1v60','ff_n40C_1v95')]
def run(c):
    env=dict(os.environ,ECO4O_CORNER=c)
    with open(root/f'eco4o_slewfix/logs/top_newcpu_eco4o_baseline_{c}.log','w') as f:
        subprocess.run(['sta','-exit',str(Path(__file__).with_name('analyze_sram_slew.tcl'))],env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
    print(c,flush=True)
with ThreadPoolExecutor(max_workers=3) as pool: list(pool.map(run,cs))
