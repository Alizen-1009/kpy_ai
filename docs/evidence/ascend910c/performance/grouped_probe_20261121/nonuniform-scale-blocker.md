# Nonuniform scales: hardware integration gate remains closed

Actual guarded die8 run `run_20261121T135720864230145`, torch 2.13.0+cpu / torch_npu 2.13.0.rc1. Script and launcher frozen in run folder, SHA256 `8b9599de515307269832da0485fa32b3de02a11e7386dd164bc03453675dc765`. Exit0 means the harness completed, NOT a numerical acceptance pass. Container independently inspected absent.

Compared INT64 accumulation followed by FP64 scales and final BF16 rounding; also independently used FP32 multiplication at each scale step followed by BF16 rounding. Random seed42; positive per-channel scales `0.0001+rand*0.031`, per-token `0.0001+rand*0.037`. Same 12 shapes/counts/layout cases as constant-scale run.

All 12 executed, no nonfinite output. All 12 differ from both CPU references, maximum normalized error 2 BF16 ULP in each case. Absolute max errors range 0.0078125–0.5. CPU FP32-vs-FP64 final rounding differs at just one element in two cases and zero elsewhere; it does not explain hardware error. This is not a quality PASS or permission to relax tolerance. The one-ULP diagnostic bound was checked explicitly and failed.

Per user instruction, stopped before real-weight artifact conversion or single-layer hardware integration. Need explain hardware scale/dequant rounding contract (possibly intermediate rounding or scale encoding semantics; unproven) with controlled cases or authoritative implementation, then rerun gate. Do not adopt a two-ULP bound merely because it fits observations.

An initial attempt `run_20261121T135659952052996` encountered Python IndentationError before operator work; its exit/log/cleanup evidence is retained. Fixed and local py_compile passed before the actual run above. No production backend, official checkpoint, or shared environment modified.
