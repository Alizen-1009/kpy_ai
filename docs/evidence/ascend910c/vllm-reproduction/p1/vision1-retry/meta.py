import torch,json
from types import SimpleNamespace
from vllm_ascend.models.deepseek_v4.vision import DeepseekV4ViT,DeepseekV4Aligner
p=json.load(open('/evidence/model-header.json')); v=p['config']['vision_config']
c=SimpleNamespace(vision_n_layers=v['num_hidden_layers'],vision_dim=v['hidden_size'],vision_n_heads=v['num_attention_heads'],vision_inter_dim=v['intermediate_size'],vision_patch_size=v['patch_size'],vision_rope_theta=v['rope_theta'],vision_downsample_ratio=v['downsample_ratio'],hidden_size=p['config']['text_config']['hidden_size'])
from vllm.config import VllmConfig, DeviceConfig, set_current_vllm_config
with set_current_vllm_config(VllmConfig(device_config=DeviceConfig(device='cpu'))), torch.device('meta'):
 m=torch.nn.Module();m.vision=DeepseekV4ViT(c);m.aligner=DeepseekV4Aligner(c)
 for n in ('image_start','image_end','image_newline'): m.register_parameter(n,torch.nn.Parameter(torch.empty(c.hidden_size,dtype=torch.float32)))
a={n:list(t.shape) for n,t in m.named_parameters()}
h={n:d['shape'] for n,d in p['headers'].items()}
assert len(a)==len(h)==266,(len(a),len(h))
assert a==h,{'missing':list(h.keys()-a.keys()),'extra':list(a.keys()-h.keys()),'mismatch':{n:(a[n],h[n]) for n in a.keys()&h.keys() if a[n]!=h[n]}}
assert all(t.device.type=='meta' for t in m.parameters())
print(json.dumps({'status':'passed','actual_tower_constructors':True,'wrapper_constructor':False,'parameters':a,'count':266,'generation_test':False}))
