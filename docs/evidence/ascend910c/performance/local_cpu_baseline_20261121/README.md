# Local CPU baseline before optimization

No core quantization changes at capture. This is macOS CPU synthetic testing, not the pinned Ascend environment, official payload validation or performance evidence.

Command (from project root):
```bash
PYTHONPATH=ref/DeepInfer uv run --no-project --python 3.12 --with 'torch>=2.9' --with numpy --with safetensors --with transformers --with pillow --with pytest --with einops --with pyzmq --with psutil --with posix-ipc python ref/DeepInfer/scripts/ascend910c/check_official_cpu_tests.py --report /tmp/deepinfer-perf-baseline-cpu-20261121-v6.json
```

253 tests executed, 1 failure, 0 errors. The pre-existing baseline failure is `test_shared_sparse_c2_attention_prefill_then_decode`: 1/4096 elements differ, max absolute difference 1.1920928955078125e-07, with zero tolerance. Do not weaken the test or label this full-suite PASS. Source hashes and exact versions are in results.json. FP4 compute's five targeted tests also passed in an earlier direct unittest run. Initial attempts lacked dependencies / used Python 3.11; these were environment setup failures, not core changes.

History consulted: `/Users/alizen/.pi/agent/skills/model-pr-optimization-history/sglang/deepseek-v4/README.en.md`, reviewed-kernel introduction (lines 1–110). PRs #38829/#38944/#39098/#39305 concern attention selection and #39123 concerns KV storage, not an Ascend FP4 expert replacement. No CUDA/Blackwell path or FP4 KV format will be presumed equivalent to this expert's group32 E8M0, BF16-rounded FP32 K256 accumulation contract. Optimization selection awaits actual expert profile.
