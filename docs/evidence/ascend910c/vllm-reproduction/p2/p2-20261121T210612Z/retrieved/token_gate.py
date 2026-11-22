import ast,json,sys,urllib.request,subprocess,pathlib,hashlib
p=pathlib.Path('.')
model='p1-vision1-20261121T205625Z-244b8fbf'
cid='1fdb00879533bb97ba7ef9f7bf7f64639a03e8b01bdfbdfe198b8a03fcf98a65'
def get(path,body=None):
 r=urllib.request.Request('http://127.0.0.1:18550'+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'})
 return json.load(urllib.request.urlopen(r,timeout=60))
m=get('/v1/models');p.joinpath('models.json').write_text(json.dumps(m));assert [x['id'] for x in m['data']]==[model]
for name,cmd in [('inspect',['docker','inspect',cid]),('top',['docker','top',cid,'-eo','pid,args']),('listener',['ss','-ltnp','sport = :18550'])]:
 p.joinpath(name+'.txt').write_bytes(subprocess.check_output(cmd))
assert '2227670' in p.joinpath('top.txt').read_text() and 'pid=2227670,' in p.joinpath('listener.txt').read_text()
sys.path.insert(0,str(p/'official1017/encoding'))
from encoding import encode_messages
source=ast.parse(p.joinpath('reference/tests/acc_eval.py').read_text()); scope={'json':json,'os':__import__('os'),'encode_messages':encode_messages,'re':__import__('re')}
scope['NUM']=__import__('re').compile(r'-?[\d,]*\.?\d+')
for node in source.body:
 if isinstance(node,ast.FunctionDef) and node.name in ['load_gsm8k','extract_gsm8k','norm_num','build_prompt']:
  exec(compile(ast.Module(body=[node],type_ignores=[]),'frozen','exec'),scope)
items=scope['load_gsm8k'](200,str(p/'gsm8k'));rows=[]
for it in items:
 prompt=scope['build_prompt'](it['prompt'],'chat'); body={'model':model,'prompt':prompt};resp=get('/tokenize',body); rows.append({'idx':it['idx'],'request':body,'response':resp});p.joinpath('tokenize.json').write_text(json.dumps(rows))
counts=[x['response']['count'] for x in rows];print(json.dumps({'min':min(counts),'max':max(counts),'over4096':sum(x>4096 for x in counts),'over_with512':sum(x+512>4096 for x in counts)}))
