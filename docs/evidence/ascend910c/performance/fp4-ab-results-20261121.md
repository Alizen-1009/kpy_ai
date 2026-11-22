# Approved FP4 candidate: actual paired A/B

Reference SHA256 1100b1f8caca4ce65824829fdf19eeb25f9c003e05cde8cd5ad9c1fabc89534b frozen independently; approved candidate SHA256 58a7a16b9f67b54bad373f62764965b11fa4690021f1cd0cfa4048380f34f6a5 verified by benchmark. Candidate deployed only in new isolated source copy `/root/yuhao/deepinfer_910c_yh/src_yh/DeepInfer_fp4_ab_20261121_yh`, leaving prior source intact. No core edits by benchmark agent.

Runs (all under this directory):
- `stage5_moe_batch_die8_20261121T131338667081043_yh`: first AB, exit0; initial hashes only.
- `stage5_moe_batch_die8_20261121T131523790546490_yh`: final AB with post-timing hashes, exit0.
- `stage5_moe_batch_die8_20261121T131659473324053_yh`: full bounded candidate replay, exit1.
- `stage5_moe_batch_die8_20261121T131816767627779_yh`: same full bounded old-reference replay, exit1.

Every run freshly passed die8 idle guard (3157–3158MiB), exact one-die exposure; read-only checkpoint mounts; no full model allocation/receipt bypass. Every owned CID independently confirmed absent in cleanup_independent.json. All four complete small evidence bundles downloaded, no trace in these runs.

## Final paired benchmark

Expert124 from real captured layer30 router. M8 repeats one actual token, not eight requests. Each stage one warmup per lane then five pairs, order AB/BA/AB/BA/AB. Same inputs; isolated down uses common reference mid. Full expert includes actual gate/up, weighted SwiGLU FP8 quantization and down. Initial AND final up/mid-data/mid-scales/down hashes identical between implementations and unchanged after timings. JSON retains all samples, source manifest and input/snapshot hashes; scripts/launcher archived with run.

Median wall ms (reference -> candidate):
| M | gate/up | down | complete expert |
|---|---|---|---|
|1|831.843 ->685.661|416.480 ->343.744|1259.514 ->1037.523|
|8|847.129 ->700.968|423.399 ->350.354|1272.614 ->1052.666|

Full expert latency reductions17.63% /17.28%, speedups1.214x /1.209x. M1 reference range1258.119–1261.201ms vs candidate1035.614–1039.638ms; M8 reference1271.562–1274.450ms vs candidate1052.049–1057.269ms. Every paired candidate faster; gains far exceed within-run spread. Absolute baselines shifted across runs, reinforcing use of interleaved same-run comparison rather than prior profile baseline.

Both peak metrics reset/read around each synchronized sample, identical resident A/B lane setup. Full-expert peak allocated same between lanes: M1 60,342,784 bytes, M8 60,892,672 bytes. Gate/down candidate327KB lower (326,656 bytes). Reserved117,440,512 bytes throughout. These include both resident lanes and allocator caching, not isolated deployment memory.

## Complete single-die FFN replay (includes shared expert)

Actually ran unchanged full replay on candidate AND reference: real HC/norm/router, shared FP8 expert, all6 selected FP4 experts124/35/364/75/140/80, weighted combine. Read154,137,964 payload bytes (cap201,326,592); peak78,369,792 bytes. Their entire npu_yh.json objects are identical. Shared checks and all routed up/mid/down batch-invariance checks pass. Reconstructed output equals captured historical replay bit-exact (5120 elements).

Both overall exit1, NOT acceptance success: same pre-existing M48 gate/scores/weights bit differences, and reconstructed output differs from historical pre-HC-fix decode in1225 elements/maxabs0.00390625. The same captured snapshot contains the historical decode/replay discrepancy. No tolerance weakened. This demonstrates matching bounded FFN reconstruction, not a repeated layer-performance A/B, EP8 communication or whole-model speedup. Full expert performance is established above; full layer speedup is not measured.

## Reproduce final AB

On authorized host, with scripts already deployed:
```bash
export OFFICIAL_SOURCE_DIR=/root/yuhao/deepinfer_910c_yh/src_yh/DeepInfer_fp4_ab_20261121_yh
export MOE_REPLAY_SNAPSHOT=/root/yuhao/deepinfer_910c_yh/reports_yh/stage5_full_8_15_20261119T202949060872566_yh/rank0_replay_tensors_yh.pt
export FP4_BENCHMARK_MODE=ab
export FP4_APPROVED_CANDIDATE_SHA256=58a7a16b9f67b54bad373f62764965b11fa4690021f1cd0cfa4048380f34f6a5
bash "$OFFICIAL_SOURCE_DIR/scripts/ascend910c/run_fp4_profile_20261121_yh.sh" 8
```
Use run_official_moe_replay.sh for complete bounded diagnostic (expected existing failures above). Reference uses original DeepInfer_stage4_20261119T141621_yh source. Python compile and bash syntax checks passed. Main agent's CPU256 baseline-equivalent attention failure is independent, not hidden or waived. No commit made; full-load receipt must be refreshed before any future changed-source full-model run.
