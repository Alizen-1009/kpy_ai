# Nonuniform scale discrepancy explained by effective weight-scale truncation

This supersedes the unresolved diagnosis in nonuniform-scale-blocker.md, not its observations.

## Controlled falsification

`run_20261121T140028619922250`: K64 and K256, one group, eight sparse one-hot signed A8 rows, signed INT4 columns, N256. Separate weight-only, token-only, both nonuniform scales. Full a, nonzero q rows, scale arrays and output arrays saved in results.json. Frozen script enumerates FP64, FP32 multiply orders, BF16/FP16 rounding of scales/product/intermediates, and truncation hypotheses.

All six cases match **truncate weight scale low16 FP32 mantissa bits** exactly. Token-only matches untruncated standard math. Other candidate rounding stages fail weight-only/both cases. Thus no tolerance increase is needed. This is truncation toward zero to BF16 representable weight scales, NOT ordinary round-to-nearest `.to(bfloat16)`.

Effective tested equation:

`BF16_RNE(FP32(FP32(INT64_dot) * bitcast_f32(bitcast_i32(s) & 0xffff0000)) * t)`.

## Independent dense/real-shape check

`run_20261121T140108510716264`: original nonuniform random dense 12-case suite repeated. All 12 match this prediction exactly, max_abs0, including 5120->4608 and 2304->5120, M1/M8, empty/uneven groups, ND and NZ. Input A8 compared after six calls: unchanged in every case. This is output behavior on this installed path, not universal documentation or a guarantee for bias-enabled/fused variants.

Both successful runs exit0 and independent docker inspect confirms owned containers absent. Fresh die8 guard and no checkpoint access unchanged.

A K32 minimal attempt returned error561103 / EZ0026: K must be divisible by64; retained run_20261121T135948945458280. Replaced with K64 rather than hiding failure.

Upstream master test downloaded to upstream_test_npu_grouped_matmul.py, SHA256 7977f049dfb67987dafac99df2ede172f568b914323284485323125816170d55. URL https://raw.githubusercontent.com/Ascend/op-plugin/master/test/test_custom_ops/test_npu_grouped_matmul.py . It is not the installed-version normative spec: skipped A8W4 bias/two-path test and low13 scale handling must not override actual bias=None observations. Installed kernel implementation has not yet been source-matched; why it truncates exactly16 low bits remains an internal implementation question.

Next prototype should explicitly record effective truncated weight scales and use them in its same-quantization oracle. Keep loss from ideal RTN scales separately measurable; do not silently treat full FP32 requested scales as effective. Actual-weight/model quality remains untested.
