# Actual download attempt — BLOCKED by refused redirect

SSH alias: `910c` only. Fresh statvfs `/root/syf/data_yf`: available 875945725952 B, required 791128633881 B. Task directory was absent, not a symlink; created new mode-0700 `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh` with owner.json and tools/model/logs. Shared checkpoints/DeepInfer unchanged. No reassembly, containers, or NPU use.

Copied audited downloader unchanged (SHA256 `4e7a88b2ad9e1e0bdff989e5b14d3f2f7bb7a20917a25cb5e774ff9d3faf1b5c`), fixed 120-file manifest (SHA256 `62e252b4a6d8eb23a89b0f2af65960d564711230bb1aba8b788e8936d5ed927c`). Revision 50029772e7757c3d9cec50481661091b369af901. Supervisor source preserved here; it adds sanitized redirect status/hostname logging while still unconditionally rejecting redirects. No alternative sources or credentials.

Executed --direct --execute --max-files 3 first: 3 files, 48218 B verified by downloader and independently rehashed by supervisor. Then invoked full single-stream execution, reverified existing three, completed configuration.json (29 B). Total actual completed payload **48247 B, 4/120 files SHA256/size passed**; no partial files at snapshot. No double cache.

First LFS file `engram_extra.safetensors` returned **302**, target hostname **cdn-lfs-cn-1.modelscope.cn**. Redirect refused before downloading its body; supervisor exited code 1. No signed URLs were logged. Full weights NOT downloaded; P0 NOT passed.

Exact process: PID 2206335, /proc start_ticks 175838376, boot_id 20bd7f0d-55e0-4cf5-b001-eab251f97b15, started_unix 1795267000.3851058. Command launched: python3 -u /root/syf/data_yf/yuhao_vllm_ascend_repro_yh/tools/run_download.py. Detached session with task-owned log `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/logs/download.jsonl`. At one subsequent evidence snapshot /proc/2206335 was absent: process no longer running. No polling/sleep.

Raw sanitized process identity, completion/error events and exit status copied to process.json, download.jsonl, exit.json alongside this report. Requires explicit redirect-policy review/approval before any further download. No retry or permission expansion performed.
