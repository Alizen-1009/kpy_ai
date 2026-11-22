import pathlib,json,urllib.request,urllib.parse,hashlib,datetime
P=pathlib.Path(__file__).resolve().parent
files=json.loads((P.parent/'model-files.json').read_text())
rev='50029772e7757c3d9cec50481661091b369af901'
names=['README.md','config.json','configuration.json','engram_int8/PARTS.sha256','engram_int8/reassemble_engram_weights.sh','mtpq_manifest.json','quant_model_description.json','quant_model_weights.safetensors.index.json','tokenizer.json','tokenizer_config.json','release/reports/quant-repro-validation.md','release/reports/quant-repro-accuracy.md','release/msmodelslim/recipes/deepseek_v4_1_flash_w4a8.yaml']
selected=[x for x in files if x['Path'] in names]
assert len(selected)==len(names) and all(x['Size']<=32*1024**2 for x in selected) and sum(x['Size'] for x in selected)<=128*1024**2
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
records=[]
for x in selected:
 url='https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend/repo?'+urllib.parse.urlencode({'Revision':rev,'FilePath':x['Path']})
 dest=P/x['Path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():
  data=dest.read_bytes();status='verified-existing'
 else:
  with opener.open(url,timeout=90) as r:
   assert r.status==200
   data=r.read(x['Size']+1);status=r.status
 assert len(data)==x['Size'] and hashlib.sha256(data).hexdigest()==x['Sha256'], x['Path']
 if not dest.exists():
  tmp=dest.with_name(dest.name+'.part');tmp.write_bytes(data);tmp.rename(dest)
 records.append(dict(x,url=url,status=status,verified_sha256=hashlib.sha256(data).hexdigest(),utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
 (P/'downloads.json').write_text(json.dumps(records,indent=2)+'\n')
 print(x['Path'],len(data),flush=True)
