# Authorized four-worker resume — RUNNING, not complete

Task root: `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh`.

Validated old PID 2207298, start_ticks 175851895, boot_id `20bd7f0d-55e0-4cf5-b001-eab251f97b15`, and exact task supervisor cmdline before sending SIGTERM only to that PID. Confirmed termination and scanned /proc file descriptors: no task-model writers remained. No wrapper/external task was killed. Existing complete files and partial bytes were retained.

Deployed `tools/download_assets_parallel.py`; local and remote loaded SHA256 match: `32a59ee9f1a77d6680fd8d02c5c3df27de472c51984661692859729cc40e9d68`. Deployment copy occurred before termination; execution only after termination/writer/capacity checks. Same 120-file manifest SHA256 `62e252b4a6d8eb23a89b0f2af65960d564711230bb1aba8b788e8936d5ed927c`, same model directory.

Fresh capacity: remaining missing bytes after retained parts 516568671627 + reassembly allowance 196613849824 + reserve 68719476736 = required **781901998187 B**; available **866717949952 B**, passed. Six complete files were independently size/SHA256 verified.

Detached supervisor `tools/run_download_parallel.py` runs `--workers 4 --resume --direct --execute`. PID **2210671**, start_ticks **175934799**, boot_id above, started Unix 1795267964.6156163. Independent remote files: `logs/parallel-process.json`, `logs/parallel-download.jsonl`, and eventual `logs/parallel-exit.json` (absent in latest snapshot; not an exit/completion claim).

## Four-stream growth

Snapshots Unix 1795267985.77435 → 1795267994.976619, sizes in bytes. All four locks belong to PID 2210671; both snapshots confirm matching /proc identity.

| File under engram_int8 | First | Second |
|---|---:|---:|
| layers_14_engram_embed.scale.safetensors.part | 8665432064 | 8708423680 |
| layers_14_engram_embed.weight.safetensors.part-00-of-06.part | 98566144 | 142606336 |
| layers_14_engram_embed.weight.safetensors.part-01-of-06.part | 100663296 | 143654912 |
| layers_14_engram_embed.weight.safetensors.part-02-of-06.part | 68157440 | 97517568 |

The retained scale partial grew from preflight 8597274624 B; code permits append only after strict HTTP 206 and exact Content-Range validation. Growth therefore demonstrates successful validated resume (raw HTTP headers are deliberately not logged). Failure stops the group; no source switching, fallback redownload, or partial deletion was performed. Fresh files use normal HTTP 200.

Latest independently verified complete count: **6/120** (`.gitattributes`, `README.md`, `config.json`, `configuration.json`, `engram_extra.safetensors`, `engram_int8/PARTS.sha256`). Partial data is not hash-complete.

Raw evidence: `parallel-preflight.json`, `parallel-switch-output.json`, `parallel-process.json`, `parallel-download.jsonl`, `parallel-snapshot-1.json`, `parallel-snapshot-2.json`. Reproducible supervisor/control/snapshot scripts are alongside this report. No reassembly, containers, or NPU operations.
