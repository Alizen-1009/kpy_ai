# Bounded runtime closure

`runtime_report.json` closes pre-model prerequisites against current runtime-map SHA256 `0219f07e6ad02119a6f262999d7448c7afdcfb88fa4eb77765f6326624fa94e8` (MAX_LEN=4096, GPU_UTIL=0.85). It supersedes the CLI/environment/provenance open items in earlier chronological reports, not their real-model limitations.

No copied argparse sources or full help were available. Exactly one additional help-only run reused device_preflight's fresh idle, immutable image, selected frozen mounts, no model mount, network-none, inspected-create gate and full-CID cleanup. No serving function was invoked. Full help lists all 21 selected serve_v2 flags, including deepseek_v4, lazy loading and JSON default-chat-template-kwargs. Fixed numeric/string/boolean/JSON values match the documented parameter forms; model-dependent cross-field validation remains P1. This is not a claim of full argv parsing.

Log: `cli-help-preflight-f3d1f0a4f91543b896ca326e33b40b1e.log`. CID `043477aa082902a7c123660d365485e91e1db27c0ccd9d8a9b5719f9ab81f19b`. CLI_EXIT=0, START_EXIT=0, final ExitCode=0/OOMKilled=false, stop/rm exit0; final host npu-smi output independently passed launch.check_npu. Existing successful operator/import/tokenizer/quantizer evidence reused, not rerun.

## Image environment review
All 27 exact keys/values are retained in runtime_report.reviewed_image_env, with per-key review. SDK/toolchain/ATB paths point to vendor locations; CMAKE_PREFIX_PATH and PATH contain absolute locations. Remaining values are non-secret ATB synchronization/cache/memory/ABI controls, LCCL controls, SOC_VERSION, DEBIAN_FRONTEND, TASK_QUEUE_ENABLE and OMP_NUM_THREADS. No credential, signed URL, shell code or LD_PRELOAD/LD_AUDIT/BASH_ENV/ENV was found in these values. This does not audit arbitrary files inside the image.

Raw LD_LIBRARY_PATH and PYTHONPATH end in empty components, allowing current-directory lookup. Image PATH itself has no empty component. The current launcher source implements a fixed post-login Python bootstrap removing empty LD_LIBRARY_PATH/PYTHONPATH components before exec of frozen serve_v2; the probe also sanitizes these paths. Raw image values remain unchanged. The bootstrap does not sanitize PATH: if login scripts introduce empty PATH components, that risk is NOT proven eliminated. Recommended hardening is to include PATH in the fixed wrapper's empty-component removal and use absolute interpreter/shell paths; no launcher changes made here. The main agent reports six bootstrap tests passing; this report independently checked source, not those test executions.

Image ID, two git commits and retained component/OPP library hashes establish the bounded image identity despite absent BUILD_INFO in the searched locations. No requirement to wait indefinitely for that filename.

P1 still requires actual weight/Engram identity and tokenizer semantics, model configuration validation, HCCL/TP8, memory capacity, kernel shape/dtype correctness, first generation and output quality. None is established by this report.
