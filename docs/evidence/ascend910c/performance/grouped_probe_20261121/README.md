# Grouped W4A8 device capability probe

Actual die8 execution, original task torch 2.13.0+cpu / torch_npu 2.13.0.rc1, original CANN92 task SDK. No checkpoint accessed. Fresh policy+idle check before each invocation, only davinci8 exposed (plus manager/devmm/hisi control nodes); 240s timeout; self-owned container cleanup and independent inspect recorded. No shared environment modification.

## Successful contract

`run_20261121T135327033992219`: 12/12 cases match INT64 CPU integer matmul, FP64 scale multiplication, then BF16 rounding exactly. Synthetic signed INT4 [-8,7], A8 [-127,127], per-channel weight scale 1/128, per-token scale 1/64. Shapes K,N = 256,256; 5120,4608; 2304,5120. Three experts, counts [1,0,0] and [1,0,7], counts int64 on NPU, group_list_type=1, group_type=0, split_item=2. Both ND and NZ pass.

Packing along N: even low nibble, odd high nibble. Crucial: NZ cast operates on packed **int8** [E,K,N/2] BEFORE view(int32), not after. Scale FP32 bits reinterpreted int32, masked into int64 [E,1,N]. Ordinary GMM uses bias=None; no assist correction is required for this contract. Output BF16.

Successful run source and launcher snapshots included, hash in device.log. Exit 0, inspect confirms container absent. Peak allocation is cumulative allocator maximum, not isolated per-case delta. Timing is first execution plus five repeats (not statistically robust benchmark). Real-shape steady wall approximately 0.10–0.23ms, events 0.09–0.22ms; no whole-FFN or model speed claim.

## Failed contracts retained

135150: supplied reference-style assist as GMM bias and cast int32 to NZ; numerical oracle fails. 135231: bias=None gives exact ND, but int32-first NZ gives incorrect results. Neither result is acceptable. These exploratory runs only logged source hashes, not frozen source copies; final successful run includes copies.

## Remaining

This is synthetic operator capability, not original-weight quality, calibration, real FFN, route weighting or full-model validation. Only power-of-two constant scales tested. Fused `_C_ascend.grouped_matmul_swiglu_quant_v2` has NOT passed device testing. CPU-only extension import attempt aborted; initial inventory errors do not demonstrate operator absence. Image 2.10 fallback not needed for ordinary GMM because task 2.13 succeeded. Need separately sandbox fused extension test, nonuniform scales and additional groups before final integration decisions.

Inventory raw log retained; use image_driver_inventory.clean.json for machine parsing (original .json contains trailing driver diagnostic).
