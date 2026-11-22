import json,hashlib
from probe import ROOT
raw=json.loads((ROOT/'ms-pinned-files.body').read_text())
assert raw['Success']
files=raw['Data']['Files']; blobs=[f for f in files if f['Type']=='blob']
manifest=[{k:f.get(k) for k in ('Path','Size','Sha256','Revision','IsLFS')} for f in blobs]
(ROOT/'model-files.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
parts=[f for f in blobs if '.part-' in f['Path']]
image=json.loads((ROOT/'quay-arm64.body').read_text())
summary={'revision':'50029772e7757c3d9cec50481661091b369af901','api_data_keys':list(raw['Data']),'file_count':len(blobs),'directory_count':len(files)-len(blobs),'total_bytes':sum(f['Size'] for f in blobs),'missing_sha256':[f['Path'] for f in blobs if len(f['Sha256'])!=64],'engram_parts_bytes':sum(f['Size'] for f in parts),'engram_parts_count':len(parts),'image_layer_bytes':sum(f['size'] for f in image['layers']),'master_same_files':files==json.loads((ROOT/'ms-files-direct.body').read_text())['Data']['Files']}
for name,path in [('ms-readme','README.md'),('ms-reassemble','engram_int8/reassemble_engram_weights.sh')]:
 f=next(f for f in blobs if f['Path']==path); summary[name+'_hash_matches']=hashlib.sha256((ROOT/(name+'.body')).read_bytes()).hexdigest()==f['Sha256']
(ROOT/'summary.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
