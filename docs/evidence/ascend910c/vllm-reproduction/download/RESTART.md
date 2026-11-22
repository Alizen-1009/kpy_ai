# Authorized CDN-policy restart — RUNNING, not complete

Reused task workspace `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh`; preserved and rehashed all four completed files. Confirmed old PID 2206335 absent and no .part files. Fresh available 875945586688 B >= remaining budget 791128585634 B. Evidence: restart-preflight.json.

Old tool SHA256: `4e7a88b2ad9e1e0bdff989e5b14d3f2f7bb7a20917a25cb5e774ff9d3faf1b5c`.
New audited tool SHA256 (remote and local match): `6c3d7e49a2366b9b6d62593ae64e877d97d30b7c3b44364f06eb59e349127ad9`.

Supervisor source `run_download_restart.py` adds sanitized logging around existing policy without bypassing it. Full --direct --execute started detached, single stream; no caches. Only reviewed HTTPS CDN permitted, no new domain allowed, no signed URL/header logging.

Exact process: PID/session 2207298, start_ticks 175851895, boot_id 20bd7f0d-55e0-4cf5-b001-eab251f97b15; started_unix 1795267135.5728822. Command: `python3 -u /root/syf/data_yf/yuhao_vllm_ascend_repro_yh/tools/run_download_restart.py`. Remote log: `logs/restart-download.jsonl`; identity: `logs/restart-process.json`; eventual exit code will be written to `logs/restart-exit.json` (not yet present, process running).

Snapshot at Unix 1795267148.1515303: /proc confirms matching running PID/startticks/cmdline. 4/120 files fully SHA256/size verified, totaling 48247 B. First LFS `engram_extra.safetensors` passed approved 302 redirect to cdn-lfs-cn-1.modelscope.cn and its `.part` had **68157440 / 629310402 B**. Total payload present at snapshot **68205687 B**, of which partial is not hash-complete. No failure seen. This is actual LFS progress, not a completed weight download.

Evidence: restart-snapshot.json, restart-process.json, restart-download.jsonl, restart-preflight.json. Snapshot captured once, no sleep/polling. No shared assets changed, no service/container/NPU or reassembly operations. Previous RESULT.md describes prior blocked attempt, superseded only for current process status by this restart record.
