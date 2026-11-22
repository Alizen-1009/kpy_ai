# Symmetric warmup + attribution rerun

Exit0; full 12 real GMM effective-oracle checks remain exact, A8 CPU codes/scales exact, input unchanged, quality_pass=null. Both lanes warmup1 before three alternating paired full timings. Extra section timings performed AFTER full samples with independent synchronization/event boundaries; do not interpret their sum as exact full timing.

Median full wall FP4=8.95007s, W4=2.30525s (~3.88x this diagnostic implementation only). Separate sections: FP4 shared2.29884s/routed6.63375s/combine0.000368s; W4 shared2.29542s/routed including A8 quant0.001089s/combine0.000373s. Now shared dominance has actual evidence, rather than prior inference.

Peak allocated FP4~297.9MB/W4~424.1MB; peak reserved488636416 bytes both. Same reset window around each full sample, both original FP4 and derived W4 plus shared resident. These are not independently provisioned serving footprints.

FP4 output exactly matches captured replay hash7ae7f390f6f98ea17b143328d6643244df5346ebb479bc35565f8b49931d45b3.

Error decomposition (tensor-level, NOT full factorial FFN causal attribution): decoded BF16 weight->requested RTN relativeL2 0.16594–0.17786 across12 matrices; requested->effective truncated scale weights relativeL2 ~0.00195313. Real BF16 input->old FP8 relativeL2 .0271168; BF16->A8 .00850979; old FP8->A8 .0285748. CPU independently recomputed FP32 SwiGLU+clamp+route on first GEMM output vs NPU mid: maxabs1.19209e-7, relativeL2 3.38444e-8. Thus device mid is not used as sole evidence of SwiGLU correctness. Complete CPU float/fakequant FFN intervention outputs are not yet implemented; these local losses cannot be summed to explain .3038658 final output relativeL2.

All raw E8M0 scales observed in [119,122]. Script explicitly rejects 0/255 (indeed anything outside1..254) before pow decoding; no incorrect special-byte semantics accepted.

operand_manifest.json independently stores original selected packed operand and scale SHA256 (fused gate/up after lossless concatenation, plus down). It is NOT a hash of entire checkpoint shards, whose full reads would exceed bounded payload authorization. cleanup_independent.json stores separate post-run docker inspect result. Derived artifact path/hash and frozen script hash in w4_ffn.json.

Previous attempt142108 rejected oversized activation decode _tile(0,1,0,5120), retained failure bundle. Fixed by twenty allowed K256 tiles; did not relax decoder bound or numerical gates. No core/backend changes, checkpoint read-only, only fresh-idle die8.
