"""CPU stdlib only: execute captured real loader, no tensors/payload/NPU."""
import ast,json
from pathlib import Path
from types import SimpleNamespace
p=Path(__file__).parent
src=ast.parse((p/'vl_model.py').read_text())
f=next(n for n in src.body if isinstance(n,ast.FunctionDef) and n.name=='_vision_parameter_name')
c=next(n for n in src.body if isinstance(n,ast.ClassDef))
l=next(n for n in c.body if isinstance(n,ast.FunctionDef) and n.name=='load_weights')
ns={}
def loader(param,weight): assert param==weight,(param,weight)
ns['default_weight_loader']=loader
exec(compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),f,l],type_ignores=[])),'captured-loader','exec'),ns)
d=json.loads((p/'model-header.json').read_text()); weights=[(k,v['shape']) for k,v in d['headers'].items()]
class Language:
 def load_weights(self,ws): return {k for k,v in ws}
for enabled in (False,True):
 params=dict(weights) if enabled else {}
 obj=SimpleNamespace(named_parameters=lambda:params.items(),language_model=Language())
 try:
  result=ns['load_weights'](obj,weights)
  assert enabled and result==set(params)
  print('enabled: PASS all',len(result),'vision tensors strictly matched')
 except KeyError as e:
  assert not enabled and "Vision weight 'aligner.w1.bias' has no parameter 'aligner.w1.bias'." in str(e)
  print('disabled: reproduced',e)
for k in ('aligner.w1.weight','aligner.w1.bias','aligner.w2.weight','aligner.w2.bias'): print(k,d['headers'][k]['shape'])
