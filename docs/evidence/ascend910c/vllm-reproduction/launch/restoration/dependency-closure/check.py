"""AST evidence only: no imports from inspected files, no runtime certification."""
import ast, hashlib, json, pathlib, subprocess, inspect
R=pathlib.Path(__file__).resolve().parent
repo=R.parents[6]
mp=json.loads((R.parent/'dspark-runtime-map.json').read_text())
manifest=json.loads((R/'sources.json').read_text())
mods={}
for f in manifest['files']:
    p=R/f['file']; assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256']
    mods['vllm_ascend.'+f['file'][8:-3].replace('/','.')]=ast.parse(p.read_text())
ref=repo/'ref/deepseek-v4.1-flash-ascend910B'
assert subprocess.check_output(['git','-C',str(ref),'rev-parse','HEAD'],text=True).strip()=='ab88ff84efa7970875f3f8cc38dfcb06c491b154'
report=[]
for m in mp['mounts']:
    if pathlib.Path(m['destination']).name not in ['dspark_proposer.py','llm_base_proposer.py','dsa_v1.py']: continue
    p=repo/m['source_relative_to_repo']; data=p.read_bytes()
    assert hashlib.sha256(data).hexdigest()==m['sha256']
    rel=p.relative_to(ref)
    assert data==subprocess.check_output(['git','-C',str(ref),'show','HEAD:'+str(rel)])
    tree=ast.parse(data); imports={}
    for n in ast.walk(tree):
        if isinstance(n,ast.ImportFrom) and n.module in mods:
            definitions={x.name:x for x in mods[n.module].body if isinstance(x,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef))}
            for a in n.names:
                definition=definitions.get(a.name); imports[a.asname or a.name]=definition
                report.append(dict(payload=p.name,line=n.lineno,module=n.module,symbol=a.name,status='definition-found' if definition else 'BLOCKING missing direct definition (check reexports)',signature=ast.unparse(definition.args) if isinstance(definition,(ast.FunctionDef,ast.AsyncFunctionDef)) else None))
    for n in ast.walk(tree):
        if isinstance(n,ast.Call):
            fun=n.func.value if isinstance(n.func,ast.Subscript) else n.func
            if isinstance(fun,ast.Name) and fun.id in imports:
                d=imports[fun.id]; item=dict(payload=p.name,line=n.lineno,call=ast.unparse(n),status='requires runtime/type validation')
                constructor=isinstance(d,ast.ClassDef)
                if constructor:
                    d=next((v for v in d.body if isinstance(v,ast.FunctionDef) and v.name=='__init__'),None)
                if isinstance(d,ast.FunctionDef):
                    item['signature']=ast.unparse(d.args)
                    if not any(isinstance(v,ast.Starred) for v in n.args) and all(k.arg for k in n.keywords):
                        a=d.args; params=[]; positional=a.posonlyargs+a.args
                        defaults=[inspect.Parameter.empty]*(len(positional)-len(a.defaults))+[None]*len(a.defaults)
                        for i,(arg,default) in enumerate(zip(positional,defaults)):
                            if constructor and i==0: continue
                            params.append(inspect.Parameter(arg.arg,inspect.Parameter.POSITIONAL_ONLY if i<len(a.posonlyargs) else inspect.Parameter.POSITIONAL_OR_KEYWORD,default=default))
                        if a.vararg: params.append(inspect.Parameter(a.vararg.arg,inspect.Parameter.VAR_POSITIONAL))
                        for arg,default in zip(a.kwonlyargs,a.kw_defaults): params.append(inspect.Parameter(arg.arg,inspect.Parameter.KEYWORD_ONLY,default=None if default is not None else inspect.Parameter.empty))
                        if a.kwarg: params.append(inspect.Parameter(a.kwarg.arg,inspect.Parameter.VAR_KEYWORD))
                        try:
                            inspect.Signature(params).bind(*([None]*len(n.args)),**{k.arg:None for k in n.keywords if k.arg not in {'num_warps','num_stages','enable_fp_fusion'}})
                            item['status']='AST argument binding passes; runtime/types unverified'
                        except TypeError as e: item.update(status='BLOCKING argument binding',error=str(e))
                    args=d.args; allowed={a.arg for a in args.args+args.kwonlyargs}; keys={k.arg for k in n.keywords if k.arg}
                    extra=keys-allowed-{'num_warps','num_stages','enable_fp_fusion','launch_cooperative_grid'}
                    if extra and not args.kwarg: item.update(status='BLOCKING unexpected keywords',unexpected=sorted(extra))
                report.append(item)
        if isinstance(n,ast.Attribute) and ('context' in ast.unparse(n.value).lower()):
            report.append(dict(payload=p.name,line=n.lineno,context_access=ast.unparse(n),status='field inventory; not runtime availability proof'))
(R/'ast-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('entries',len(report)); print(json.dumps([x for x in report if x.get('status','').startswith('BLOCKING')],indent=2))
