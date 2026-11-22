# Recovery 3 — completed

Remote isolated run: `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/logs/recovery-3-20261121T200226Z`.

Preflight: zero writers/locks; free 425602080768 bytes, remaining downloads 75453478287, assembly 196613849824, reserved 68719476736. Current downloader copied into new run only; historical copies/supervisors untouched.

Executed full manifest with `--workers 4 --resume --direct --retries 3 --execute`; waited to actual exit 0. Supervisor PID/startticks 2220464/178273338; downloader 2220465/178273353. Events: 79 verified_existing + 41 complete = 120 fully hash-verified files. No short_response occurred in this run; unfiltered JSONL retained. Before/after size, mtime_ns and inode recorded, checked unchanged for existing files and checked again after assembly for all manifest files.

Staged deployment_yh reassemble_engram.py executed successfully, retaining every input shard and using no-clobber publication. Two final files independently streamed through sha256sum and matched reassembly expected hashes. Final available space 153534525440 bytes (>64 GiB).

Local assembly, independent hash, audit script and verified report: `../../assets-final/recovery-3-*`. Remote `verified_report.json` binds complete manifest and remote `reassembly.json` digest; manifest hashes derive from actual downloader verification events, not assumed metadata. No NPU/container/service operations performed.
