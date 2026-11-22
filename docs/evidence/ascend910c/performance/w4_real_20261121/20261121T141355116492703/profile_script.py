"""Bounded real layer30 experiment, not production backend or quality acceptance."""
import torch, torch_npu, json, hashlib,time
from pathlib import Path
from w4a8_prototype import *
from quantization_error_metrics import compare_outputs
HERE=Path(__file__).parent
def digest(t):return hashlib.sha256(t.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes()).hexdigest()
def run_block(a,bf,banks,ids,weights,shared_up,shared_down,cfg,report):
 from deepinfer.quantization.activation import swiglu_fp8_activation
 from deepinfer.quantization.fp4 import expert_operand,fp4_expert_gemm_nt
 assert ids.cpu().tolist()==[[124,35,364,75,140,80]]
 ops=[(expert_operand(g,0),expert_operand(d,0)) for g,d in banks]
 artifact=[]; native=[]
 lut=torch.tensor([0,.5,1,1.5,2,3,4,6,-0.,-.5,-1,-1.5,-2,-3,-4,-6])
 for side in (0,1):
  entries=[]
  for pair in ops:
   op=pair[side]; raw=op.data.cpu().view(torch.uint8).long(); sf=op.scales.cpu().view(torch.uint8)
   scale=torch.pow(2.,sf.float()-127)
   decoded=(torch.stack((lut[raw%16],lut[raw//16]),-1).flatten(-2).reshape(raw.shape[0],-1,32)*scale[:,:,None]).flatten(-2).bfloat16()
   q,s=quantize_weight(decoded); entry=dict(codes=q,requested_scale=s,effective_scale=effective_weight_scale_910c(s),packed=pack_nd(q),decoded_hash=digest(decoded),code_saturation=float((q.abs()==7).float().mean()))
   entries.append(entry)
  artifact.append(entries)
  native.append((torch_npu.npu_format_cast(torch.stack([e['packed'] for e in entries]).npu(),29).view(torch.int32),torch.stack([scale_abi(e['requested_scale']) for e in entries])[:,None,:].npu()))
 artifact_path=report.with_name('derived_w4a8.pt');torch.save(dict(metadata=METADATA,weights=artifact,ids=ids.cpu(),input_bf16=bf.cpu()),artifact_path)
 gl=torch.ones(6,dtype=torch.int64,device='npu');route=weights[0,:,None];order=sorted(range(6),key=lambda i:int(ids[0,i]))
 def aq(x):
  f=x.float();mx=f.abs().amax(1);s=torch.where(mx==0,torch.ones_like(mx),mx/127);return torch.round(f/s[:,None]).clamp(-127,127).to(torch.int8),s
 def gmm(x,s,side):
  w,sc=native[side];return torch_npu.npu_grouped_matmul([x],[w],scale=[sc],per_token_scale=[s],bias=None,group_list=gl,group_list_type=1,group_type=0,split_item=2,output_dtype=torch.bfloat16)[0]
 def mid(up):
  g,u=up.float().chunk(2,1)
  if cfg.swiglu_limit is not None:g=g.clamp_max(cfg.swiglu_limit);u=u.clamp(-cfg.swiglu_limit,cfg.swiglu_limit)
  return (g/(torch.exp(-g)+1))*u*route
 saved={}
 def block(name,capture=False):
  shared=shared_down(swiglu_fp8_activation(shared_up(a),clamp_value=cfg.swiglu_limit))
  if name=='w4':
   x,s=aq(bf.repeat(6,1));u=gmm(x,s,0);mv=mid(u);z,zs=aq(mv);y=gmm(z,zs,1)
   if capture:saved.update(x=x.cpu(),s=s.cpu(),u=u.cpu(),z=z.cpu(),zs=zs.cpu(),y=y.cpu(),mid=mv.cpu())
  else:
   ys=[]
   for i,(gu,dn) in enumerate(ops):
    u=torch.empty((1,4608),dtype=torch.bfloat16,device='npu');v=torch.empty((1,5120),dtype=torch.bfloat16,device='npu');fp4_expert_gemm_nt(a,gu,u);fp4_expert_gemm_nt(swiglu_fp8_activation(u,topk_weights=weights[0,i].expand(1),clamp_value=cfg.swiglu_limit),dn,v);ys.append(v)
   y=torch.cat(ys)
  total=torch.zeros_like(shared,dtype=torch.float32)
  for i in order:total.add_(y[i:i+1].float())
  return (total+shared.float()).bfloat16()
 block('w4',True);checks=[]
 for side,an,sn,yn in [(0,'x','s','u'),(1,'z','zs','y')]:
  for i,e in enumerate(artifact[side]):
   oracle=device_matmul_oracle_910c(saved[an][i:i+1],saved[sn][i:i+1],e['codes'],e['requested_scale']);checks.append(dict(side=side,expert=int(ids[0,i]),exact=torch.equal(oracle,saved[yn][i:i+1]),metrics=compare_outputs(oracle,saved[yn][i:i+1])))
 result=dict(kernel_checks=checks,artifact=str(artifact_path),artifact_sha256=hashlib.sha256(artifact_path.read_bytes()).hexdigest(),input_hash=digest(bf),metadata=METADATA,quality_pass=None)
 if not all(c['exact'] for c in checks):
  report.with_name('w4_ffn.json').write_text(json.dumps(result,indent=2));raise RuntimeError('Real kernel oracle mismatch; timed comparison not authorized')
 samples=[];outs={}
 for pair in range(3):
  for name in (('fp4','w4') if pair%2==0 else ('w4','fp4')):
   torch.npu.synchronize();torch.npu.reset_peak_memory_stats();b,e=torch.npu.Event(enable_timing=True),torch.npu.Event(enable_timing=True);st=time.perf_counter();b.record();out=block(name);e.record();torch.npu.synchronize();samples.append(dict(pair=pair,lane=name,wall_seconds=time.perf_counter()-st,event_ms=b.elapsed_time(e),peak_allocated=torch.npu.max_memory_allocated()));outs[name]=out.cpu()
 result.update(samples=samples,fp4_vs_w4=compare_outputs(outs['fp4'],outs['w4']),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),saturation={n:float((saved[n].abs()==127).float().mean()) for n in ('x','z')})
 report.with_name('w4_ffn.json').write_text(json.dumps(result,indent=2));return result
source=(HERE/'check_official_moe_replay.py').read_text().replace('    del up,down\n','    banks=[]\n')
start=source.index('        one,ma,ya=stages(8)');end=source.index('\n\ndef main():',start)
source=source[:start]+'''        banks.append((gu,dn))
    reader.close();torch.npu.synchronize()
    return run_block(a,bf,banks,ids,weights,up,down,cfg,args.report)
'''+source[end:]
exec(compile(source,str(HERE/'check_official_moe_replay.py'),'exec'),dict(__name__='__main__',run_block=run_block))
