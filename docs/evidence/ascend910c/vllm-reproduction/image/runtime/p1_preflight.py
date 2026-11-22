import pathlib,json,hashlib,subprocess,shlex,uuid,ast
root=pathlib.Path('/Users/alizen/Dev/kpy_ai'); out=pathlib.Path(__file__).parent
mp=json.loads((out.parents[1]/'launch/runtime-map.json').read_text()); selected=[x for x in mp['mounts'] if x['selected']]
assert len(selected)==11
runid=uuid.uuid4().hex; remote='/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/payload/preflight_'+runid
subprocess.run(['ssh','910c','mkdir -p '+shlex.quote(remote)],check=True)
records=[]; specs=[]
for m in selected:
 b=(root/m['source_relative_to_repo']).read_bytes(); assert hashlib.sha256(b).hexdigest()==m['sha256']
 name=pathlib.Path(m['source_relative_to_repo']).name; dest=remote+'/'+name
 subprocess.run(['ssh','910c','umask 077; test ! -e '+shlex.quote(dest)+' && dd of='+shlex.quote(dest)+' status=none && chmod 444 '+shlex.quote(dest)],input=b,check=True)
 got=subprocess.check_output(['ssh','910c','sha256sum '+shlex.quote(dest)],text=True).split()[0]; assert got==m['sha256']
 records.append(dict(source=m['source_relative_to_repo'],destination=dest,sha256=got))
 specs.extend(['--mount','type=bind,src='+dest+',dst='+m['destination']+',readonly'])
(out/'frozen-payload.json').write_text(json.dumps(records,indent=2))
probe=r'''import ast,pathlib,json,subprocess,os,importlib
print('LOGIN_ENV',json.dumps({k:os.environ.get(k) for k in ['ASCEND_HOME_PATH','ASCEND_OPP_PATH','LD_LIBRARY_PATH','PYTHONPATH']}))
base=pathlib.Path('/vllm-workspace/vllm-ascend/vllm_ascend')
paths=[base/'models/deepseek_v41'/n for n in ['engram_hbm.py','engram_hash.py','engram_jit_kernel.py','engram_plan_kernel.py','engram_gate.py','model.py']]+[base/n for n in ['ascend_forward_context.py','ops/rope_dsv4.py','attention/dsa_v1.py','ops/fused_moe/token_dispatcher.py']]
ops=set()
for p in paths:
 t=ast.parse(p.read_text()); compile(t,str(p),'exec'); print('COMPILE_OK',str(p))
 for n in ast.walk(t):
  if isinstance(n,(ast.Import,ast.ImportFrom)): print('IMPORT_AST',str(p),n.lineno,ast.unparse(n))
  if isinstance(n,ast.Call) and ast.unparse(n.func).startswith('torch.ops.'):
   print('OP_CALL',str(p),n.lineno,ast.unparse(n)); ops.add(ast.unparse(n.func))
roots=[pathlib.Path('/vllm-workspace/vllm'),pathlib.Path('/vllm-workspace/vllm-ascend')]
needles={x.split('.')[-1] for x in ops}|{'deepseek_v4','AscendConfig','ascend_quant','--tokenizer-mode','--default-chat-template-kwargs'}
for r in roots:
 for f in r.rglob('*'):
  if f.suffix not in ['.py','.cpp','.h'] or '.git' in f.parts: continue
  try: lines=f.read_text(errors='replace').splitlines()
  except OSError: continue
  for i,l in enumerate(lines):
   if any(n in l for n in needles): print('DEFINITION_OR_USE',str(f),i+1,l[:800])
for p in paths:
 module='vllm_ascend.'+str(p.relative_to(base))[:-3].replace('/','.')
 r=subprocess.run(['python3','-B','-c','import importlib; importlib.import_module('+repr(module)+')'],capture_output=True,text=True,timeout=90)
 print('IMPORT_RESULT',module,r.returncode,r.stdout[-3000:],r.stderr[-6000:])
r=subprocess.run(['python3','-B','-m','vllm.entrypoints.cli.main','serve','--help'],capture_output=True,text=True,timeout=90)
print('CLI_HELP_RESULT',r.returncode,r.stdout[-30000:],r.stderr[-6000:])
'''
remote_code="""import subprocess,json,re
image='sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef'
x=json.loads(subprocess.check_output(['docker','image','inspect',image]))[0]
env={v.split('=',1)[0]:v.split('=',1)[1] for v in x['Config'].get('Env',[])}
safe={'PATH','LD_LIBRARY_PATH','PYTHONPATH','ASCEND_HOME_PATH','ASCEND_OPP_PATH','LANG','LC_ALL','HOME','DEBIAN_FRONTEND','TZ','PYTHONUNBUFFERED','PIP_DISABLE_PIP_VERSION_CHECK','ASCEND_TOOLKIT_HOME','ASCEND_AICPU_PATH','TOOLCHAIN_HOME','ASCEND_SLOG_PRINT_TO_STDOUT','LIBRARY_PATH','CPLUS_INCLUDE_PATH','C_INCLUDE_PATH'}
print('IMAGE_ENV_REVIEW',json.dumps({k:{'status':'review-path-or-setting' if k in safe else 'UNREVIEWED_REDACTED','value':v if k in safe else '<redacted>'} for k,v in env.items()}),flush=True)
assert not x['Config'].get('Volumes')
cid=None
try:
 args=['docker','create','--label',LABEL,'--network','none','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges','--memory','4g','--cpus','2','--pids-limit','128']+MOUNTS+['--entrypoint','/bin/bash',image,'-lc','python3 -B -c '+__import__('shlex').quote(PROBE)]
 cid=subprocess.check_output(args,text=True).strip(); assert re.fullmatch('[0-9a-f]{64}',cid)
 print('FULL_CID',cid,flush=True)
 r=subprocess.run(['docker','start','-a',cid],capture_output=True,text=True,timeout=1000)
 print(r.stdout,flush=True); print(r.stderr,flush=True)
 print('STATE',subprocess.check_output(['docker','inspect','--format','{{json .State}}',cid],text=True),flush=True)
 print('HOST_CONFIG',subprocess.check_output(['docker','inspect','--format','{{json .HostConfig}}',cid],text=True),flush=True)
finally:
 if cid and re.fullmatch('[0-9a-f]{64}',cid):
  print('STOP',subprocess.check_output(['docker','stop',cid],text=True),flush=True)
  print('REMOVE',subprocess.check_output(['docker','rm',cid],text=True),flush=True)
"""
remote_code='LABEL='+repr('yh.p1-preflight='+runid)+'\nMOUNTS='+repr(specs)+'\nPROBE='+repr(probe)+'\n'+remote_code
with (out/'p1-preflight.log').open('w') as f: subprocess.run(['ssh','910c','python3'],input=remote_code,text=True,stdout=f,stderr=subprocess.STDOUT,check=True)
