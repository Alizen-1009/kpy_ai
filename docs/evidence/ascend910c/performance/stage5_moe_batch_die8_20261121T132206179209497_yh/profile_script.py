#!/usr/bin/env python3
"""Bounded M1 shared+six-routed+combine AB, using unchanged replay construction.
Only harness source is adapted in memory; core modules remain untouched.
"""
import hashlib, importlib.util, json, os
from pathlib import Path
import torch
import torch_npu
HERE=Path(__file__).parent
REF=Path('/root/yuhao/deepinfer_910c_yh/scripts_yh/fp4_ab_reference_20261121/fp4_reference.py')
OLD='1100b1f8caca4ce65824829fdf19eeb25f9c003e05cde8cd5ad9c1fabc89534b'
NEW='58a7a16b9f67b54bad373f62764965b11fa4690021f1cd0cfa4048380f34f6a5'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(REF)==OLD
import deepinfer.quantization.fp4 as candidate
assert sha(candidate.__file__)==NEW==os.environ['FP4_APPROVED_CANDIDATE_SHA256']
spec=importlib.util.spec_from_file_location('frozen_fp4_ffn_reference',REF)
ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)

def run_block(a,banks,ids,weights,shared_up,shared_down,cfg,expected,report):
    import time
    from deepinfer.quantization.activation import swiglu_fp8_activation
    from deepinfer.quantization.fp4 import expert_operand
    def digest(t):return hashlib.sha256(t.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
    assert list(a.data.shape)==[1,5120]
    assert ids.cpu().tolist()==[[124,35,364,75,140,80]]
    order=sorted(range(6),key=lambda c:int(ids[0,c]))
    # Resolve metadata and allocate bounded output buffers outside timing.
    ops=[(expert_operand(g,0),expert_operand(d,0)) for g,d in banks]
    up=torch.empty((1,4608),dtype=torch.bfloat16,device='npu:0')
    routed=[torch.empty((1,5120),dtype=torch.bfloat16,device='npu:0') for _ in banks]
    route=[weights[0,i].expand(1) for i in range(6)]
    functions={'reference':ref.fp4_expert_gemm_nt,'candidate':candidate.fp4_expert_gemm_nt}
    def block(name):
        shared=shared_down(swiglu_fp8_activation(shared_up(a),clamp_value=cfg.swiglu_limit))
        for i,(gu,dn) in enumerate(ops):
            functions[name](a,gu,up)
            mid=swiglu_fp8_activation(up,topk_weights=route[i],clamp_value=cfg.swiglu_limit)
            functions[name](mid,dn,routed[i])
        total=torch.zeros_like(shared,dtype=torch.float32)
        for i in order:total.add_(routed[i].float())
        total.add_(shared.float())
        return total.bfloat16()
    for name in functions:block(name)
    torch.npu.synchronize();samples=[];outputs={}
    for pair in range(3):
        for name in (('reference','candidate') if pair%2==0 else ('candidate','reference')):
            b,e=torch.npu.Event(enable_timing=True),torch.npu.Event(enable_timing=True)
            torch.npu.synchronize();torch.npu.reset_peak_memory_stats();t=time.perf_counter();b.record();out=block(name);e.record();torch.npu.synchronize()
            samples.append(dict(pair=pair,lane=name,wall_seconds=time.perf_counter()-t,device_ms=b.elapsed_time(e),peak_allocated_bytes=torch.npu.max_memory_allocated(),peak_reserved_bytes=torch.npu.max_memory_reserved()))
            outputs[name]=out.detach().cpu()
    checks={name:digest(out) for name,out in outputs.items()}
    checks['captured_replay']=digest(expected)
    assert len(set(checks.values()))==1,checks
    root=Path(candidate.__file__).resolve().parents[2]
    result=dict(scope='M1 fixed real layer30 norm/router output: shared FP8 + six FP4 experts + weighted combine; excludes HC/norm/router/load/CPU oracle/EP8/decoder',samples=samples,output_hashes=checks,selected_ids=ids.cpu().tolist(),weights=weights.cpu().tolist(),input_data_sha256=digest(a.data),input_scales_sha256=digest(a.scales),reference_sha256=OLD,candidate_sha256=NEW,torch=torch.__version__,torch_npu=torch_npu.__version__,source_manifest={str(p.relative_to(root)):sha(p) for p in sorted((root/'deepinfer').rglob('*.py'))},resident_storage='all six original packed quantized experts plus shared quantized weights; no full expert decoded cache')
    with report.with_name('ffn_ab.json').open('x') as f:json.dump(result,f,indent=2)
    return result

source=(HERE/'check_official_moe_replay.py').read_text()
assert source.count('    del up,down\n')==1
source=source.replace('    del up,down\n','    banks=[]\n')
start=source.index('        one,ma,ya=stages(8)')
end=source.index('\n\ndef main():',start)
source=source[:start]+'''        banks.append((gu,dn))
    reader.close();torch.npu.synchronize()
    result=run_block(a,banks,ids,weights,up,down,cfg,snapshots['replay'][30]['hidden'],args.report)
    return dict(passed=True,benchmark_only=True,payload_bytes_read=read_bytes,payload_limit_bytes=192<<20,**result)
'''+source[end:]
exec(compile(source,str(HERE/'check_official_moe_replay.py'),'exec'),dict(__name__='__main__',run_block=run_block))
