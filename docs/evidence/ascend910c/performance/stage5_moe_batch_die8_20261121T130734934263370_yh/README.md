# Real layer30 expert124 baseline + M1 profile

Run completed on authorized die8, fresh idle3158MiB, exact exposure checked inside unchanged replay input lane. Original checkpoint/view read-only. Docker exit0; cleanup_independent.json confirms exact owned CID absent. No core modifications, no full allocation, no receipt bypass. Historical evidence unchanged.

Real captured HC state -> official norm/router -> selected expert124 (route weight0.6009923219680786). M1 uses its real last-token activation; M8 repeats that activation, NOT eight requests. Down consumes actual gate/up -> weighted SwiGLU -> FP8 quantization output. Input/scale hashes, snapshot hash and all deepinfer Python source hashes in fp4_baseline.json. Torch2.13.0+cpu, torch_npu2.13.0.rc1; same pinned launcher image/CANN92.

Each section: one warmup then three synchronized wall/event repetitions; both allocated/reserved peaks reset before and read after exactly the same three-call window. Existing resident tensors/cache remain included. No empty-cache perturbation.

Median wall milliseconds:
| M | gate/up | SwiGLU+quantize | down | full expert |
|---|---:|---:|---:|---:|
|1|881.737|8.690|439.637|1328.790|
|8|894.546|8.303|446.680|1346.725|

Raw all-three wall/event samples in JSON. Full expert allocated peaks M1=60,313,088 bytes; M8=60,676,096 bytes. Reserved=117,440,512 bytes for both. Separate stage timings are not additive synchronized critical-path attribution.

M1-only profiler explicit wait0/warmup1/active1/repeat1 plus step() at boundaries. No previous RECORD-stop warning. Active full-expert wall2234.321ms vs unprofiled median1328.790ms (~68% overhead); warmup+capture+export36.284s, including31.650s offline parse. Do not transfer profiled percentages to unprofiled wall time.

Remote parsed complete CSV: 1080 aten::mm /1080 MatMulV2 kernels confirms one full expert's720+360 tiles. 90,167 kernel rows. Across2233.957ms device span, union busy495.860ms (22.20%), uncovered1738.097ms (77.80%). Uncovered time is NOT proven entirely CPU: launch starvation/host bookkeeping/synchronization are hypotheses, not a precise Python percentage.

Measured kernel sums (not necessarily disjoint):
- RightShift2178:125.834ms (~25.38% busy-union denominator)
- LeftShift2178:75.691ms (~15.26%)
- RepeatInterleave2160:54.332ms (~10.96%)
- Index1080:45.709ms (~9.22%), plus IndexCheck15.636ms
- MatMulV2 1080:2.308ms (~0.47% busy,0.103% profile span)
- Host self: empty_tensor226.349ms, leftshift130.295ms, copy121.025ms, where101.183ms, rightshift100.599ms; aten::mm9.742ms. These are profiler aggregates, not exclusive end-to-end percentages.

Priority hypothesis: fuse/reduce repeated per-K256 decode/scale pointwise and launch/allocation work, NOT enlarge GEMM tiles. Specific fp4.py expressions: `tile.gemm_operand()`, `torch.stack((bits & 15, bits >> 4), ...)`, indexed magnitudes/sign where, `sf.repeat_interleave(32, dim=1)`, `(values * expanded_sf).to(torch.bfloat16).float()`, and repeated `a._tile(...)`. Right/left shifts also originate in scale/activation decoding, so don't attribute all201.524ms solely to packed nibble extraction. Inspect matching source before choosing exact fusion. Preserve BF16 intermediate rounding, ascending K256 accumulation, A64x256/B128x256/single64x128 acc bounds. MM arithmetic alone is not the leading measured kernel cost. No optimization implemented.

Reproduce (host):
```bash
export OFFICIAL_SOURCE_DIR=/root/yuhao/deepinfer_910c_yh/src_yh/DeepInfer_stage4_20261119T141621_yh
export MOE_REPLAY_SNAPSHOT=/root/yuhao/deepinfer_910c_yh/reports_yh/stage5_full_8_15_20261119T202949060872566_yh/rank0_replay_tensors_yh.pt
bash "$OFFICIAL_SOURCE_DIR/scripts/ascend910c/run_fp4_profile_20261121_yh.sh" 8
```
Full trace retained remotely in reports_yh/this-directory/trace. Only bounded summary downloaded. summarize_fp4_profile.py parsed remotely and independently checked cleanup. Launcher was subsequently extended to invoke this same summarizer automatically and archive scripts; that automation addition was not rerun (measurement itself and summarizer ran successfully separately). Existing replay preliminary M48 gate differences remain in run log; wrapper intentionally exits after measurement, not a correctness acceptance result. User independently ran5 numerical CPU tests; full suite not claimed.
