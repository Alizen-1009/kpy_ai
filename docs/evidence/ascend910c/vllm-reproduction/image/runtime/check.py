import subprocess,json,pathlib,uuid,re
image='quay.nju.edu.cn/ascend/vllm-ascend@sha256:16a57b897a2f475f85b0e90df1644c9870c2418b368b2adf447c5173eae211c3'
def run(a): return subprocess.check_output(a,text=True)
x=json.loads(run(['docker','image','inspect',image]))[0]
assert not x['Config'].get('Volumes'), 'image declares volumes'
print(json.dumps({k:x[k] for k in ['Id','RepoDigests','Architecture','Size']}),flush=True)
print('SAFE_ENV',json.dumps([e for e in x['Config'].get('Env',[]) if e.split('=')[0] in ['PATH','LD_LIBRARY_PATH','PYTHONPATH','ASCEND_HOME_PATH','ASCEND_OPP_PATH']]),flush=True)
code=r'''import importlib.metadata as m,pathlib,subprocess,hashlib,json,ast
for n in ['torch','torch_npu','vllm','vllm-ascend','triton','numpy']:
 try: print('PACKAGE',n,m.version(n))
 except m.PackageNotFoundError: print('PACKAGE',n,'absent')
def emit(p):
 p=pathlib.Path(p)
 if not p.is_file(): print('ABSENT',str(p)); return
 b=p.read_bytes(); print('FILE',str(p),'SHA256',hashlib.sha256(b).hexdigest())
 if p.suffix in ['.py','.sh','.txt'] or p.name in ['profile','version.info','ascend_toolkit_install.info']:
  print('CONTENT',str(p),json.dumps(b.decode(errors='replace')[:400000]))
for root in ['/vllm-workspace/vllm','/vllm-workspace/vllm-ascend']:
 for args in [['rev-parse','HEAD'],['status','--porcelain','--untracked-files=no']]:
  p=subprocess.run(['git','-c','safe.directory='+root,'-C',root]+args,capture_output=True,text=True); print('GIT',root,args,p.returncode,p.stdout,p.stderr)
base=pathlib.Path('/vllm-workspace/vllm-ascend/vllm_ascend')
for rel in ['models/deepseek_v41','attention/dsa_v41.py','attention/dsa_v1.py','ascend_forward_context.py','ops/rope_dsv4.py','ops/fused_moe/token_dispatcher.py','core/deepseek_v41.py','worker/model_runner_v1.py','utils.py']:
 p=base/rel
 if p.is_dir():
  print('LAYOUT',str(p),[str(f.relative_to(p)) for f in p.rglob('*') if f.is_file()])
  for f in p.rglob('*.py'): emit(f)
 else: emit(p)
for p in [pathlib.Path('/etc/profile'),*pathlib.Path('/etc/profile.d').glob('*.sh')]:
 if p.is_file():
  print('PROFILE_SHA',str(p),hashlib.sha256(p.read_bytes()).hexdigest())
  print('PROFILE_INIT',str(p),[l for l in p.read_text(errors='replace').splitlines() if 'set_env' in l or 'profile.d' in l])
for root in ['/usr/local/Ascend','/vllm-workspace']:
 for p in pathlib.Path(root).rglob('*'):
  if not p.is_file(): continue
  if p.name=='set_env.sh': print('SET_ENV',str(p),str(p.resolve()))
  if p.name in ['BUILD_INFO.txt','version.info','ascend_toolkit_install.info'] or ('sdk' in str(p).lower() and p.name in ['version.txt','VERSION']): emit(p)
  if 'opp' in str(p).lower() and '.so' in p.name: print('OPP_SHA',str(p),hashlib.sha256(p.read_bytes()).hexdigest())
'''
cid=None
try:
 cid=run(['docker','create','--label','yh.image-audit='+uuid.uuid4().hex,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','2g','--cpus','2','--pids-limit','128','--entrypoint','python3',image,'-B','-c',code]).strip()
 assert re.fullmatch('[0-9a-f]{64}',cid)
 print('FULL_CID',cid,flush=True)
 r=subprocess.run(['docker','start','-a',cid],text=True,capture_output=True)
 print(r.stdout,flush=True); print('STDERR',r.stderr,flush=True)
 print('STATE',run(['docker','inspect','--format','{{json .State}}',cid]),flush=True)
 print('HOST_CONFIG',run(['docker','inspect','--format','{{json .HostConfig}}',cid]),flush=True)
finally:
 if cid and re.fullmatch('[0-9a-f]{64}',cid):
  print('STOP',run(['docker','stop',cid]),flush=True)
  print('REMOVE',run(['docker','rm',cid]),flush=True)
