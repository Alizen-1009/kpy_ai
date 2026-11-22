"""Anonymous bounded public GSM download and reference source freeze; no inference."""
from pathlib import Path
import urllib.request, hashlib, json, shutil
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
REF=ROOT/'ref/deepseek-v4.1-flash-ascend910B'
files=['LICENSE','tests/acc_eval.py','tests/vision_accuracy_check.py','experiments/delivery_matrix/workloads.py','experiments/delivery_matrix/benchmark.py','experiments/operator_stack/parallel_tiny/dspark_general_quality_api_cpu/scoring.py','experiments/operator_stack/parallel_tiny/dspark_general_quality_api_cpu/evidence/evaluator_sources.json','tools/ced_pd_acceptance.py']
records=[]
for name in files:
 p=REF/name
 if not p.exists():
  records.append({'path':name,'available':False});continue
 dst=HERE/'reference'/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dst)
 records.append({'path':name,'available':True,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
base='https://raw.githubusercontent.com/openai/grade-school-math/master/'
total=0
for remote,local in [('LICENSE','LICENSE'),('grade_school_math/data/train.jsonl','train.jsonl'),('grade_school_math/data/test.jsonl','test.jsonl')]:
 cached=HERE/'gsm8k'/local
 if cached.exists(): data=cached.read_bytes()
 else:
  with urllib.request.urlopen(base+remote,timeout=60) as r: data=r.read(100*1024*1024-total+1)
 total+=len(data)
 if total>100*1024*1024:raise RuntimeError('download budget exceeded')
 if local=='LICENSE' and b'MIT License' not in data:raise RuntimeError('license mismatch')
 dst=HERE/'gsm8k'/local;dst.parent.mkdir(exist_ok=True);dst.write_bytes(data)
 records.append({'url':base+remote,'path':'gsm8k/'+local,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
(HERE/'assets.json').write_text(json.dumps({'download_bytes':total,'files':records},indent=2)+'\n')
