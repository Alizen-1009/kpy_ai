# SPDX-License-Identifier: Apache-2.0
"""Controlled official-FP4 expert computation; not a model backend.

Accepts explicit BF16 or row-group32 FP8Activation operands. This numerical
bring-up seam does not automatically select the model's activation policy,
route tokens, communicate, or select itself in native grouped GEMM.
"""
from __future__ import annotations

import torch

from deepinfer.quantization.activation import FP8Activation
from deepinfer.quantization.official import OfficialQuantizedOperand


def expert_operand(weight: torch.Tensor, local_expert: int) -> OfficialQuantizedOperand:
    """Select a local physical slot (not a global HF expert ID), without copies.

    Raw loading retains replicas and ownership order. No INT8 dtype inference
    or W8A8/per-channel interpretation is permitted. Storage stays caller-owned.
    """
    if getattr(weight, "official_layout", None) != "fp4_expert":
        raise ValueError("Expected an explicitly loaded official FP4 expert bank")
    if weight.ndim != 3 or weight.dtype != torch.int8:
        raise ValueError("Expected packed INT8 [E,N,K/2] expert storage")
    scales = getattr(weight, "sf", None)
    if not isinstance(scales, torch.Tensor) or scales.ndim != 3 or scales.shape[0] != weight.shape[0]:
        raise ValueError("Expected raw scales with the same local expert count")
    if type(local_expert) is not int or not 0 <= local_expert < weight.shape[0]:
        raise IndexError("Local physical expert slot out of range")
    return OfficialQuantizedOperand(weight[local_expert], scales[local_expert], "fp4_expert")


@torch.no_grad()
def fp4_expert_gemm_nt(a: torch.Tensor | FP8Activation, b: OfficialQuantizedOperand, out: torch.Tensor) -> None:
    """Write out = A @ packed E2M1 B.T with bounded decoded tiles.

    Numerical contract: E2M1 * exact E8M0 -> BF16 rounding -> FP32
    accumulation -> output rounding. This is NOT native FP8 x FP4 equivalence.
    Weight/scale tiles are at most [128,256]/[128,8]; activations [64,256],
    accumulator [64,128]. No full expert decode or persistent decoded cache.
    Output is caller-allocated and capped at 1M elements; empty M/N/K work.
    Inputs and output must not share storage. Errors are not retried with a
    different precision or backend. Meta tensors are planning-only.
    """
    if not isinstance(b, OfficialQuantizedOperand) or b.layout != "fp4_expert":
        raise TypeError("An explicit official FP4 operand is required")
    a_data = a.data if isinstance(a, FP8Activation) else a
    if not isinstance(a, FP8Activation) and (not isinstance(a, torch.Tensor) or a.ndim != 2 or a.dtype != torch.bfloat16):
        raise TypeError("This bring-up seam requires 2D BF16 or explicit FP8Activation")
    m, k = a_data.shape
    n, b_k = b.logical_shape
    if k != b_k or tuple(out.shape) != (m, n):
        raise ValueError("Incompatible official FP4 GEMM shapes")
    if out.dtype not in (torch.bfloat16, torch.float32):
        raise TypeError("Output must be BF16 or FP32")
    if a_data.device != b.data.device or out.device != a_data.device or a_data.device.type == "meta":
        raise ValueError("Non-meta input, weight, scales and output must share a device")
    if out.numel() > 1 << 20:
        raise ValueError("Official FP4 GEMM output exceeds the per-call budget")
    if out.numel():
        ptr = out.untyped_storage().data_ptr()
        inputs = (a_data, a.scales, b.data, b.scales) if isinstance(a, FP8Activation) else (a_data, b.data, b.scales)
        if any(t.numel() and t.untyped_storage().data_ptr() == ptr for t in inputs):
            raise ValueError("Output must not share input storage")
        # Reject overlapping/as_strided output views before partial writes.
        if torch._debug_has_internal_overlap(out) != 0:
            raise ValueError("Output must have a non-overlapping dense layout")
    # A compact E2M1 magnitude table, including signed zero via sign application.
    magnitudes = torch.tensor([0., .5, 1., 1.5, 2., 3., 4., 6.], dtype=torch.float32, device=a_data.device)
    for row in range(0, m, 64):
        end_row = min(row + 64, m)
        for col in range(0, n, 128):
            end_col = min(col + 128, n)
            result = torch.zeros((end_row - row, end_col - col), dtype=torch.float32, device=a_data.device)
            for inner in range(0, k, 256):
                end_k = min(inner + 256, k)
                # K tile boundaries are even and group32-aligned. Only the
                # final tile may end inside a scale group.
                tile = OfficialQuantizedOperand(
                    b.data[col:end_col, inner // 2:end_k // 2],
                    b.scales.view(torch.uint8)[col:end_col, inner // 32:(end_k + 31) // 32].view(torch.float8_e8m0fnu), "fp4_expert",
                )
                data, sf = tile.gemm_operand()
                bits = data.view(torch.uint8).to(torch.int32)
                codes = torch.stack((bits & 15, bits >> 4), dim=-1).flatten(-2)
                values = magnitudes[(codes & 7).long()]
                values = torch.where((codes & 8) != 0, -values, values)
                expanded_sf = sf.repeat_interleave(32, dim=1)[:, :end_k - inner]
                decoded = (values * expanded_sf).to(torch.bfloat16).float()
                a_tile = a._tile(row, end_row, inner, end_k) if isinstance(a, FP8Activation) else a[row:end_row, inner:end_k].float()
                result.add_(torch.mm(a_tile, decoded.mT))
            out[row:end_row, col:end_col].copy_(result)
