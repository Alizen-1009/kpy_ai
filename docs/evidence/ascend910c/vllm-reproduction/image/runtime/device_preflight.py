"""Bounded authorized CLI-only device preflight. Never invokes serving."""
import pathlib,json,subprocess,shlex,uuid,sys,inspect
ROOT=pathlib.Path('/Users/alizen/Dev/kpy_ai'); sys.path.insert(0,str(ROOT))
from scripts.vllm_ascend_repro import launch,container_gate
OUT=pathlib.Path(__file__).parent
mapping=json.loads((OUT.parents[1]/'launch/runtime-map.json').read_text())
frozen=json.loads((OUT/'frozen-payload.json').read_text())
selected=[m for m in mapping['mounts'] if m['selected']]
mounts=[]
for m in selected:
 r=next(r for r in frozen if r['source']==m['source_relative_to_repo']); assert r['sha256']==m['sha256']
 mounts.append((r['destination'],m['destination'],r['sha256']))
probe=r'''import sys,runpy,traceback,importlib,json,ast,pathlib,os,re
failures=[]
sys.argv=['vllm','serve','--help']
try:
 runpy.run_module('vllm.entrypoints.cli.main',run_name='__main__')
except SystemExit as e:
 print('CLI_EXIT',e.code,flush=True)
 if e.code not in (0,None): failures.append('CLI')
except BaseException:
 traceback.print_exc(); failures.append('CLI')
for name in ['vllm_ascend.models.deepseek_v41.model','vllm_ascend.attention.dsa_v1']:
 try: importlib.import_module(name); print('ORDERED_IMPORT_OK',name,flush=True)
 except Exception: traceback.print_exc(); failures.append(name)
try:
 import torch
 from vllm_ascend.utils import enable_custom_op
 if not enable_custom_op(): failures.append('custom_op_registration')
 print('DEVICE_NODES',sorted(str(p) for p in pathlib.Path('/dev').glob('davinci*')),flush=True)
 for p in PAYLOADS:
  if not p.endswith('.py'): continue
  for n in ast.walk(ast.parse(pathlib.Path(p).read_text())):
   if isinstance(n,ast.Call) and re.fullmatch(r'torch\.ops\.\w+\.\w+',ast.unparse(n.func)):
    name=ast.unparse(n.func); print('PAYLOAD_CALL',p,n.lineno,ast.unparse(n),flush=True)
    try:
     op=torch.ops
     for bit in name.split('.')[2:]: op=getattr(op,bit)
     print('ACTUAL_SCHEMAS',name,str(op._schemas),flush=True)
    except Exception: traceback.print_exc(); failures.append(name)
 from vllm.model_executor.layers.quantization import get_quantization_config
 print('QUANTIZER_ASCEND',get_quantization_config('ascend'),flush=True)
 from vllm.tokenizers.registry import TokenizerRegistry
 print('TOKENIZER_REGISTRY',vars(TokenizerRegistry),flush=True)
except Exception: traceback.print_exc(); failures.append('registrations')
print('PROBE_FAILURES',json.dumps(failures),flush=True)
sys.exit(bool(failures))
'''
probe='PAYLOADS='+repr([m[1] for m in mounts])+'\n'+probe
remote=inspect.getsource(container_gate)+'\n' # strip module CLI guard before embedding
remote=remote[:remote.index('if __name__ == "__main__":')]
remote+='\n'+inspect.getsource(launch.require)+'\n'+inspect.getsource(launch.check_npu)
remote+='\nMOUNTS='+repr(mounts)+'\nPROBE='+repr(probe)+'\nRUN_ID='+repr('p1-device-'+uuid.uuid4().hex)+'\n'
remote+=r'''
import hashlib,pathlib,shlex,traceback
IMAGE='sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef'
def command(args):
 r=subprocess.run(args,capture_output=True,text=True); print('COMMAND',args,'EXIT',r.returncode,flush=True); print(r.stdout,r.stderr,flush=True); r.check_returncode(); return r.stdout
check_npu(command(['npu-smi','info']))
x=json.loads(command(['docker','image','inspect',IMAGE]))[0]
assert not x['Config'].get('Volumes')
env=dict(v.split('=',1) for v in x['Config']['Env'])
assert not any(k in env for k in ['LD_PRELOAD','LD_AUDIT','BASH_ENV','ENV'])
print('IMAGE_ENV_UNATTESTED',json.dumps(env),flush=True)
args=['docker','create','--label','owner=yuhao-vllm-repro','--label','run_id='+RUN_ID,'--network','none','--ipc','private','--security-opt','no-new-privileges','--memory','8g','--cpus','4','--pids-limit','512','--tmpfs','/tmp:rw,exec,nosuid,nodev,size=1073741824','--workdir','/tmp']
for k in ['LD_LIBRARY_PATH','PYTHONPATH']:
 if k in env: args+=['--env',k+'='+':'.join(v for v in env[k].split(':') if v)]
for k,v in {'HOME':'/tmp','XDG_CACHE_HOME':'/tmp/cache','TRITON_CACHE_DIR':'/tmp/triton','NUMBA_CACHE_DIR':'/tmp/numba','PYTHONDONTWRITEBYTECODE':'1','V41_ENGRAM_DEVICE_INDEX':'0','VLLM_BATCH_INVARIANT':'0'}.items(): args+=['--env',k+'='+v]
for d in sorted(DEVICES): args+=['--device',d+':'+d+':rwm']
for src,dst,sha in MOUNTS:
 assert pathlib.Path(src).is_file() and hashlib.sha256(pathlib.Path(src).read_bytes()).hexdigest()==sha
MOUNTS += [('/usr/local/Ascend/driver','/usr/local/Ascend/driver',None),('/etc/ascend_install.info','/etc/ascend_install.info',None)]
for src,dst,_ in MOUNTS:
 assert pathlib.Path(src).exists(); args+=['--mount','type=bind,src='+src+',dst='+dst+',readonly']
# Login initialization is retained; sanitize path components again after profile.
wrapper="import os; "+"; ".join("os.environ[%r]=':'.join(x for x in os.environ.get(%r,'').split(':') if x)"%(k,k) for k in ['LD_LIBRARY_PATH','PYTHONPATH'])+"; exec("+repr(PROBE)+")"
args+=['--entrypoint','/bin/bash',IMAGE,'-lc','exec python3 -B -u -c '+shlex.quote(wrapper)]
cid=None
try:
 check_npu(command(['npu-smi','info']))
 cid=command(args).strip(); assert re.fullmatch('[0-9a-f]{64}',cid)
 rec=json.loads(command(['docker','inspect',cid]))[0]
 # Docker tmpfs entries are separately validated; gate only permits bind entries.
 tmp=[m for m in rec['Mounts'] if m['Type']=='tmpfs']; assert all(m['Destination']=='/tmp' for m in tmp)
 checked=dict(rec); checked['Mounts']=[m for m in rec['Mounts'] if m['Type']!='tmpfs']
 errors=validate_inspect(checked,cid,IMAGE,RUN_ID,[m[0] for m in MOUNTS],[]); assert not errors,errors
 assert {(m['Source'],m['Destination'],m['RW']) for m in checked['Mounts']}=={(s,d,False) for s,d,_ in MOUNTS}
 h=rec['HostConfig']; assert h['NetworkMode']=='none' and h['IpcMode']=='private' and h['Memory']==8589934592 and h['NanoCpus']==4000000000 and h['PidsLimit']==512
 assert h['Tmpfs']=={'/tmp':'rw,exec,nosuid,nodev,size=1073741824'} and not h['ReadonlyRootfs'] and not h['CapDrop'] and 'no-new-privileges' in h['SecurityOpt']
 print('GATE_PASS',cid,flush=True)
 r=subprocess.run(['docker','start','-a',cid],capture_output=True,text=True,timeout=480); print('START_EXIT',r.returncode,flush=True); print(r.stdout,r.stderr,flush=True)
 command(['docker','inspect','--format','{{json .State}}',cid])
finally:
 if cid and re.fullmatch('[0-9a-f]{64}',cid):
  command(['docker','stop',cid]); command(['docker','rm',cid])
 command(['npu-smi','info'])
'''
with (OUT/('p1-device-preflight-'+uuid.uuid4().hex+'.log')).open('x') as f:
 r=subprocess.run(['ssh','910c','python3'],input=remote,text=True,stdout=f,stderr=subprocess.STDOUT)
print('SSH_EXIT',r.returncode)
