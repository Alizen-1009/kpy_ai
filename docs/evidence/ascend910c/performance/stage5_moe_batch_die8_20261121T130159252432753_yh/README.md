# First bounded FP4 baseline (partial stage 1)

Actual authorized 910c die8 run; fresh idle HBM 3159 MiB, exact one-die device guard, unchanged existing read-only checkpoint launcher. Exit0 and independent Docker inspect confirms owned CID absent. No full-model allocation/receipt bypass and no core quantization changes.

The independent wrapper reuses check_official_moe_replay.py's captured layer29–30 HC state, norm and router, then intercepts the first real selected routed expert gate/up call. It deliberately exits after measurement: this is NOT a completed replay correctness test. M=8 repeats the actual last-token activation, as the existing diagnostic does; it is NOT eight distinct decode tokens, nor a full expert/EP8 benchmark.

One warmup, three unprofiled synchronized samples:
- wall seconds: 0.890524847, 0.892645959, 0.891686252
- NPU event ms: 890.244934, 892.521545, 891.572327
- shape [8,5120] -> [8,4608]
- peak allocated after warmup/reset: 44,485,632 bytes; reserved reported after profiling: 117,440,512 bytes (different measurement windows).
- torch 2.13.0+cpu, torch_npu 2.13.0.rc1; pinned launcher image and CANN92 environment unchanged.
- fp4.py SHA256 1100b1f8caca4ce65824829fdf19eeb25f9c003e05cde8cd5ad9c1fabc89534b matches local source.

CPU+NPU trace captures 720 aten::mm calls, consistent with merged gate/up: 36 output tiles x20 K tiles. Down's expected 360 calls and full expert's 1080 remain unmeasured. Kernel CSV contains 61,308 rows, summed durations 346,737.379 us; all Type=N/A, so no dequant/GEMM percentage is claimed. Summed durations are not critical-path time. Profile context+export took 19.6304s including 16.55s offline parsing, NOT pure instrumentation overhead. Profiler warned about stopping in RECORD; capture completeness needs verification before attribution.

Replay setup logs show M48 gate bit differences (maxabs 1.24e-5), unchanged selected IDs. No claim of new numerical validation; M6/M8 gate and HC comparisons passed. Historical snapshot predates the fixed HC implementation and is used as real input provenance only.

## Reproduce on authorized host

```bash
OFFICIAL_SOURCE_DIR=/root/yuhao/deepinfer_910c_yh/src_yh/DeepInfer_stage4_20261119T141621_yh \
MOE_REPLAY_SNAPSHOT=/root/yuhao/deepinfer_910c_yh/reports_yh/stage5_full_8_15_20261119T202949060872566_yh/rank0_replay_tensors_yh.pt \
bash "$OFFICIAL_SOURCE_DIR/scripts/ascend910c/run_fp4_profile_20261121_yh.sh" 8
```

Shell note: set/export OFFICIAL_SOURCE_DIR first, or use the literal absolute script path; inline assignment does not expand the same command's argument variable.

New scripts are in ref/DeepInfer/scripts/ascend910c. Remote source directory contains the two added scripts only; core unchanged. Raw complete trace remains on host at the identically named reports_yh directory. Recursive SCP hit 120s timeout; local trace subtree is PARTIAL and must not be presented as complete. Small JSON reports, before/after, run log and independent cleanup were separately retrieved.

Next: extend bounded capture to M1 plus M8 full expert gate/up, SwiGLU and down; explicitly record selected ID and tensor hashes, source-tree manifest and driver/CANN versions; use explicit profiler schedule/step and validate capture coverage; summarize by kernel name/correlation rather than N/A Type, separate host dispatch gaps from device busy time. Only then select a core optimization. This first measurement supports tiny-mm launch volume as a candidate, not yet proven dominant runtime attribution.
