# 最小 eager runtime map

仅本地只读抽取；未 SSH、未修改 ref、未核验镜像或运行 NPU。JSON 是组装输入。

## 挂载（所有新 launcher 挂载建议只读；旧脚本部分为 rw，但本分支不修改载荷）
| source（相对 ref） | container destination | 采用 | SHA256 |
|---|---|---|---|
| patches/files/engram_hbm.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/engram_hbm.py | True | f8a762a93b932bbf655cc8edea20c637655d0579775f2aeceb5bdd6653401269 |
| patches/files/engram_hash.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/engram_hash.py | True | acf1aa4a9a75eef5ebe6dbf69bbeb8dd9195797c739ecc46751e3a79776ff4a8 |
| patches/files/engram_jit_kernel.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/engram_jit_kernel.py | True | 1394bbe7e9752a0bcf3cc177f3ff3baf10c9c1d6847569855f5d5ed5237f38cf |
| patches/files/engram_plan_kernel.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/engram_plan_kernel.py | True | 87fd738eeb8c69d363d01105de1bb7067acc714e8d8e98739f146b6c547e8117 |
| patches/files/engram_gate.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/engram_gate.py | True | 955e40b94e933aabddb37035ec295e701bdfe3c12fef586a6b7ba775a05e90a2 |
| patches/files/model.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/model.py | True | dfbc3c0d3b0f9ce3349509de5dfb3799a47f834eec26a951769bf4a54e6c022b |
| patches/files/ascend_forward_context.py | /vllm-workspace/vllm-ascend/vllm_ascend/ascend_forward_context.py | True | eb8442f593c11d666743c18b0936e64a302e53b2d0972c691706b179efb3bdee |
| patches/files/rope_dsv4.py | /vllm-workspace/vllm-ascend/vllm_ascend/ops/rope_dsv4.py | True | 25151bcf62e49e1c1db780718eb7c29322c51767bf15693b46fe7b34ed3ba981 |
| patches/files/dsa_v1.py | /vllm-workspace/vllm-ascend/vllm_ascend/attention/dsa_v1.py | True | f2633fd764203b14beff046a8029b48f4585d57df38914895be1cd432f41612c |
| patches/files/token_dispatcher_moemask.py | /vllm-workspace/vllm-ascend/vllm_ascend/ops/fused_moe/token_dispatcher.py | True | 37f96f834b98e257b5b82eaab607c451199b191c9c01078f61213c4e592fc9b8 |
| patches/files/engram_device_index.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/engram_device_index.py | False | 4c9a29e3e37c0170ab8b349dc4996aaf0d488ad375b7dc400589d9cc906ca7f4 |
| patches/files/engram_graph.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/engram_graph.py | False | 14c14f0b24e2ba96caf424a187035e24947d81b28bba8de9bbc7eab6c886e962 |
| patches/files/device_metadata.py | /vllm-workspace/vllm-ascend/vllm_ascend/worker/device_metadata.py | False | e8c707ed91abcbce535ca196f461d4da301f8f7029fdd22f222d2c9a3e15f25a |
| patches/files/block_table.py | /vllm-workspace/vllm-ascend/vllm_ascend/worker/block_table.py | False | f92dea34393f4264999ff94038e68e28c7cf98d577c11c49e45c3609dbc0e286 |
| patches/files/indexer.py | /vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/indexer.py | False | 0c447a246ee3e3d1399cf992beecef19ab22528cb4c1153abfe2b74f3d1a048e |
| patches/files/patch_cudagraph.py | /vllm-workspace/vllm-ascend/vllm_ascend/patch/worker/patch_cudagraph.py | False | b85d998e22a523fd5da354033a080d7ebb7759e59f75d2d788b3089c9be272cb |
| scripts/serve_v2.sh | /opt/dsv41/scripts/serve_v2.sh | True | 814ef3abd53d7413653e2e2ac7c0b0bef83becff461996f93414de0a17106114 |
| patches/admission_gate.patch | /opt/dsv41/admission_gate.patch | False | 81b47593d6462c12e20c1b94dc811b85d1613586c5a447622e983230b003fda4 |

## 必需性边界
保留 10 个无条件 baseline Python payload，不声称它们都是“任意版本必需”。model/Engram 是配对实现；其余保留旧 mount 分支兼容面、关闭优化门控。版本必需性须由镜像源码/API 对照确定，当前不能凭版本号猜测。跳过项理由逐项见 JSON。SPEC0 不挂 draft，GRAPH0 不挂 dynamic-spec；不恢复已撤销 model_runner_v1。

## 补丁命令
本分支无需 git apply。admission gate 可跳过，设 VLLM_ADMISSION_GATE=0；原幂等应用命令仅作为可选记录写入 JSON。

## CANN
原脚本没有显式 CANN source 命令，依赖 bash -lc 登录环境。下一步只读镜像需读取 entrypoint/profile，确认真实 set_env.sh；不能把惯用路径冒充抽取事实。

## 调用和 ENV
JSON environment_whitelist 固定关闭 graph/spec/CPU binding/loaderMT/多流/MC2/融合/实验。禁止继承任意宿主 ENV；同时审查镜像 ENV。LOAD_FORMAT 为空，不能 dummy。MAX_SEQS=1 等为新 launcher 明示选择，非性能结论。
`cd /workspace; exec bash /opt/dsv41/scripts/serve_v2.sh`
serve_v2 会自行加入 --enable-expert-parallel、--trust-remote-code、--enforce-eager、ascend quantization；不会加 DP 参数（DP1）、spec config 或 loaderMT config。它可能自动 LD_PRELOAD jemalloc，不是 PGO。

## 无 NPU 镜像核验
- Record image digest, architecture, image ENV/entrypoint/cmd, BUILD_INFO.txt; git HEAD for /vllm-workspace/vllm and /vllm-workspace/vllm-ascend; package metadata for torch, torch_npu, vllm, vllm-ascend and CANN versions.
- For every selected destination: test regular file (new modules may be absent), inspect parent, hash original, verify import dependencies without importing NPU runtime. Flat models/deepseek_v41 layout is required; upstream refactor to engram/ package is incompatible (AGENTS 5b.2).
- Inspect unmounted attention/dsa_v41.py, models/deepseek_v41/indexer.py, core/deepseek_v41.py, worker/model_runner_v1.py, utils.py and custom operator shared libraries; verify API compatibility with mounted payload. No exact image compatibility established locally.
- Verify deepseek_v4 tokenizer registration, ascend quantization support and CLI options from serve_v2.sh; real model config/weight manifest and Engram int8 files must match.
- No NPU devices, no model execution, no git apply in verification container. Read-only container can inspect sources, hashes, package metadata and shell initialization.
