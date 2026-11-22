"""Close bounded runtime prerequisites from retained evidence, not model execution."""
import hashlib,json,re
from pathlib import Path
D=Path(__file__).parent
R=D.parents[5]
M=D.parents[1]/'launch/runtime-map.json'
log=D/'cli-help-preflight-f3d1f0a4f91543b896ca326e33b40b1e.log'
s=log.read_text()
image=json.JSONDecoder().raw_decode(s[s.index('[\n',s.index("COMMAND ['docker', 'image', 'inspect'")):])[0][0]
env=dict(v.split('=',1) for v in image['Config']['Env'])
flags='host port served-model-name tensor-parallel-size enable-expert-parallel trust-remote-code dtype kv-cache-dtype max-model-len max-num-seqs max-num-batched-tokens block-size gpu-memory-utilization additional-config quantization enforce-eager no-enable-prefix-caching safetensors-load-strategy limit-mm-per-prompt tokenizer-mode default-chat-template-kwargs'.split()
help_lines=s.splitlines()[763:2632]
evidence={}
for flag in flags:
 hits=[(i+764,line.strip()) for i,line in enumerate(help_lines) if re.search(r'--'+re.escape(flag)+r'(?:\s|,|$)',line)]
 assert hits,flag
 evidence['--'+flag]=hits
assert 'CLI_EXIT 0' in s and 'START_EXIT 0' in s
assert not any(k in env for k in ['LD_PRELOAD','LD_AUDIT','BASH_ENV','ENV'])
assert all(env[k].startswith('/usr/local/Ascend/') for k in ['ASCEND_HOME_PATH','ASCEND_OPP_PATH','ATB_HOME_PATH','TOOLCHAIN_HOME','ASCEND_TOOLKIT_HOME','ASCEND_TOOLKIT_LATEST_HOME','ASCEND_AICPU_PATH'])
review={k:('Absolute vendor/system search directories; empty components tracked separately.' if k in ['PATH','LD_LIBRARY_PATH','PYTHONPATH','CMAKE_PREFIX_PATH'] else 'Vendor SDK location; no credential or executable injection.' if k.endswith('_PATH') or k.endswith('_HOME') else 'Non-secret build/runtime tuning scalar; reviewed exact retained value.') for k in env}
paths=['DEVICE-RETRY.md','RESULT.md','audit.log','supplement.log','interfaces.txt','p1-device-preflight-9fb7c6664deb4e47a9428d10bb43118a.log',log.name,'cli_help_preflight.py']
report=dict(schema_version=1,image_id=image['Id'],runtime_map_sha256=hashlib.sha256(M.read_bytes()).hexdigest(),cann_login_verified=True,payload_api_verified=True,image_environment_verified=True,reviewed_image_env=env,mapping={'4':[8,9],'5':[10,11],'6':[12,13],'7':[14,15]},evidence_scope='Bounded pre-model runtime prerequisites only: login initialization, selected frozen payload imports and seven structural operator schemas, CLI option availability and JSON syntax, reviewed image environment. Not model/kernel correctness, full launch argv parsing, capacity, or deployment readiness.',evidence_paths=['docs/evidence/ascend910c/vllm-reproduction/image/runtime/'+p for p in paths],evidence_sha256={p:hashlib.sha256((D/p).read_bytes()).hexdigest() for p in paths},environment_review=review,search_path_risks={'raw_empty_components':[k for k in ['PATH','LD_LIBRARY_PATH','PYTHONPATH'] if '' in env[k].split(':')],'mitigation':'launch.py fixed post-login Python bootstrap now removes LD_LIBRARY_PATH/PYTHONPATH empty components before exec frozen serve_v2.sh (source reviewed). Raw image values are unchanged. PATH in image has no empty component; general post-profile PATH risk is not claimed eliminated. Bootstrap is not real-model validation.'},cli_review={'method':'One fresh-idle same device_preflight lifecycle with --help=all only, no repeated schema/registry probes, no model mounts or service. Full CID stop/rm exit0; container exit0, OOMKilled false. Static flag/value review against full help; not complete argv parse. JSON enable_thinking=false is valid JSON object.','selected_flag_help_lines':evidence,'parameters':{'MAX_LEN':'4096','GPU_UTIL':'0.85','TP':'8','DP':'1','tokenizer-mode':'deepseek_v4','quantization':'ascend'}},provenance={'vllm_commit':'6e448d0ea9bf3d88d898b65449ca6dc2aec170ac','vllm_ascend_commit':'e43cf1e9f5d9bead076853aa6bcacb671465de94','OPP':'Component versions and shared-library hashes retained in audit.log; BUILD_INFO absent in bounded search, not a permanent blocker.'},remaining_p1=['Actual model/Engram manifest, resolved symlink targets and complete weight hashes','Tokenizer semantic match to actual metadata (registration already proven)','Model configuration-dependent validation, loading, tensor shapes/dtypes and real kernel execution','HCCL/TP8 communication, memory capacity, first generation correctness and output quality'])
(D/'runtime_report.json').write_text(json.dumps(report,indent=2)+'\n')
print('runtime_report.json',report['runtime_map_sha256'],len(env),'image ENV keys')
