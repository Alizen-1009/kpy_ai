# VISION=1 retry: P1 runtime smoke passed, service retained

Run `p1-vision1-20261121T205625Z-244b8fbf`, exact CID `1fdb00879533bb97ba7ef9f7bf7f64639a03e8b01bdfbdfe198b8a03fcf98a65`. Endpoint on 910c: http://127.0.0.1:18550. Served model is run ID. Retained for immediate P2.

## Meta gate
`meta.py` executed real image ViT/aligner constructors on torch meta without NPU devices and compared all 266 actual parameter names/shapes to actual checkpoint headers, including biases. Passed (`meta.stdout`). Wrapper itself was not instantiated; sentinel parameters follow its actual source. No tensor payload loaded and no numerical/vision inference claim. No model code or image modification; CPU harness disables plugin autoload and supplies CPU vLLM config. Initial CPU harness setup attempts failed before comparison and were corrected (backend shared libraries, missing current vLLM config, CPU device selection, flat header structure).

## Deployment
New `deployment_v2_yh` copied reviewed original deployment; original deployment unchanged. Only map VISION/MM_LIMIT_IMAGES changed to 1; new runtime report retains historical prerequisites and explicitly adds bounded meta evidence with new map hash. Frozen original payload directory, manifest, recovery verified/reassembly reports reused. Launcher hashes and fresh NPU-idle/RAM/disk/port gates passed. Exactly one real service launch. Same pinned image 1f2c0819..., weights and precision; strict loader unchanged, no keys skipped.

## Observed
Readiness and three real streamed generation requests passed HTTP 200 with stop finish reason. Completion-token usage: 3, 10, 28. Responses include `21颗`, remembered paper-boat name, and Python sum-even function; this is runtime smoke, NOT P2 quality acceptance. See run smoke/summary.json and raw SSE/response files.

All eight TP/EP ranks logged successful weight loading (37.4330 GB each). Logged available KV 6.87 GiB; graph memory 0; peak activation 4.66 GiB. Post-smoke host RAM, NPU/process memory, loopback listener and full logs in post-smoke.txt. Full run monitor records host memory throughout.

Fallback/warnings: causal_conv1d_update_npu unavailable; explicit PyTorch fallback logged, per-request synchronization and graph-capture limitation noted. GRAPH=0 remains unchanged. RMS/fused-add RMS native priorities logged. max_num_batched_tokens=8192 exceeds max_num_seqs*max_model_len=4096 warning; unrecognized rope keys and admission-gate env warning preserved. No tuning performed.

Original failed container untouched. To stop only this service if needed: `docker stop 1fdb00879533bb97ba7ef9f7bf7f64639a03e8b01bdfbdfe198b8a03fcf98a65`.
