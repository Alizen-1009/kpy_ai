import os,json,glob,hashlib,subprocess
from pathlib import Path
print('NUMA')
for p in glob.glob('/sys/devices/system/node/node*/meminfo')+glob.glob('/sys/devices/system/node/node*/cpulist'): print(p,Path(p).read_text())
roots=['/root/yuhao/DeepSeek-V4.1-Flash-1017-HF','/root/syf/data_yf/DeepSeek-V4.1-Flash-1017-original_yf','/root/syf/data_yf/DeepSeek-V4-Flash-0731-w8a8','/root/syf/data_yf/DeepSeek-V4-Flash-w8a8-mtp','/data2/syf/DeepSeek-V4.1-Flash-1017-original_yf']
for root in roots:
 print('\nMODEL',root)
 for p in sorted(Path(root).iterdir()):
  print('ENTRY',p.name,p.stat().st_size,'dir' if p.is_dir() else 'file')
  if p.is_file() and p.stat().st_size<20000000 and (p.name.startswith(('config','quant','model.safetensors.index','tokenizer_config'))):
   b=p.read_bytes(); print('SHA256',p.name,hashlib.sha256(b).hexdigest())
   try: d=json.loads(b)
   except: continue
   if 'weight_map' in d:
    shards=sorted(set(d['weight_map'].values())); print('INDEX',len(d['weight_map']),len(shards), 'missing',[s for s in shards if not (Path(root)/s).is_file()]); print('SHARDS',[(s,(Path(root)/s).stat().st_size if (Path(root)/s).exists() else None) for s in shards]); print('ENGRAM/DRAFT/VISION_KEYS',[k for k in d['weight_map'] if any(t in k.lower() for t in ['engram','draft','vision'])][:100])
   else: print('CONFIG',json.dumps(d))
print('\nEXPLICIT INVENTORY')
for f in ['/root/syf/v41_download_status_yf.json','/root/syf/README_v41_download_yf.txt','/root/syf/v41_inventory_yf.json']:
 p=Path(f)
 if p.exists():
  b=p.read_bytes(); print(f,'SHA256',hashlib.sha256(b).hexdigest()); print(b.decode())
print('\nBOUNDED SOURCE/MODEL LOCATIONS')
for root in ['/root/yuhao/deepinfer_910c_yh/src_yh','/root/syf/data_yf/models','/root/syf/data_yf/hf_cache']:
 for path,dirs,files in os.walk(root):
  depth=len(Path(path).relative_to(root).parts)
  print(path,'DIRS',dirs)
  if '.git' in dirs or '.git' in files:
   for args in [['rev-parse','HEAD'],['status','--short']]:
    r=subprocess.run(['git','--no-optional-locks','-C',path]+args,capture_output=True,text=True); print(args,r.stdout,r.stderr)
   dirs[:]=[]
  else: dirs[:]=[d for d in dirs if not d.startswith('.') and depth<2]
print('OPP HOST')
for p in glob.glob('/usr/local/Ascend/cann/*/opp/vendors/*')+glob.glob('/usr/local/Ascend/cann/opp/vendors/*'): print(p)
