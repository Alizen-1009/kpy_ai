# P1 preflight execution findings

Evidence: p1-preflight.log, p1-preflight-retry.log, p1-preflight-cache.log, p1-preflight-tmpfs.log; frozen-payload.json (11 locked source/destination hashes).

Created a unique task-owned payload/preflight_<uuid> directory below /root/syf/data_yf/yuhao_vllm_ascend_repro_yh, copied exactly 11 selected files, checked both hashes and chmod444. No ref/shared modification. All ten Python replacements mounted at real destinations read-only, plus serve_v2.sh. All ten compile successfully in the actual image.

Four probe containers used no devices, network none, 2CPU/4GiB/pids128, read-only root, cap-drop ALL/no-new-privileges, no shared bind. Final probe added a private 512MiB exec tmpfs /tmp for compiler caches, not a host/shared mount. Earlier attempts proved readonly cache failures and /dev/shm noexec failures; these are harness issues, not payload API failures. No default-capabilities requirement established; caps were never elevated.

Final bash -lc probe initialized CANN and ran individual module imports plus vllm serve --help. Five imports succeeded: engram_hash, engram_jit_kernel, engram_plan_kernel, engram_gate, ascend_forward_context. Engram HBM, rope, token_dispatcher and CLI help reach Triton NPU backend get_arch and fail with SystemError in this no-device container. No devices added to bypass. model and dsa_v1 direct imports hit DeviceOperator circular import; whether normal CLI import ordering avoids this remains unverified (do not label proven serving failure).

AST evidence records every explicit import and torch.ops call from all ten payloads. Source declaration/registration evidence exists for dsa_v41_forward, npu_hc_pre_v2, npu_hc_post, compressor_metadata_out, inplace_partial_rotary_mul, npu_vllm_quant_lightning_indexer_metadata, npu_rms_norm_dynamic_quant. Final log includes 10-line declaration context, enabling exact argument review; mere textual matches are not a completed schema assertion. deepseek_v41 frontend registration exists; distinguish requested deepseek_v4 tokenizer rather than assuming aliases. CLI runtime help did not complete, so full option/quantizer/tokenizer closure is not claimed here.

Image ENV was individually enumerated with unknown values redacted. Several ATB/LCCL/SOC/OMP settings still require review, and LD_LIBRARY_PATH/PYTHONPATH have trailing empty components (current-directory search). No LD_PRELOAD/LD_AUDIT/BASH_ENV/ENV appeared. Do not set image_environment_verified=true yet; launcher compares the entire ENV dictionary exactly.

No passing runtime_report.json emitted: environmental no-device get_arch failures are bounded deferrals to actual P1, not a demand for static proof of all behavior. Remaining immediate review work is explicit OP argument/declaration review, exact CLI/tokenizer/ascend registration, ENV decisions and circular-import classification. This report distinguishes these incomplete checks from actual demonstrated model failure.

All containers exited 0 at the probe-driver level (child import/CLI nonzero statuses explicitly logged), were inspected, then stopped/removed by full CID with successful confirmations:
- f4f7bc4586898463938c886773d75cf5ccef2ca2ad42fb10fc3864992e29b269
- 197934adde2691221c9bc04572986625861bfac183890128485dbc125450ca2d
- 0e24e806fc80f68b799f9a2d0e217d31f4904b36dd9a6da31267e1da54b835ec
- 8c646e9ee0948d3a6ee7887930300e72ccceba6cf9c8df44db4511334c857d89

No model execution occurred. Importing modules does implicitly probe NPU availability; failures are retained rather than hidden.
