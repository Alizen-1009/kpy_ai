# Download stopped — assets NOT verified or reassembled

Observed the authorized existing PID 2210671 every 60 seconds in two consecutive bounded foreground SSH sessions. First observer ended at its four-hour deadline (124); second detected downloader termination (observer 34, downloader **1**). No writer was started, terminated, modified, or cleaned up.

- Identity while running: start_ticks 175934799, boot_id 20bd7f0d-55e0-4cf5-b001-eab251f97b15, run_download_parallel.py cmdline.
- Downloader started Unix 1795267964.6156163; ended 1795288859.7976096 (20895.182 seconds, about 5h48m15s).
- Exact logged exception type: **ValueError**. The running downloader log suppresses the message and traceback; the specific underlying cause and failing file cannot be established from this log. Do not label this as disk exhaustion, hash mismatch, or transport failure without additional evidence.
- Last observed available space: 508214726656 bytes; model regular-file size sum including retained partials/metadata: 367729367836 bytes, observed Unix 1795288881.3907.
- Log records 60 complete/verified_existing events out of the 120 manifest files. This is downloader-reported, NOT independent full-manifest SHA256 verification.
- Last four started shards: quant_model_weights-00033 through 00036-of-00072.safetensors; final event failed/error_type ValueError then supervisor_exit/code 1.

Gate intentionally stopped: no 120-file verified report, no Engram reassembly, no launch-ready report was fabricated. Existing partial files and locks were not removed. Staged deployment_yh tools were not modified. No NPU, containers, or services were used.

Evidence: observe.py; observe-1.jsonl and observe-2.jsonl (60-second identity/log/capacity/byte observations); corresponding SSH stderr; exact copied parallel-process.json, parallel-exit.json, parallel-download.jsonl.
