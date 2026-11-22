# Read-only failure diagnosis

PID 2210671 absent. No writer launched; no part/lock deleted or altered; no NPU touched. Raw sanitized observations: probe.jsonl. Probe implementation: probe.py (stdin is the pinned manifest JSON on one line; run over SSH with `python3 -c` and supply manifest on stdin).

| shard | expected bytes | part bytes | complete | lock |
|---|---:|---:|---|---|
|33|4289972760|2265972736|absent|absent|
|34|4294998904|1111490560|absent|absent|
|35|4290759864|794786553|absent|absent|
|36|1256249776|0|absent|absent|

Manifest SHA256 values are captured in probe.jsonl. None of the four parts has full expected size, so no full-file hash was performed. Existing completed assets were not hashed.

Available 508214767616; remaining download 158065939608; EXTRA 196613849824; reserve 68719476736; required 423399266168; current headroom 84815501448 bytes. Current budget passes; this is not a measurement of the exact failure instant.

All four requests returned 302 to the historically allowed cdn-lfs-cn-1.modelscope.cn then 206 with exact requested Content-Range. Shards 33–35: last 1 MiB of local partial matched remotely. Shard 36: requested one byte at offset 0 (empty part has no tail). Raw first-run tail_match=false for shard36 means no local byte exists, NOT corruption; script now reports null for this case. Application payload read total 3145729 bytes. No ignored Range or changed CDN observed now.

## Interpretation and limits

Historical log records ValueError without message/path. Exact failure is NOT reproduced by this bounded probe. All parts are incomplete, not full-size bad-hash parts. Shard35's non-MiB boundary and shard36's zero length are compatible with an early EOF producing `size/hash mismatch`, while other workers stop, but do NOT establish which worker failed or why. Historical connection truncation, transient redirect/range behavior and other ValueError branches remain unproven. Tail matches do not validate all earlier bytes. Do not label this a proven hash mismatch or disk exhaustion.

No evidence currently requires quarantining any part; preserve all four. Resume will hash retained bytes and validate final size/hash. If final hash subsequently fails, preserve/quarantine that particular part before a fresh download, never all assets.

## Recovery (NOT executed)

Do not rerun run_download_parallel.py: that wrapper overwrites historical process/exit metadata. Prefer a new versioned tool with safe static error reason plus path logging before resuming. Existing tool can resume without wrapper/history replacement as follows, after separately ensuring no other writer exists:

```sh
R=/root/syf/data_yf/yuhao_vllm_ascend_repro_yh
python3 "$R/tools/download_assets_parallel.py" \
  --manifest "$R/tools/model-files.json" --dest "$R/model" \
  --workers 1 --resume --direct --execute \
  > "$R/logs/recovery-$(date -u +%Y%m%dT%H%M%SZ).jsonl" 2>&1
```

This resumes retained parts rather than downloading complete assets again, but the current run() preflight hashes existing completed files (large read-only I/O). It is therefore a deliberate authorized recovery operation, not the bounded diagnostic loop performed here. It retains the old tool's poor error detail; improved safe instrumentation is recommended before execution. No local downloader change made by this diagnosis.
