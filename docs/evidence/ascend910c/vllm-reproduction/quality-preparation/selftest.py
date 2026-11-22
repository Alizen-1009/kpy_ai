"""Offline synthetic scorer controls, never model results."""
import importlib.util,json,copy,sys,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
R=P/'reference'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
s=load('scoring',R/'experiments/operator_stack/parallel_tiny/dspark_general_quality_api_cpu/scoring.py')
gold,sha=s.canonical_gold(P/'gsm8k')
doc={'summary':{'served_model':'synthetic','task':'gsm8k','mode':'chat','n':100,'correct':100,'empty':0,'errors':0,'gsm8k_jsonl_sha256':sha},'results':[{'idx':f'gsm8k-{i}','ok':True,'err':None,'raw':'#### '+g,'gold':g} for i,g in enumerate(gold)]}
assert s.check_gsm100(doc,'synthetic',gold,sha)['strict_GSM100_passed']
negatives=0
for kind in ['wrong','empty','duplicate','model']:
 d=copy.deepcopy(doc)
 if kind=='wrong':d['results'][0]['raw']='#### -999999'
 if kind=='empty':d['results'][0]['raw']=''
 if kind=='duplicate':d['results'][1]['idx']='gsm8k-0'
 if kind=='model':d['summary']['served_model']='other'
 try:s.check_gsm100(d,'synthetic',gold,sha)
 except ValueError:negatives+=1
 else:raise AssertionError(kind)
v=subprocess.run([sys.executable,str(R/'tests/vision_accuracy_check.py'),'--self-test'],capture_output=True,text=True)
assert v.returncode==0,v.stdout+v.stderr
w=load('workloads',R/'experiments/delivery_matrix/workloads.py')
counts={t.task_id:len(w.fixed_unit_cases(t.task_id)) for t in w.CODE_TASKS}
assert len(counts)==8 and sum(counts.values())==128
(P/'selftest-result.json').write_text(json.dumps({'scope':'offline synthetic scorer controls only; no model inference','gsm_positive':100,'gsm_negative_controls_rejected':negatives,'vision_selftest_stdout':v.stdout,'vision_exit':v.returncode,'code_case_counts':counts,'code_sandbox_execution':'NOT RUN'},indent=2)+'\n')
print('PASS: GSM synthetic100 + 4 negatives, Vision built-in self-test, Code8/128 inventory')
