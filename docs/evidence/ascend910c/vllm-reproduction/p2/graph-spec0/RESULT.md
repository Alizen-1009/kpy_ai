# GRAPH1/SPEC0 — executed to completion; acceptance FAILED

Run `p2-graph-20261121T230225Z`, full CID `ec301b67f2f8466a76aa46b1f064f3753b5925157fd1c69c23449915cb757d4e`, loopback18550. Old CID8bf3 remained stopped, never restarted. Independent deployment_graph_yh uses graph map with MAX_LEN8192 / VISION1 / MM_LIMIT_IMAGES1, zero additional payload (mount list equality asserted). Runtime report binds new map SHA and explicitly certifies API prerequisites only, graph_runtime_verified=false. Frozen launcher checked NPU availability, asset/payload hashes and isolation; fresh NPU/listener evidence retained.

Readiness and smoke succeeded. Actual logs show GRAPH1/EAGER0, SPEC0 and FULL_DECODE_ONLY configuration; decode FULL capture 1/1 completed, 11 seconds / 0.28GiB. However there is no explicit replay event/counter in retained logs: successful generation is not substituted for independent replay proof. No eager restart or configuration downgrade occurred. Startup generic mamba Triton fallback warnings remain in logs; they are not silently discarded or called proof of full-model eager fallback.

All three quality clients actually completed serially on this same instance (foreground wait, not merely background dispatch):
- GSM200 first200, original 8-shot client/data: 198/200 (99%), empty=0/errors=0. Output cap1024 differs from historical512 and is NOT strict same-configuration reproduction. Wire audit: 199 stop, **1 length**. Thus the mandatory all-stop gate FAILED despite score exceeding197.
- Code128: 8/8 tasks,128/128 assertions; original4096 output cap, timeout1800; sandbox and response evidence retained.
- Vision23:23/23, minhit1.0, mandatory neg-text-01/neg-swap-01 passed, empty/errors0; explicit existing images-dir and official-dir. Vision wires include27 stop completions (23 suite plus token measurement requests).

CLI help exposed wrapper preconditions (wire directory must be new, cwd reference path, ENC_DIR); corrected before inference using underlying CLI help and new task cwd. No client CLI exception stopped a healthy service. Actual argv and help retained. Raw GSM/vision wire bytes (base64), usage/finish metadata, Code responses, sandbox records and full server logs are local in this directory. wire-summary.json records exact GSM length sidecar.

Service remains healthy/running and idle (final-metrics: running=waiting=0, KV usage=0; final-inspect). Not stopped for a quality gate failure; no engine/OOM failure observed. **Do not advance as a fully accepted graph baseline:** all-stop failure and missing explicit replay evidence remain. No DSpark/P3 launched. No retries or changed token cap used to overwrite the failed gate.
