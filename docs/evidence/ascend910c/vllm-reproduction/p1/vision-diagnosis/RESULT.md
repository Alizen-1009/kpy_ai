# P1 vision loader diagnosis

## Confirmed cause

VISION=0 removes the entire vision tower, NOT just bias parameters. The loader nevertheless demands every vision checkpoint parameter. This deterministically produces the reported first key failure.

Evidence is copied read-only from stopped full CID `67993945c3595dc9bc76bbddc429c2c4d7d49be7cadd5b3d4b1bdbd7795e3525`. No new container, NPU use, service retry, shared edit or launcher/runtime-map edit.
Image pinned by P1 argv: `sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef`.

* `../p1-20261121T203514Z-4f842308/container.log:1,5`: vision=0 and actual `--limit-mm-per-prompt {"image": 0}`. Error at line 272.
* Runtime `/vllm-workspace/vllm-ascend/vllm_ascend/models/deepseek_v41/vl_model.py:68-90` (local `v41_vl_model.py`): image limit zero => image_enabled false => vision/aligner/image parameters remain None.
* V41 inherits V4 wrapper (`v41_vl_model.py:39-41`). Runtime `deepseek_v4/vl_model.py:238-259`: inherited loader builds named_parameters, intercepts vision names, raises at 252 before passing them to language model.
* `deepseek_v4/vision.py:112-120`: actual aligner w1 and w2 use nn.Linear default bias=True. Thus the no-bias-wrapper hypothesis is false.
* `_vision_parameter_name`, `vl_model.py:40-46`: removes optional model. only; unprefixed aligner.w1.bias maps identically. Thus prefix-bug hypothesis is false for this failing key.
* Frozen reference `patches/files/model.py:1570,1619-1651`: deferred vision prefixes are filtered by language backbone only. They cannot prevent the outer wrapper's earlier KeyError while iterating its generator.

## Checkpoint

`probe.py` reads published config + actual index + safetensors headers only (8-byte header length then bounded JSON). `model-header.json` preserves all 266 vision tensor names/shapes/dtypes. No tensor payload was loaded.
Config vision hidden_size=1024, downsample_ratio=3, num_hidden_layers=32; text hidden_size=5120. No explicit aligner-bias field in published config. w1 shape [5120,9216], bias [5120]; w2 [5120,5120], bias [5120]. 9216 = 1024*3**2; all consistent with actual class.
Full model hash verification is historical established evidence, not newly re-streamed here: `download/recovery-3/RESULT.md`, `assets-final/recovery-3-verified_report.json`, `assets-final/recovery-3-independent.sha256` record 120/120 verified files and independent assembly hashes. This diagnosis does not claim a new full-payload hash pass.

## CPU reproduction and limitations

Run `python3 reproduce.py`; actual captured loader and name mapping are AST-extracted/executed with shape-only stand-ins, no torch/NPU. `reproduce.stdout`: exact KeyError with absent tower; with complete parameter-name/shape dictionary, all 266 pass. This is a loader-contract reproduction, NOT full constructor execution or numerical inference validation. Enabled-case dictionary comes from checkpoint, so that pass alone does not prove every real tower parameter matches; actual aligner dimensions/bias independently match the source.

## Minimal recommendation (not applied)

Do NOT drop bias, skip missing vision keys, change dtype, or upgrade main. To retain strict loading while keeping image requests disabled, change ONLY V41 constructor allocation predicate at `deepseek_v41/vl_model.py:68-71` to `image_enabled = config.vision_n_layers > 0` (prefer rename to tower_present in a reviewed patch). Keep multimodal request limit at zero and loader strict. This allocates and loads the actual BF16 tower even for text-only serving; budget its replicated memory before restart. Alternatively enable image limit >0 in a separately approved launch configuration, which changes advertised capability and is not applied here.

Reference AGENTS read. Search of frozen reference patches and serve scripts found no packaged vl_model.py/vision.py frontend patch to simply mount. Therefore cannot substantiate 'one of the ten payloads omitted an existing frozen fix'. Frozen native_sources snapshots named in MANIFEST are evidence snapshots, not proof of released/installable patches. Proposed fix needs a NEW frozen V41 wrapper patch + hashes/explicit runtime mapping after approval, not an automatic main upgrade. Launcher/runtime-map remain untouched.

Before any real restart: CPU/meta instantiate actual V41 wrapper against published config under limits 0 and >0; compare exact 266 vision names/shapes and verify strict missing/extra-key negative controls, preserving bias values and precision. Current loader-only test is necessary but not sufficient for that gate. Then a single approved startup/readiness/smoke run; no blind retry performed.
