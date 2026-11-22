"""Local-only variant builder and bounded AST inventory. Never starts a service."""
import ast, copy, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[6]
BASE=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path(__file__).resolve().parent
REF=ROOT/'ref/deepseek-v4.1-flash-ascend910B'
IMAGE=BASE.parent/'image/runtime'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v): (OUT/n).write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
b=json.loads((BASE/'runtime-map.json').read_text())
head=subprocess.check_output(['git','-C',str(REF),'rev-parse','HEAD'],text=True).strip()
report=json.loads((IMAGE/'runtime_report.json').read_text())
g=copy.deepcopy(b)
g['scope']='Restoration candidate GRAPH1 SPEC0; not executed or runtime-certified'
g['provenance']={'reference_head':head,'base_map_sha256':sha(BASE/'runtime-map.json'),'image_id':report['image_id'],'prerequisite_report':str((IMAGE/'runtime_report.json').relative_to(ROOT)),'prerequisite_report_sha256':sha(IMAGE/'runtime_report.json'),'note':'Original report only covers original payload; not variant certification'}
g['environment_whitelist'].update(GRAPH='1',EAGER='0',DRAFT_GRAPH='0',CAPTURE_SIZES='1',DSPARK_GRAPH_CAPTURE_METADATA='0')
g['additional_payloads']=[]
g['pending_gates']=['Rehash all selected payloads and inspect actual image/environment; isolated environment only','Validate generated CLI JSON and graph config against pinned image','Authorized isolated launch only after other agent finishes; no concurrent use of occupied dies','Observe FULL_DECODE_ONLY capture and replay; no fallback accepted as graph proof','Run real short generation, GSM, Vision and Code regression; capture errors or degradation stop rollout']
g['runtime_report']=None
save('graph-runtime-map.json',g)
d=copy.deepcopy(g); d['scope']='Restoration candidate DSpark K5 GRAPH1 DRAFT_GRAPH1; not runtime-certified'
d['environment_whitelist'].update(SPEC='1',SP_TOKENS='5',SPEC_EAGER='0',DRAFT_GRAPH='1',CAPTURE_SIZES='1,2,3,4,6',DSPARK_GRAPH_CAPTURE_METADATA='1',DSPARK_DRAFT_USE_CUDAGRAPH='1',DSPARK_DRAFT_METADATA_MODE='sync',DSPARK_CAPTURE_VALUE_FIX='1',DSPARK_SWA_INDICES_RESIDENT='1',DSPARK_CAPTURE_NCTX_FIX='1',DSPARK_DISPATCH_QUERY_LEN_FIX='1',DSPARK_RT_FLAGS='0',DSPARK_GRAPH_DEVICE_METADATA='0')
imports=[]
for name,dest in [('dsa_v1.py','attention'),('dspark_proposer.py','spec_decode'),('llm_base_proposer.py','spec_decode')]:
 p=REF/'patches/files/draft'/name
 frozen=subprocess.check_output(['git','-C',str(REF),'show',f'{head}:patches/files/draft/{name}'])
 assert frozen==p.read_bytes(),f'non-HEAD draft payload: {p}'
 target=f'/vllm-workspace/vllm-ascend/vllm_ascend/{dest}/{name}'
 m={'source_relative_to_ref':str(p.relative_to(REF)),'source_relative_to_repo':str(p.relative_to(ROOT)),'destination':target,'sha256':sha(p),'mode':'ro','selected':True,'classification':'draft-graph-required-replacement'}
 d['mounts']=[x for x in d['mounts'] if x['destination']!=target]+[m]
 d['additional_payloads'].append(m)
 tree=ast.parse(p.read_text())
 for node in ast.walk(tree):
  if isinstance(node,ast.ImportFrom):
   module=node.module or ''; capture=IMAGE/('__vllm-workspace__vllm-ascend__'+module.replace('.','__')+'.py.source')
   selected=next((x for x in d['mounts'] if x['selected'] and x['destination'].endswith('/'+module.replace('.','/')+'.py')),None)
   provider=ROOT/selected['source_relative_to_repo'] if selected else capture
   names=[a.name for a in node.names]
   status='not-captured: image dependency, must verify before DSpark launch'
   if provider.exists():
    t=ast.parse(provider.read_text()); symbols={n.name for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef))}
    status='selected payload' if selected else 'captured image source'
    status+='; definitions present: '+','.join(n for n in names if n in symbols)+'; others may be imports/constants'
   imports.append({'payload':name,'line':node.lineno,'module':module,'names':names,'status':status})
d['pending_gates']+=['Resolve uncaptured imports in import-audit.json using only same fixed image sources, not new main','Check live three draft hashes; dspark_proposer contains DSPARK_GRAPH_CAPTURE_METADATA and container env equals 1','Check actual SPEC_EAGER=false and four fixes enabled; no /tmp flags override','Guard: 8 serial samples minimum acceptance A >=1.3; two A=1.00 and accepted throughput=0 readings fail immediately; run official draft_graph_guard only after increasing MAX_SEQS/capture coverage to 8']
save('dspark-runtime-map.json',d);save('import-audit.json',imports)
# Record concrete captured Engram interfaces without importing torch/NPU.
interfaces=[]
for p in [REF/'patches/files/model.py',*IMAGE.glob('*model.py.source'),*IMAGE.glob('*model_runner_v1.py.source')]:
 t=ast.parse(p.read_text())
 for n in ast.walk(t):
  if isinstance(n,ast.FunctionDef) and n.name=='prepare_engram_inputs': interfaces.append({'source':str(p.relative_to(ROOT)),'sha256':sha(p),'line':n.lineno,'signature':ast.unparse(n.args)})
save('graph-interface-audit.json',interfaces)
print('Wrote independent variants; base map unchanged')
