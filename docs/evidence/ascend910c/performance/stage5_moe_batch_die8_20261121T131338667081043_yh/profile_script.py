#!/usr/bin/env python3
"""Alternating paired A/B on real replay input. Requires explicit approved candidate hash."""
import hashlib, importlib.util, inspect, json, os, runpy, sys, time
from pathlib import Path
import torch
import torch_npu
import deepinfer.quantization.fp4 as candidate
from deepinfer.quantization.activation import FP8Activation, swiglu_fp8_activation

REFERENCE_HASH='1100b1f8caca4ce65824829fdf19eeb25f9c003e05cde8cd5ad9c1fabc89534b'
reference_path=Path('/root/yuhao/deepinfer_910c_yh/scripts_yh/fp4_ab_reference_20261121/fp4_reference.py')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(reference_path)==REFERENCE_HASH
candidate_hash=sha(candidate.__file__)
assert candidate_hash==os.environ['FP4_APPROVED_CANDIDATE_SHA256'] and candidate_hash!=REFERENCE_HASH
spec=importlib.util.spec_from_file_location('frozen_fp4_reference',reference_path)
reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
functions={'reference':reference.fp4_expert_gemm_nt,'candidate':candidate.fp4_expert_gemm_nt}
report=Path(sys.argv[sys.argv.index('--report')+1]).parent/'fp4_ab.json'
assert not report.exists()
def digest(t): return hashlib.sha256(t.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()

def benchmark(*args,**kwargs):
    frame=inspect.currentframe().f_back;loc=frame.f_locals;outer=frame.f_back.f_locals
    assert int(outer['expert_id'])==124
    gu,dn=candidate.expert_operand(loc['gu'],0),candidate.expert_operand(loc['dn'],0)
    weight=loc['weights'][0,loc['choice']]
    base=args[0];results=[]
    for n in (1,8):
        a=FP8Activation(base.data[:n],base.scales[:n]); lanes={}
        for name,fn in functions.items():
            up=torch.empty((n,4608),dtype=torch.bfloat16,device='npu:0');out=torch.empty((n,5120),dtype=torch.bfloat16,device='npu:0')
            fn(a,gu,up)
            mid=swiglu_fp8_activation(up,topk_weights=weight.expand(n),clamp_value=loc['cfg'].swiglu_limit)
            fn(mid,dn,out)
            lanes[name]=(up,mid,out)
        checks={}
        for field,x,y in zip(('gate_up','mid_data','mid_scales','down'),(lanes['reference'][0],lanes['reference'][1].data,lanes['reference'][1].scales,lanes['reference'][2]),(lanes['candidate'][0],lanes['candidate'][1].data,lanes['candidate'][1].scales,lanes['candidate'][2])):
            checks[field]=dict(reference_sha256=digest(x),candidate_sha256=digest(y))
            assert checks[field]['reference_sha256']==checks[field]['candidate_sha256'],field+' bitwise mismatch'
        # Isolated down receives exactly the same reference-generated mid in both lanes.
        common_mid=lanes['reference'][1]
        def invoke(name,stage):
            fn=functions[name];up,mid,out=lanes[name]
            if stage=='gate_up':fn(a,gu,up)
            elif stage=='down':fn(common_mid,dn,out)
            else:
                fn(a,gu,up)
                mid=swiglu_fp8_activation(up,topk_weights=weight.expand(n),clamp_value=loc['cfg'].swiglu_limit)
                fn(mid,dn,out)
        stages={}
        for stage in ('gate_up','down','full_expert'):
            for name in functions:invoke(name,stage)
            torch.npu.synchronize();samples=[]
            for i in range(5):
                for name in (('reference','candidate') if i%2==0 else ('candidate','reference')):
                    b,e=torch.npu.Event(enable_timing=True),torch.npu.Event(enable_timing=True)
                    torch.npu.synchronize();torch.npu.reset_peak_memory_stats();t=time.perf_counter();b.record();invoke(name,stage);e.record();torch.npu.synchronize()
                    samples.append(dict(pair=i,lane=name,wall_seconds=time.perf_counter()-t,device_ms=b.elapsed_time(e),peak_allocated_bytes=torch.npu.max_memory_allocated(),peak_reserved_bytes=torch.npu.max_memory_reserved()))
            stages[stage]=samples
        results.append(dict(M=n,expert_id=124,activation_data_sha256=digest(a.data),activation_scales_sha256=digest(a.scales),checks=checks,stages=stages))
    root=Path(candidate.__file__).resolve().parents[2]
    result=dict(scope='same real expert124; M8 repeats single real token; not full MoE/EP8/model',reference_sha256=REFERENCE_HASH,candidate_sha256=candidate_hash,source_manifest={str(p.relative_to(root)):sha(p) for p in sorted((root/'deepinfer').rglob('*.py'))},snapshot_sha256=sha(sys.argv[sys.argv.index('--snapshot')+1]),torch=torch.__version__,torch_npu=torch_npu.__version__,results=results)
    with report.open('x') as f:json.dump(result,f,indent=2)
    print(json.dumps(result),flush=True);raise SystemExit(0)

candidate.fp4_expert_gemm_nt=benchmark
runpy.run_path(str(Path(__file__).with_name('check_official_moe_replay.py')),run_name='__main__')
