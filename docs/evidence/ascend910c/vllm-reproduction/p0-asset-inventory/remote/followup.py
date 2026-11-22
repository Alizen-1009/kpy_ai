from pathlib import Path
import json,hashlib,subprocess
r=subprocess.run(['docker','image','inspect','quay.io/ascend/vllm-ascend:v0.30.0-a3','--format','{{.Id}} {{json .RepoDigests}} {{.Size}}'],capture_output=True,text=True); print(r.stdout,r.stderr)
root=Path('/root/yuhao/DeepSeek-V4.1-Flash-1017-HF')
for p in root.iterdir():
 if p.is_file() and p.stat().st_size<20000000 and any(x in p.name for x in ['token','config','index']): print('SMALL_METADATA_SHA256',p.name,p.stat().st_size,hashlib.sha256(p.read_bytes()).hexdigest())
idx=json.loads((root/'model.safetensors.index.json').read_text())['weight_map']
for term in ['engram','draft','vision','mtp']:
 keys=[k for k in idx if term in k.lower()]; print('KEY_GROUP',term,len(keys),keys[:5])
inv=json.loads(Path('/root/syf/v41_inventory_yf.json').read_text())
errors=[]
for f in inv['files']:
 p=Path(f['destination_yf'])
 if not p.exists() or p.stat().st_size!=f['Size']: errors.append((str(p),'missing/size mismatch'))
print('OFFICIAL_INVENTORY_SIZE_CHECK',len(inv['files']),errors)
for root in ['/root/yuhao/deepinfer_910c_yh','/usr/local/Ascend/cann/version.info','/usr/local/Ascend/cann/aarch64-linux/ascend_toolkit_install.info']:
 p=Path(root)
 if p.is_dir(): print('WORKSPACE_TOP',[(x.name,'dir' if x.is_dir() else 'file') for x in p.iterdir()])
 elif p.is_file(): print(root,p.read_text())
