# DSpark actual inference and measured speed: PASS (bounded smoke)

Served name: `dspark-fix-20261122T012300Z`, endpoint on 910c `http://127.0.0.1:18550`.
Full live CID: `7c2a3c7bf7c32ac25239f414d0392ba10e5ae711082cd4ecdac20a5afd5f42db`.
Stop: `ssh 910c docker stop 7c2a3c7bf7c32ac25239f414d0392ba10e5ae711082cd4ecdac20a5afd5f42db`.

Foreground execution waited through loading, graph capture, three real smoke requests, and complete 1 warmup + 8 measured SSE requests. No engine failure occurred. Service retained running, OOMKilled=false (inspect.json).

## Provenance and isolation

Independent new payload `payload/dspark-fix-20261122T012300Z` and `deployment_dspark_fix_yh`; selected map remains 13 files. Only dsa_v1 hash changed, all other selected hashes asserted unchanged. Local minimal diagnostic bugfix differs from original published source: source.patch removes invalid module-level self diagnostic access; computation/shape guard untouched. Fixed image and prior MAX_LEN8192/SPEC1/K5/GRAPH1 settings inherited unchanged; launcher safety gates untouched. Old fullCID was asserted not running, port bind tested free, fresh idle gate passed before launcher and launcher repeats gates. No shared ref, original payload, weights, precision or tensor math changes.

CPU regression evidence cpu2.log passed in no-device/network-none read-only fixed-image container with TORCH_DEVICE_BACKEND_AUTOLOAD=0; both CPU container fullCIDs removed. Initial auto-backend import failure retained separately.

## Actual generation

Chinese explanation coherent (128-token cap truncates answer); multi-turn arithmetic correctly returned `17 + 8 = 25`. Initial code smoke hit 128-token cap during docstring; supplemental concise code request returned complete correct `return sum(n * n for n in numbers)` with finish_reason=stop. No obvious text degeneration in these bounded checks; not full quality equivalence or formal benchmark certification.

container.log:46 identifies DSpark K5; :537-560 records actual draft graph capture with three layers and five draft input tokens. Successful actual generation and nonzero draft acceptance counters follow capture (not environment-only evidence).

## Speed

Same current-tps prompt, temperature=0, min_tokens=max_tokens=256, ignore_eos=true, 1 warmup + 8 measured, serial. All 9 final usage objects verify 21 input / 256 output tokens; full SSE events and DONE retained in current-tps.jsonl.

- End-to-end output TPS median **97.1556**, range **87.3913–101.7041**.
- TTFT median **0.247953 s**, range **0.213374–0.259727 s**.
- Against supplied 30.959 TPS baseline: **3.1382x**, **+213.82%**.
- Definition: 256 / complete SSE elapsed time, including TTFT. This is short-prompt current-TPS, not the old 2048/256 full suite.

## Real speculative accounting

metrics-before/after bracket all nine speed requests (including warmup, excluding smoke). Deltas: **560 draft rounds**, **2800 proposed tokens**, **1752 accepted tokens**. Accepted/proposed **62.5714%**, not 100%. Accepted draft length **3.12857/round**; conventional acceptance length including one target token **4.12857**. Per-position accepted deltas: [500,413,324,277,238]. Actual emitted output per draft round 2304/560 = **4.11429** (request boundaries/clipping differ from conventional acceptance length).

No direct per-step kernel timing was collected. Full-request wall time amortized per draft round is **42.7457 ms**, including prefills/TTFT/network; this is NOT decode kernel step latency. Log windows independently show mean acceptance lengths 2.33, 3.89, 4.09; these windows mix smoke and portions of benchmark, so metrics deltas are preferred for the benchmark aggregate. SSE chunk spacing is not token ITL.
