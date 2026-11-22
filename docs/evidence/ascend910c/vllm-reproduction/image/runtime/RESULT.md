# Fixed image, no-NPU inspection

## Result
Image downloaded and available. Static checks below passed, but full payload API closure is NOT established; do not equate package versions or the successful audit container with successful serving. No model/NPU execution performed.

- Existing pull finished exit 0; no new pull/prune/tag substitution.
- Digest: `sha256:16a57b897a2f475f85b0e90df1644c9870c2418b368b2adf447c5173eae211c3` (quay.nju.edu.cn/ascend/vllm-ascend).
- Image ID: `sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef`.
- Architecture arm64; Size 24,930,899,801 bytes. Docker partition available before audit 46,131,953,664 bytes (>16 GiB).
- torch 2.10.0+cpu; torch_npu 2.10.0.post4; vllm 0.27.1+empty; vllm-ascend 0.1.dev5097+ge43cf1e9f; triton 3.5.0; numpy 1.26.4. Read with importlib.metadata only, no imports of those packages.
- vllm HEAD 6e448d0ea9bf3d88d898b65449ca6dc2aec170ac; ascend HEAD e43cf1e9f5d9bead076853aa6bcacb671465de94; full git porcelain empty for both.
- SDK asc-devkit Version=9.1.0, timestamp 20260730_231653901. Component version.info and OPP library SHA256 recorded in audit.log.
- BUILD_INFO.txt not found under recursively checked /vllm-workspace or /usr/local/Ascend, nor top-level BUILD* in /, /root, /opt, /workspace. This is a bounded search, not proof of global absence.

## Initialization and layout
/etc/profile sources `/usr/local/Ascend/ascend-toolkit/set_env.sh` (resolves to `/usr/local/Ascend/cann-9.1.0/set_env.sh`), ascendnpu-ir set_env.sh, and ATB set_env.sh --cxx_abi=1. Nothing sourced by inspection itself. Only necessary PATH/LD_LIBRARY_PATH/PYTHONPATH/ASCEND_HOME_PATH/ASCEND_OPP_PATH ENV values were recorded.

Deepseek_v41 is the expected flat layout, with model.py, engram_hbm.py, engram_hash.py, engram_gate.py, indexer.py alongside each other, not the incompatible nested engram package. engram_jit_kernel.py and engram_plan_kernel.py are new payload additions absent in image listing. Original destination file hashes and selected unmounted source copies are retained locally as *.source.

## Actual interface comparison
`interfaces.txt` comes from AST parsing, not importing runtime packages. Unmounted dsa_v41.py imports dsv4_dsa_overlap_stream and the two rope helpers; model_runner_v1.py imports AscendDSAMetadataBuilder and six ascend_forward_context symbols; utils.py imports select_moe_comm_method/use_cann_megamoe; dspark.py imports DeepseekV41DecoderLayer. All these named imports exist in replacement modules. Shared function signatures across compared originals/payloads match except Engram `_record_offload_use(self, source_ptr, device)` gains optional `reuse_event=False`; this is not a required-argument break.

Substantive differences remain: payload Engram adds EP communicator reuse and configurable fallback HCCL buffer, JIT plan sidecar imports with fallback handling, routing instrumentation, and reuse-event handling. This is not a byte-identical payload. `payload.diff` preserves 3307 diff lines for review. Existing imports/signatures alone do not establish behavioral compatibility, operator schema compatibility, or all dynamically imported APIs.

Remaining deployment gate: inspect payload dependencies outside this captured subset (vllm APIs/custom ops), call argument and context-field compatibility across all unmounted consumers, tokenizer/quantization/CLI registration and real-weight/Engram metadata. BUILD_INFO provenance remains unresolved. No proven flat-layout or named-import blocker in the inspected subset; no claim that full deployment is ready.

## Container lifecycle
Both containers created with unique audit label, no device assignment, network none, read-only, cap-drop ALL, no-new-privileges, memory 2GiB, cpus 2, pids128, no bind/shared mounts. Image-declared volumes checked absent before create. Entry point overridden to python3 -B; no shell login or model initialization.

- b9db2f36bcb744192f2826d22f95852fa26f3a30403a755c5fadbdfbe817cc8c
- b2894d0480db5ba870302c97ed88a1693e7d9e66d076a76e5eab4fa6213aa5d7

create → start -a → inspect exit 0 → output/HostConfig saved → stop/rm by full CID. Both removals confirmed in logs. No other container touched. Scripts and raw audit/supplement logs retained here.
