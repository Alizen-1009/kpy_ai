# P1 — executed, failed during model loading

Run: `p1-20261121T203514Z-4f842308`.
Exact CID: `67993945c3595dc9bc76bbddc429c2c4d7d49be7cadd5b3d4b1bdbd7795e3525`.
Remote run directory: `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/runs_yh/p1-20261121T203514Z-4f842308`.
Remote evidence: `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/logs/p1-20261121T203514Z-4f842308` (copied here).

All staged hashes match staging attestation; local hashes match except the permitted newer downloader. Staged tools were not overwritten. Fresh launcher NPU check passed; available RAM 1054633906176 bytes and disk 153534373888 bytes; port 18550 unused. Original flat frozen payload was copied into a new unique payload tree with runtime-map-relative directories, hash checked and chmod 444; originals unchanged.

Actual complete launch argv is in run evidence `argv.json`. Launcher executed create → inspect gate → start, restricted devices 8–15. Started 20:35:20Z; monitoring continued until actual exit at 20:44:28Z, not merely container running. API configured for 127.0.0.1:18550; no successful readiness response or smoke requests.

Fatal model-loader error (container.log line 272 and other worker traces):
`KeyError: "Vision weight 'aligner.w1.bias' has no parameter 'aligner.w1.bias'."`
Location: `/vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v4/vl_model.py:252`, `language_weights`.
Earlier warning: unavailable `causal_conv1d_update_npu` import caused PyTorch fallback; not established as the fatal cause.
Docker state: exit code 1, OOMKilled=false. No claim of smoke/quality success; no usage or finish_reason produced. P2 is blocked.

Ownership checked against full CID and both owner/run_id labels, then only `docker stop 67993945c3595dc9bc76bbddc429c2c4d7d49be7cadd5b3d4b1bdbd7795e3525` executed (exit 0). Post-stop confirms Running=false/Pid=0 and no listener on 18550. Stopped container retained for evidence; no name-based cleanup. No code, precision or resource-boundary changes or automatic retry.
