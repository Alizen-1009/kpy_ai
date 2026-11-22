# Device retry — bounded probe passed; deployment not yet attested

## Execution evidence

Ran `python3 -m py_compile .../device_preflight.py` successfully, then exactly one real invocation of the existing script. No script/shared payload changes, model loading, serving, benchmark or operator execution requested.

Raw evidence: `p1-device-preflight-9fb7c6664deb4e47a9428d10bb43118a.log`.
SHA256: `abc7c7ddc84db80f21573ed70941a8fd470e9702949a3954c63898e4e9adfd0f`.
Run label: `p1-device-149a8303a1344bde89b23b23518527b9`.
Full CID: `65b6ba18d3f605da6045275ced0c67ca6a5fe2dd3a076842e494f89773dc7bbb`.
Container timestamps: 2026-11-21 13:59:27.421376624Z–13:59:53.238072309Z.

- Fresh host idle checks and create/inspect gate passed (line 762).
- Only authorized compute dies 8–15 exposed, plus control devices; DEVICE_NODES at line 854. Readonly frozen payloads/driver mounts; no model mount; network none.
- Explicit `V41_ENGRAM_DEVICE_INDEX=0`, `VLLM_BATCH_INVARIANT=0`; custom extension enabled before schema lookup.
- SSH_EXIT 0 **and** START_EXIT 0; final State exited / ExitCode 0 / OOMKilled false / Error empty (885–886).
- CLI_EXIT 0; ordered model and dsa_v1 imports both passed (851–853).
- `PROBE_FAILURES []` (881); no traceback. Earlier missing auto-index module and unregistered-op observations are superseded for this corrected probe only.
- Full-CID stop and rm each exited 0 (888–892). Post-cleanup host npu-smi exited 0; its captured final output separately passed local `launch.check_npu`.
- Nonfatal stderr: `can not use command: npu-smi info` (882); host checks succeeded. Do not reinterpret this as a kernel test.

## Seven schema families versus frozen payload

Actual schemas and exact AST calls: lines 855–878; 12 callsites, seven unique operators. Structural argument compatibility reviewed, **not** tensor shape/dtype or kernel correctness.

| Operator | Payload/schema comparison |
|---|---|
| vllm.dsa_v41_forward | model.py:734: three positional arguments match Tensor, mutable output Tensor, layer-name str; void return. |
| npu_hc_pre_v2 | model.py:815: five positional inputs, four keyword-only fields hc_mult/hc_sinkhorn_iters/norm_eps/hc_eps match; four Tensor returns. |
| npu_hc_post | model.py:828: four positional Tensor inputs, Tensor result; outer squeeze correctly excluded from operator lookup. |
| compressor_metadata_out | dsa_v1.py:100: nine explicit positional arguments plus three output buffers match 12 schema parameters; three aliased output returns. |
| inplace_partial_rotary_mul | Five sites: three Tensor inputs plus rotary_mode and partial_slice keywords match; in-place/void signature. |
| npu_vllm_quant_lightning_indexer_metadata | dsa_v1.py:873: all named arguments, including cmp_ratio/device and optional sequence tensors, match actual schema names. |
| npu_rms_norm_dynamic_quant | Two sites: x/gamma positional plus epsilon keyword; optional smooth_scale/beta omitted legally; two outputs. |

## CLI/registration scope and remaining gates

`ascend` resolves to AscendModelSlimConfig (879). Registry includes both upstream `deepseek_v4` and patched `deepseek_v41` (880). Runtime-map currently specifies `--tokenizer-mode=deepseek_v4`, which is registered, **not** the patched deepseek_v41 tokenizer. Registration proves availability, not that the selected tokenizer is semantically right for the eventual weights.

Important limitation: this run invokes only `vllm serve --help`, which prints config groups rather than all options. It does **not** parse the complete serve_v2.sh launch argv or validate `--default-chat-template-kwargs={"enable_thinking":false}`. Therefore exact launch CLI compatibility remains open; no additional run was performed to conceal this gap. Next required bounded check is full CLI flag/schema inspection or parser-only validation of the exact frozen launch argv without engine/model construction.

Remaining necessary work: resolve tokenizer selection against actual model metadata; exact CLI argv/config validation; real weights/Engram manifest consistency; original image ENV/provenance attestation; then separately authorized real-model execution and output validation. No passing runtime_report.json or deployment-ready claim generated.

## Disclosure check

Raw image Env retained as instructed for the previously checked image. Scanned this log for signed-query URLs, x-amz/x-oss signatures and bearer-token patterns: zero hits. No signed URLs copied into this report. This is a bounded disclosure scan, not an independent credential audit of every arbitrary Env value.
