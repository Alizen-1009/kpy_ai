import ast,pathlib,json
root=pathlib.Path('/Users/alizen/Dev/kpy_ai'); here=pathlib.Path(__file__).parent
mapping=json.loads((here.parents[1]/'launch/runtime-map.json').read_text())
replaced={}
for m in mapping['mounts']:
 if m['selected'] and m['destination'].endswith('.py'):
  t=ast.parse((root/m['source_relative_to_repo']).read_text()); names=set()
  for n in t.body:
   if isinstance(n,(ast.FunctionDef,ast.ClassDef,ast.AsyncFunctionDef)): names.add(n.name)
   if isinstance(n,(ast.Import,ast.ImportFrom)): names.update(a.asname or a.name.split('.')[0] for a in n.names)
   if isinstance(n,ast.Assign): names.update(a.id for a in n.targets if isinstance(a,ast.Name))
  mod=m['destination'].split('/vllm-ascend/')[1][:-3].replace('/','.')
  replaced[mod]=(names,t)
for f in here.glob('*.py.source'):
 t=ast.parse(f.read_text()); mod=f.name.split('__vllm-ascend__')[-1][:-10].replace('__','.')
 if mod in replaced: continue
 for n in ast.walk(t):
  if isinstance(n,ast.ImportFrom) and n.module in replaced:
   missing=[a.name for a in n.names if a.name not in replaced[n.module][0]]
   print(f.name,n.lineno,n.module,[a.name for a in n.names],'MISSING',missing)
for mod,(names,t) in replaced.items():
 f=here/('/vllm-workspace/vllm-ascend/'+mod.replace('.','/')+'.py').replace('/','__')
 f=pathlib.Path(str(f)+'.source')
 if f.exists():
  old=ast.parse(f.read_text())
  def signatures(tree):
   out={}
   for n in ast.walk(tree):
    if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)): out[n.name]=ast.unparse(n.args)
   return out
  a,b=signatures(old),signatures(t)
  for k in a.keys() & b.keys():
   if a[k]!=b[k]: print('SIGNATURE',mod,k,'IMAGE',a[k],'PAYLOAD',b[k])
