# M1 single-die complete FFN compute A/B

Actual run passed, Docker exit0; independent cleanup confirms owned CID absent. Fresh die8 idle guard3156MiB; exact die8 exposure; original checkpoint view/archive read-only. Same new isolated source copy DeepInfer_fp4_ab_20261121_yh, not original accepted source. Frozen reference1100b1f8... vs approved candidate58a7a16b... verified in script. No core edits or full-model allocation/receipt bypass.

Scope: real layer30 M1 norm/router output with fixed IDs124/35/364/75/140/80 and actual weights. Timed block includes full shared FP8 expert, all six routed FP4 experts with weighted SwiGLU quantization, ordered FP32 combine then BF16 output. Excludes HC/norm/router computation, checkpoint reads, CPU oracle, EP8 communication and decoder. Original check_official_moe_replay.py construction is reused by adapting only its harness source in memory. Preliminary historical diagnostic comparisons remain in log, outside timing and not this benchmark's acceptance criteria.

All original quantized weights loaded first and resident together; payload154,137,964 bytes <=201,326,592 cap. No persistent full-expert decoded weights. One warmup each, three pairs AB/BA/AB. Output buffers and metadata prepared before timing; actual shared/routed arithmetic and combine remain inside. Same-window peak allocated/reserved reset/read for each synchronized sample. CPU output copies occur after timing; last lane outputs compared bitwise via hashes after all timings.

Wall seconds:
- reference9.962505,10.274681,10.002584; median10.002584
- candidate8.578886,8.730376,8.559376; median8.578886
- median latency reduction14.233%, speedup1.166x; paired reductions13.89%,15.03%,14.43%. No overlapping sample ranges; benefit exceeds measured variation.

Event milliseconds:
- reference9962.104,10274.499,10002.408
- candidate8578.695,8730.196,8559.210

Max allocated both190,231,552 bytes; reserved both241,172,480 bytes. First reference sample allocated190,220,800 differs10,752 bytes due to previous output lifetime; subsequent samples identical. Resident packed experts, shared weights and setup intermediates are included; this is not per-model memory projection.

Final reference, candidate and existing captured replay full output share SHA256:
`7ae7f390f6f98ea17b143328d6643244df5346ebb479bc35565f8b49931d45b3`.

This benchmark passes its explicitly scoped A/B+captured-replay equality. It does NOT rewrite previous full diagnostic exit1 results (historical pre-HC-fix decode mismatch and M48 gate differences), and does not claim full-model acceptance. npu_yh.json contains payload limits, ffn_ab.json contains timings/hashes/source manifest; original script/launcher copies and logs are included.

Reproduce on authorized host:
```bash
export OFFICIAL_SOURCE_DIR=/root/yuhao/deepinfer_910c_yh/src_yh/DeepInfer_fp4_ab_20261121_yh
export MOE_REPLAY_SNAPSHOT=/root/yuhao/deepinfer_910c_yh/reports_yh/stage5_full_8_15_20261119T202949060872566_yh/rank0_replay_tensors_yh.pt
export FP4_BENCHMARK_MODE=ffn
export FP4_APPROVED_CANDIDATE_SHA256=58a7a16b9f67b54bad373f62764965b11fa4690021f1cd0cfa4048380f34f6a5
bash "$OFFICIAL_SOURCE_DIR/scripts/ascend910c/run_fp4_profile_20261121_yh.sh" 8
```
New benchmark_fp4_ffn_ab.py compiled, launcher bash-n checked before execution. No commit. No claimed decoder/EP8 TPS.
