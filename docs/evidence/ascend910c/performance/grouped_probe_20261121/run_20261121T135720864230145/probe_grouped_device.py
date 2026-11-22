import torch, torch_npu, time, traceback, json, hashlib
from pathlib import Path
print(json.dumps(dict(torch=torch.__version__,torch_npu=torch_npu.__version__,sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())),flush=True)
torch.npu.set_device(0)
torch.manual_seed(42)
for k,n in [(256,256),(5120,4608),(2304,5120)]:
 for counts in [[1,0,0],[1,0,7]]:
  for nz in [False,True]:
   r=dict(k=k,n=n,counts=counts,nz=nz)
   try:
    m=sum(counts); q=torch.randint(-8,8,(3,k,n),dtype=torch.int8); a=torch.randint(-127,128,(m,k),dtype=torch.int8)
    s=0.0001+torch.rand((3,1,n),dtype=torch.float32)*0.031; t=0.0001+torch.rand((m,),dtype=torch.float32)*0.037
    packed=((q[:,:,::2].to(torch.int16)&15)|((q[:,:,1::2].to(torch.int16)&15)<<4)).to(torch.int8).contiguous().npu()
    if nz: packed=torch_npu.npu_format_cast(packed,29)
    packed=packed.view(torch.int32)
    sc=(s.view(torch.int32).to(torch.int64)&0xffffffff).npu(); assist=(8*q.float().sum(1)*s[:,0]).npu()
    x=a.npu(); ts=t.npu(); gl=torch.tensor(counts,dtype=torch.int64).npu()
    def run(): return torch_npu.npu_grouped_matmul([x],[packed],scale=[sc],bias=None,per_token_scale=[ts],group_list=gl,group_list_type=1,group_type=0,split_item=2,output_dtype=torch.bfloat16)[0]
    torch.npu.synchronize(); st=time.perf_counter(); y=run(); torch.npu.synchronize(); r['first_wall_ms']=(time.perf_counter()-st)*1000
    b=torch.npu.Event(enable_timing=True); e=torch.npu.Event(enable_timing=True); b.record(); st=time.perf_counter()
    for _ in range(5): y=run()
    e.record(); torch.npu.synchronize(); r['wall_ms']=(time.perf_counter()-st)*1000/5; r['event_ms']=b.elapsed_time(e)/5
    off=0; refs=[]; refs32=[]
    for i,c in enumerate(counts):
     acc=a[off:off+c].to(torch.int64)@q[i].to(torch.int64)
     refs.append(acc.double()*s[i].double()*t[off:off+c,None].double())
     refs32.append(acc.float()*s[i]*t[off:off+c,None]); off+=c
    ref=torch.cat(refs).bfloat16().float(); ref32=torch.cat(refs32).bfloat16().float(); out=y.cpu().float()
    ulp=torch.maximum(ref.abs(),torch.tensor(torch.finfo(torch.bfloat16).tiny)).log2().floor().sub(7).exp2()
    r['nonfinite']=int((~torch.isfinite(out)).sum()); r['fp64_bf16_max_ulp']=((out-ref).abs()/ulp).max().item(); r['fp32_max_abs']=(out-ref32).abs().max().item(); r['fp32_equal']=torch.equal(out,ref32); r['fp32_fp64_rounding_count']=int((ref32!=ref).sum()); r['within_one_bf16_ulp']=bool(r['nonfinite']==0 and r['fp64_bf16_max_ulp']<=1)
    r['output_head']=out.flatten()[:8].tolist(); r['ref_head']=ref.flatten()[:8].tolist(); r['max_abs']=(out-ref).abs().max().item(); r['exact_bf16_oracle']=torch.equal(out,ref); r['peak_allocated']=torch.npu.max_memory_allocated(); r['format']=torch_npu.get_npu_format(packed)
   except Exception: r['error']=traceback.format_exc()
   print(json.dumps(r),flush=True)
