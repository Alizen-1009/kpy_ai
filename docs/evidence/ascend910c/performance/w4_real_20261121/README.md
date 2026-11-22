# Real layer30 grouped W4A8 RTN experiment

Completed guarded die8 run 20261121T141559988943176, exit0. Original checkpoint view+archive read-only. Same bounded replay reader (192MiB payload cap) and six expert IDs 124/35/364/75/140/80; not full model and no production backend edits. Source copied to independent `/root/yuhao/deepinfer_910c_yh/src_yh/DeepInfer_w4_real_20261121_yh`. No full-model receipt bypass.

Original FP4 E2M1/E8M0 decoded on CPU with BF16 rounding then uncalibrated per-channel RTN maxabs/7. Artifact retains logical codes, ND packed bytes, requested FP32 scales, effective low16-truncated scales, decoded hashes, weight code-boundary rates and real BF16 norm input. Device uses NZ cast of packed int8 before int32 view and bias=None. Original shared expert remains FP8. Routed activation takes BF16 norm, explicit device A8 quantization in timed boundary; route weight stays after FP32 SwiGLU/clamp and before second A8 quantization. Combine is FP32 in expert-ID order then BF16.

All 12 real GEMMs match effective-scale CPU integer oracle exactly. Device activation codes and scales match CPU helper for first and mid quantization; BF16 input unchanged. This is kernel-contract validation, NOT quantization quality approval (`quality_pass=null`).

Three alternating full block pairs include shared, six routed experts, quantization and combine; exclude norm/router/conversion/load/CPU oracle. FP4 wall 8.5032/8.5206/8.4996 sec; W4 2.1957/2.1929/2.1893 sec. Median ratio about3.88x only for this diagnostic block; shared reference implementation dominates remaining seconds, not representative optimized production FFN or TPS. Peak allocated FP4 about297.9MB and W4 424.1MB with both weight representations resident; not standalone serving memory estimates.

Output vs original FP4/FP8 block: maxabs0.33203125, MAE0.06342772, RMSE0.07963759, relativeL2 0.30386584, cosine0.96365382; no nonfinite. Substantial quantization/input-policy difference: cannot claim model quality. A8 code-boundary fractions: initial0.0001953125, mid0.0004340278 (not measured clipping-event rates). Calibration absent; not SSZ/AWQ.

Derived artifact remains on target (not downloaded ~hundreds MB):
`/root/yuhao/deepinfer_910c_yh/reports_yh/stage5_moe_batch_die8_20261121T141559988943176_yh/derived_w4a8.pt`
SHA256 `146dfaaf3641e1d2e4698181be376caa99a95b9017e854934e26088019a5b41f`.

Final script hash48de4241a089f2c5f81893aa664c3edb3d18ff43ea05ea4c94c8132533590659. Script/launcher/report/logs frozen locally. Input hashde71e5c097996f61d6af5b53aa6e45367c6f7dfebf312ed3fff6b5014d20b538.

Independent post-run inspect: container46e2abcc937601aa43dcabeeb552b15031e4321c31adf8a21f13ce292d9bfb21 absent (return1, No such object). Initial run141355 completed measurement but generic replay wrapper KeyError missing `passed` caused exit1; retained all evidence. Fixed harness result field and repeated entire run; no numerical gate weakened.

Remaining before stronger claims: calibration set/model-level quality; separate attribution of initial FP8->A8 change and weight RTN; CPU-vs-device SwiGLU numerical comparison beyond downstream GEMM oracle; independent original-payload hash manifest and captured-reference output gate; steady production-oriented baseline. No fused custom op claim.
