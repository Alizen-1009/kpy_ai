"""Bounded CPU oracle enumeration; synthetic only; no weights loaded."""
import torch, torch_npu, json, hashlib
from pathlib import Path
print(json.dumps({'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'torch':torch.__version__,'torch_npu':torch_npu.__version__}),flush=True)
torch.npu.set_device(0); torch.manual_seed(731)
def trunc_bf(x): return (x.contiguous().view(torch.int32)&-65536).view(torch.float32)
for k in (64,256):
 for mode in ('weight','token','both'):
  m,n=8,256
  a=torch.zeros(m,k,dtype=torch.int8)
  for i in range(m): a[i,i]=i*17-63
  q=torch.zeros(k,n,dtype=torch.int8); q[:m]=torch.randint(-8,8,(m,n),dtype=torch.int8)
  s=torch.ones(n) if mode=='token' else torch.rand(n)*0.1+0.001
  t=torch.ones(m) if mode=='weight' else torch.rand(m)*0.1+0.001
  acc=(a.to(torch.int64)@q.to(torch.int64)).float(); S=s[None];T=t[:,None]
  variants={'fp64':(acc.double()*S.double()*T.double()).float(),'fp32_st':acc*S*T,'fp32_ts':acc*T*S}
  for dtype in (torch.bfloat16,torch.float16):
   def rnd(x): return x.to(dtype).float()
   tag=str(dtype)
   variants.update({tag+'_intermediate_st':rnd(acc*S)*T,tag+'_intermediate_ts':rnd(acc*T)*S,tag+'_scales':acc*rnd(S)*rnd(T),tag+'_product':acc*rnd(S*T),tag+'_s':acc*rnd(S)*T,tag+'_t':acc*S*rnd(T),tag+'_acc':rnd(acc)*S*T})
  variants.update({'truncate_s':acc*trunc_bf(S)*T,'truncate_t':acc*S*trunc_bf(T),'truncate_st':trunc_bf(acc*S)*T,'truncate_ts':trunc_bf(acc*T)*S,'truncate_output':trunc_bf(acc*S*T)})
  packed=((q[:,::2].short()&15)|((q[:,1::2].short()&15)<<4)).to(torch.int8)[None].npu()
  packed=torch_npu.npu_format_cast(packed,29).view(torch.int32)
  scale=(s.view(torch.int32).long()&0xffffffff).reshape(1,1,n).npu()
  out=torch_npu.npu_grouped_matmul([a.npu()],[packed],scale=[scale],bias=None,per_token_scale=[t.npu()],group_list=torch.tensor([m],dtype=torch.int64).npu(),group_list_type=1,group_type=0,split_item=2,output_dtype=torch.bfloat16)[0].cpu().float()
  comparisons={name:{'different':int((v.bfloat16().float()!=out).sum()),'max_abs':float((v.bfloat16().float()-out).abs().max())} for name,v in variants.items()}
  print(json.dumps({'k':k,'mode':mode,'a':a.tolist(),'q':q[:m].tolist(),'q_remaining_rows_zero':True,'s':s.tolist(),'t':t.tolist(),'out':out.tolist(),'comparisons':comparisons}),flush=True)
