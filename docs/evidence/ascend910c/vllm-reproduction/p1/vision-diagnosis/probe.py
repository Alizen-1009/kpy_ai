import json, struct
from pathlib import Path
p=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/model')
c=json.loads((p/'config.json').read_text()); idx=json.loads(next(p.glob('*.safetensors.index.json')).read_text())['weight_map']
keys={k:v for k,v in idx.items() if k.startswith(('aligner.','vision.','image_'))}
headers={}
for f in set(keys.values()):
 with (p/f).open('rb') as s:
  n=struct.unpack('<Q',s.read(8))[0]; assert n<32*1024*1024
  headers[f]=json.loads(s.read(n))
print(json.dumps({'config':c,'vision_index':keys,'headers':{k:headers[f][k] for k,f in keys.items()}},indent=2))
