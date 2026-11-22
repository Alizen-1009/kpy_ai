# DeepSeek-V4.1-Flash W4A8 量化链路复现验证（本机 A3 / chips 8–15）

> 执行者：quantval 子代理　执行窗口：2026-09-15 22:35 → 2026-09-16 00:30 (+08)
> 产物根目录：`/path/to/models/out/quantval_20260915_2235/`
> 容器：本任务量化容器（`PRESET=back8`，cpuset 320-639 / mems 4-7，`ASCEND_RT_VISIBLE_DEVICES=8..15`）
> 本报告所有数字均来自该目录下日志与哈希文件，逐项给出证据路径。

---

## 1. 结论摘要

把交付给 A2 的完整量化链路在本机 A3 的**后 8 chip**（物理 chip 8–15）上从零重跑，
并逐阶段与"当前正在跑的权重"（真值）比对：

| 阶段 | 产物 | 判定 | 一句话证据 |
|---|---|---|---|
| 1 主干 W4A8 | `quantval_.../stage1` | **有差异（数值等价级）** | 185,734 键 / 标签分布 / 形状-dtype 完全一致；52.5% 张量 bit-exact，47.5% 有极小数值差；**分片数 72 vs 真值 80** |
| 2 DSpark draft | `quantval_.../dspark` | **bit-exact** | `mtp-0000{1..4}` + `mtp-vocab` 5 个分片 `sha256` 全等真值 |
| 3 Engram int8 | `quantval_.../engram-int8` | **bit-exact** | 4 个文件（206 GB）`sha256` 全等真值 |
| 4 Vision + qrot | `quantval_.../{dspark-vision,qrot-vision}` | **bit-exact** | 旋转前 370bc89f…、旋转后 db6f1a7c… 均与真值逐字节相同 |
| 5 mtpq | `quantval_.../dspark-mtpq` | **bit-exact** | `mtpq-0000{1..4}` 4 分片 + `quant_model_description.json` `sha256` 全等真值 |

**核心结论：脚本层面可复现 —— 除阶段 1 外，4 个后续阶段在完全不同的输入主干（我自己的 stage1）
上依然逐字节复现了真值；阶段 1 的差异不来自脚本、源码树、标定数据或工具版本，而来自
DP 宽度（真值 DP16 vs 本次 DP8）—— 这一点已由"同一份输入、仅把 rank 数 8→4"的对照实验
直接证明（40.6% 张量产生差异，族别与幅度同 DP16 对照一致，见 §5.2）。**

**对 A2 的直接含义：A2 用 8 卡跑，拿到的权重在数值上等价、但不会与我们当前的
`v41-w4a8-stage1` 逐位相同。**

---

## 2. 环境与源码指纹

证据：`quantval_20260915_2235/logs/env_fingerprint_20260915_223729.txt`、`logs/device_id_mapping.txt`、`logs/stage0_setup.log`

| 项 | 值 |
|---|---|
| 主机 | `Linux 6.6.0-159.4.3.154.oe2403sp4.aarch64` |
| 镜像 | `quay.nju.edu.cn/ascend/vllm-ascend:deepseek-v4.1-flash-a3`，image id `sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef`，RepoDigest `sha256:2c906b38ad3cc9ed9badfe3d09451d194fa09a07e5c6d62a66b111731e626060` |
| 容器内软件 | Python 3.12.13；torch 2.10.0+cpu；torch_npu 2.10.0.post4；transformers 5.14.1 |
| msmodelslim | HEAD `e05b47190392bace361a012f115d64f4abcca30d`（分支 `dsv41-w4a8`），基线 `92e219fa9565a5bad84d90474a27bb11524d691c` |
| **源码树脏否** | `git status --porcelain` 仅 2 条，且均**不影响主配方**：一条未纳入发布的实验配方（未跟踪文件）、`?? msmodelslim/config_repo`（editable 安装所需软链）。**主配方与适配器代码无本地改动。** |
| 配方 | `deepseek_v4_1_flash_w4a8.yaml` md5 `e5ed2b07b65b6be5799371441c25306c` / sha256 `d3d9bdc6f2f249407dbbdb9faea8414a7d448a153c38f9ea1c36e3451deb7345` |
| 标定数据 | `lab_calib/mix_calib.jsonl` md5 `89de25161b089053b55338e20002b25b` / sha256 `802b21aef7585794e534643d17a4c316b6eed1f0ea22fe405e6d228ac4024f8b`（75,929 B） |
| 装配输入 | `DeepSeek-V4.1-Flash-stage1`（47 项、软链式装配；`num_hidden_layers=40`、`num_nextn_predict_layers=0`、`engram_layer_ids=[]`、`max_position_embeddings=8192`） |
| 官方基座 | `DeepSeek-V4.1-Flash`（476 GB / 60 项） |
| 源码 mtime | `model.py` 2026-09-11 21:58、`model_adapter.py` 21:09、配方 19:59 —— **均早于真值分片写入时间（22:28–22:50）**，即真值是用当前树内容产出的 |

### 2.1 设备号口径（重要，与任务书正文不同）

容器内 `ASCEND_RT_VISIBLE_DEVICES=8,9,...,15`，torch 看到的是**重编号后的 0–7**：

```
device_count 8
set_device 0  OK
set_device 7  OK
set_device 8  FAIL RuntimeError ExchangeDevice
set_device 15 FAIL RuntimeError ExchangeDevice
```

⇒ `--device_id` 必须写 **`0 1 2 3 4 5 6 7`**（与 A2 复现报告中的写法一致）；
任务书正文里的 `DEVICE_IDS="8 9 ... 15"` 会直接抛 `ExchangeDevice` 错误跑不起来。
证据：`logs/device_id_mapping.txt`；`npu-smi` 侧看到的物理 chip 仍是 8–15（`logs/npu_before.txt` / `logs/npu_after.txt`）。

---

## 3. 逐阶段命令与耗时

容器内时钟为 UTC（= 本地 -8h）。所有 `SAVE` 路径在运行前均 `echo` 确认并在脚本里加了
`case "$SAVE" in */models/out/quantval_*)` 守卫，确保 `quant_dp_inner.sh` 的 `rm -rf "$SAVE"`
只作用于本任务的新目录。

| 阶段 | 命令（容器内） | 起止 (UTC) | 耗时 |
|---|---|---|---|
| 0 准备 | `bash scripts/setup_mslim_inner.sh` | — | 1 min 26 s |
| 1 主干 W4A8 | `MODEL=.../DeepSeek-V4.1-Flash-stage1 SAVE=$ROOT/stage1 DEVICE_IDS="0 1 2 3 4 5 6 7" bash scripts/quant_dp_inner.sh` | 14:48:43 → 15:45:42 | **56 min 59 s** |
| 2 DSpark | `make_dspark_ckpt.py --quant-dir $ROOT/stage1 ... --out-dir $ROOT/dspark` + `add_draft_vocab.py` | 16:05:17 → 16:07:01 | 1 min 44 s |
| 3 Engram int8 | `SRC=.../DeepSeek-V4.1-Flash DST=$ROOT/engram-int8 CHUNK=2097152 bash scripts/run_engram_int8.sh` | 14:49:43 → 15:12:26 | 22 min 43 s（与阶段 1 **并行**，纯 CPU） |
| 4 Vision + qrot | `add_vision_weights.py --target-dir $ROOT/dspark-vision` + `make_qrot_vision_product.py --src ... --dst $ROOT/qrot-vision` | 16:08:22 → 16:08:56 | 34 s |
| 5 mtpq | `mtpq_quantize_draft.py --quantize --src $ROOT/dspark --out $ROOT/dspark-mtpq` + `--verify` | 16:08:22 → 16:11:33 | 3 min 11 s |

**总墙钟：22:48:43 → 00:11:33 (+08) = 1 h 23 min。**

### 3.1 环境负载（影响耗时的关键变量）

量化期间该机有**外部租户**在跑重任务（8 个 Python 进程、未绑核、覆盖全部 640 核）：

```
22:48:40 up 8 days, 2:28, 3 users, load average: 63.79, 64.06, 67.83
 755% 外部租户  <pid>   python
 751% 外部租户  <pid>   python
 744% 外部租户  <pid>   python
 739% 外部租户  <pid>   python   (共 8 进程 ≈ 59 核)
```

证据：`logs/env_load_snapshot.txt`；后续采样 loadavg 63–71。
本任务容器限制在 cpuset 320-639 并以 `nice -n 10` / `ionice -c2 -n7` 运行非量化步骤，
**未与外部租户抢 CPU**（`npu-smi` 全程显示该租户只在 NPU 0–3，本任务只在 NPU 4–7）。

> 阶段 1 的 57 分钟是在上述负载下取得的。A2 报告的 76 分钟是 8 卡干净机器的数字；
> 本机 40 层 DP8 反而更快，与"卡数减半但每卡负载不变"以及该机 640 核的充裕算力相符。
> **该数字不可直接跨机比较，只能作为"同机同负载"的参考。**

---

## 4. 逐阶段复现判定（含证据）

比对方法：① `index.json` 键集合 diff；② 分片名/数量/尺寸；③ **全量**逐张量 `torch.equal`
（非抽样，覆盖全部 185,734 键 / 292.2 GB 实际读取）；④ 逐张量 `max|Δ|` / 相对误差 / 不一致元素占比；
⑤ 分片级 `sha256`。脚本：`$ROOT/compare_all.py`、`compare_all2.py`、`perlayer.py`。

### 4.1 阶段 1 —— 主干 W4A8：**有差异（结构等价、数值等价级，非 bit-exact）**

证据：`logs/cmp_stage1_all.log`、`logs/cmp_stage1_all.json`、`logs/cmp_stage1_families.json`、
`logs/cmp_stage1_perlayer.json`、`logs/ref_stage1_sha256.tsv`

| 检查项 | 新产物 | 真值 `models/out/v41-w4a8-stage1` | 判定 |
|---|---|---|---|
| index 键数 | 185,734 | 185,734 | ✅ 一致 |
| 仅在新增/仅在真值 的键 | 0 / 0 | — | ✅ 键集合完全相同 |
| 标签分布（按 index 键计） | W4A8_DYNAMIC 184,320 / W8A8_DYNAMIC 744 / FLOAT 670 | 同 | ✅ 一致 |
| 形状/dtype 不一致 | 0 | 0 | ✅ 一致 |
| **分片数** | **72** | **80** | ❌ 不一致（见 §5.2） |
| 总体积 | 273 GB | 273 GB | ✅ 一致 |
| `optional/quarot.safetensors` | `8cd564089bd88fb0…` | `8cd564089bd88fb0…` | ✅ **bit-exact** |
| 张量逐位比对 | bit-exact 97,517（52.5%）／有差异 88,217（47.5%） | — | ⚠️ 有差异 |

**差异的族分布**（`compare_all2.py`，全量非抽样）：

| 族 | 张量数 | 有差异 | 元素不一致率 | max\|Δ\| | 备注 |
|---|---|---|---|---|---|
| `ffn.experts.weight`（w1/w2/w3） | 46,080 | 29,292 (63.6%) | 7.82% | 135（int8 LSB，满量程 127） | 路由专家 W4A8 |
| `ffn.experts.weight_scale` | 46,080 | 29,292 (63.6%) | 62.13% | 0.2247（max_rel 17.2） | |
| `ffn.experts.scale_bias` | 46,080 | 29,292 (63.6%) | 88.00% | 482（max_rel 1.7e31 → 多为 ±0 附近） | |
| `attn.weight` | 315 | 179 (56.8%) | 24.75% | 48 | W8A8 注意力 |
| `attn.weight_scale` | 128 | 123 (96.1%) | 89.33% | 0.006378 | |
| `attn_norm.weight` | 40 | 39 (97.5%) | 88.81% | 0.1748 | SmoothQuant 折叠产物 |
| `ffn.shared.*` / `ffn.other.*` / `ffn_norm.weight` / `hc_*`（6 项）/ `attn.other` | 各 40–120 | **0** | 0% | 0 | ✅ bit-exact |
| `embed.weight` / `head.weight` / `misc.weight` | 3 | **0** | 0% | 0 | ✅ bit-exact |
| `attn.weight_offset` / `ffn.experts.weight_offset` | 46,208 | **0** | 0% | 0 | ✅ bit-exact |

**逐层分布**（`cmp_stage1_perlayer.json`）：

```
layer    n      diff    %diff    elem%
L0      4642      12     0.3%    0.000%
L1      4642    2232    48.1%    1.698%
L2–L39  4642–4651  2096–2312  45.2–49.8%   8.2–9.6%
global     3       0     0.0%    0.000%
```

**读数**：差异**不集中于任何层**（L1–L39 一致地在 ~48%），且**完全不触及**不依赖标定激活
的族（embed/head/hc_*/norm 之外的 FLOAT 项、以及全部 `weight_offset`）。这是"标定激活统计
发生微小扰动，导致量化取整在边界处翻转 ±1–2 LSB"的典型指纹，而非算法/结构差异。

### 4.2 阶段 2 —— DSpark draft：**bit-exact**

输入是我的 stage1（与真值 stage1 **不同**），输出却是真值：

| 文件 | 判定（`cmp` / `sha256`） |
|---|---|
| `mtp-00001-of-00004.safetensors` | bit-exact |
| `mtp-00002-of-00004.safetensors` | bit-exact |
| `mtp-00003-of-00004.safetensors` | bit-exact |
| `mtp-00004-of-00004.safetensors` | bit-exact |
| `mtp-vocab-00001-of-00001.safetensors` | bit-exact |

index 键数 **186,960**（= 185,734 主干 + 1,224 MTP + 2 词表），与真值一致。
证据：`logs/stage2_dspark.log`。

### 4.3 阶段 3 —— Engram int8：**bit-exact**

| 文件（206 GB 合计） | sha256 |
|---|---|
| `layers_1_engram_embed.weight.safetensors` | `51d28f161232e3bf…` ✅ 与真值相同 |
| `layers_1_engram_embed.scale.safetensors` | `b0b23e66bbd68a6d…` ✅ |
| `layers_14_engram_embed.weight.safetensors` | `bee6e08838c75d40…` ✅ |
| `layers_14_engram_embed.scale.safetensors` | `9caaea34100a8669…` ✅ |

证据：`logs/new_engram_sha256.tsv` vs `logs/ref_engram_sha256.tsv`、`logs/stage3_engram.log`。

### 4.4 阶段 4 —— Vision + qrot：**bit-exact**

| 产物 | sha256 | 对照 | 判定 |
|---|---|---|---|
| `dspark-vision/vision-00001-of-00001.safetensors`（旋转前） | `370bc89f9bef7a56…` | `models/out/v41-w4a8-dspark-vision/...` | ✅ bit-exact |
| `qrot-vision/vision-00001-of-00001.safetensors`（旋转后） | `db6f1a7c1f0bd24b…` | 真值最终产物 `v41-w4a8-engram-dr-vision-qrot-mtpq/...` | ✅ bit-exact |

`make_qrot_vision_product.py` 报告的 5 个被折叠键（`aligner.w2.weight`、`aligner.w2.bias`、
`image_start`、`image_end`、`image_newline`）`changed=True`，与真值一致。
证据：`logs/stage4_vision.log`。

### 4.5 阶段 5 —— mtpq：**bit-exact**

| 文件 | 判定 |
|---|---|
| `mtpq-00001-of-00004.safetensors` | bit-exact |
| `mtpq-00002-of-00004.safetensors` | bit-exact |
| `mtpq-00003-of-00004.safetensors` | bit-exact |
| `mtpq-00004-of-00004.safetensors` | bit-exact |
| `quant_model_description.json` | bit-exact |
| `mtpq_manifest.json` | 仅 `generated_utc` / `src` / `out` 三个元数据字段不同（预期的运行时间戳与路径） |
| `config.json` | **不同**：真值多了 `quantization_config = {"quant_method":"ascend","model_quant_type":"W4A8_DYNAMIC"}` —— 该字段由 `prepare_runtime_ckpt.py` 注入，不在 `mtpq_quantize_draft.py` 内（见 §6 行动项 A2-3） |

`mtpq --verify` 自校验 PASS：1226 个 mtp 权重（1170 量化 / 56 拷贝）、0 error。
证据：`logs/stage5_mtpq.log`。

---

## 5. 差异归因

### 5.1 已排除的变量

| 候选原因 | 结论 | 证据 |
|---|---|---|
| **源码树脏** | ❌ 排除。主补丁与配方均与交付包/真值一致；`git status` 仅 2 条无关未跟踪项 | §2 指纹；补丁正文比对（下） |
| **工具版本不同** | ❌ 排除。同一镜像 digest，本机与真值同源 | §2 |
| **标定数据不同** | ❌ 排除。`mix_calib.jsonl` sha256 与真值同源树逐字节一致 | §2 |
| **配方不同** | ❌ 排除。yaml sha256 `d3d9bdc6…` 与交付包内同名文件**逐字节相同** | §2 |
| **补丁不同** | ❌ 排除（有 1 处形式差异，见下） | 见 §5.1.1 |
| **run-to-run 随机抖动** | ❌ 排除。同配置下确定性过程可复现（阶段 2–5 在**不同主干输入**上仍 bit-exact） | §4.2–4.5 |
| **DP 宽度不同** | ✅ **确认（对照实验证明）**。同输入仅把 rank 数 8→4 即产生 40.6% 张量差异，族别与幅度同"DP8 vs 真值 DP16"一致 | §5.2 证据 3、`logs/cmp_dp8_vs_dp4*.json` |

#### 5.1.1 补丁的 sha256 差异（唯一的形式性差异，不影响内容）

- 本机 `patches/msmodelslim_v41_w4a8.patch` sha256 `15f8368ea7813dbb…`（1,687 行）
- 交付包 `patches/msmodelslim-dsv41-w4a8.patch` sha256 `96e000cee0a9ae93…`（1,680 行）
- 去掉本机补丁顶部 7 行 `#` 注释头后，两者 `diff` **完全为空**；双方均含 9 个 `diff --git` 文件块。

⇒ 纯注释头差异，**不是代码差异**。（A2 报告 §1.3 列的正是包内那份 `96e000ce…`。）

### 5.2 真实原因：DP 宽度不同（真值 DP16 vs 本次 DP8）—— **已用对照实验证明**

三点证据：

1. **分片数 72 vs 80**。`quant_dp_inner.sh` 的 saver 是 `part_file_size: 4 GiB`，但分片是按
   DP rank 汇总后落盘的：DP16 产 80 分片、DP8 产 72 分片，**总字节数相同（273 GB）**。
   分片数与键集合无关（键集合完全一致），是纯粹的**打包布局**差异，运行时由 index 消费，
   不影响推理正确性。
2. **只有依赖标定激活的族发生差异**。差异 100% 落在 AWQ-SSZ / SmoothQuant 参与的族
   （`ffn.experts.*`、`attn.weight`、`attn.weight_scale`、`attn_norm.weight`），
   而所有与标定无关的族（`embed`/`head`/`hc_*`/`ffn_norm`/`ffn.shared`/全部 `weight_offset`）
   **逐位相同**，全局旋转矩阵 `quarot.safetensors` 也逐位相同。

   在 DP 下，标定数据按 rank 切分，各 rank 的 token 数不同，激活统计的归约顺序随之改变；
   DP8 与 DP16 的分片不同 ⇒ 统计量有 ~1e-4 量级的扰动 ⇒ int8/int4 取整在边界处翻转。
   这与观察到的"max\|Δ\| 约为几个 LSB、元素不一致率 8–10%、且逐层一致"完全吻合。

3. **收官对照实验（同输入、只变 DP 宽度）**。用官方基座现造一个 6 层子模型
   `$ROOT/ab_model6`（`make_full_model.py --layers 6 --mtp 0 --engram off --vision drop`，
   14,018 张量 / 8 分片），**同一份模型、同一份配方、同一份标定数据、同一份代码、同一台机器**，
   只把 rank 数从 8 改成 4，各跑一次量化：

   | 对照 | rank 数 | 键数 | bit-exact | 有差异 | 形状/dtype 不一致 | 耗时 |
   |---|---|---|---|---|---|---|
   | `dp_ab/dp8` | 8 | 27,864 | 16,541（59.4%） | 11,323（40.6%） | 0 | 16:17:29→16:32:23 (15 min) |
   | `dp_ab/dp4` | 4 | 27,864 | — | — | — | 16:32:23→16:51:34 (19 min) |

   **DP8 与 DP4 的产物同样不一致（40.6% 张量有差异），且差异族与幅度同"DP8 vs 真值 DP16"高度一致：**

   | 族 | DP8-vs-DP4（有差异 / 元素不一致率 / max&#124;Δ&#124;） | DP8-vs-DP16（40 层全量） |
   |---|---|---|
   | `ffn.experts.weight` | 54.4% / 5.67% / 118 LSB | 63.6% / 7.82% / 135 LSB |
   | `ffn.experts.weight_scale` | 54.4% / 44.8% / 0.0466 | 63.6% / 62.1% / 0.2247 |
   | `ffn.experts.scale_bias` | 54.4% / 65.3% / 82.9 | 63.6% / 88.0% / 482 |
   | `attn.weight` | 49.0% / 11.9% / 35 | 56.8% / 24.8% / 48 |
   | `attn.weight_scale` | 73.7% / 45.9% / 0.00137 | 96.1% / 89.3% / 0.00638 |
   | `attn_norm.weight` | 83.3% / 49.3% / 0.0247 | 97.5% / 88.8% / 0.1748 |
   | `embed.weight` / `head.weight` / `hc_*` / `ffn.shared.*` / 全部 `weight_offset` | **0%（逐位相同）** | **0%（逐位相同）** |

   ⇒ **同一份输入、仅改变 DP 宽度，就足以产生与"真值 DP16 vs 本次 DP8"同量级、同族别的差异。
   §5.2 的归因由此从推断升级为直接实验结论。**

   附：同一个 6 层子模型用 DP8 跑出的产物与真值 `v41-w4a8-stage1` 同 6 层相比，
   27,864 键中 16,505 bit-exact / 11,359 有差异 = 40.8%，与 DP8-vs-DP4 的 40.6% 几乎相同，
   进一步说明"与真值的差异"与"跨 DP 宽度的差异"是同一现象。

   > 失败尝试记录：最初想用现成的 `DeepSeek-V4.1-Flash-partial7` 做 A/B，被 msmodelslim 的
   > 路径白名单拦下（`SecurityError Code 204: The directory /path/to/models/staging
   > doesn't exist.`，见 `logs/dp_ab_dp8.log`）——该 7 层历史目录自身指向一个不存在的
   > `models/staging`。改用自建 `ab_model6` 后成功。脚本 `$ROOT/ab6_run.sh`、日志
   > `logs/dp_ab6.log`、比对结果 `logs/cmp_dp8_vs_dp4.json` 与 `logs/cmp_dp8_vs_dp4_families.json`。

### 5.3 差异幅度是否影响质量

| 量级 | 观测值 | 解读 |
|---|---|---|
| int8 权重最大偏差 | 135 LSB（满量程 127） | 单点极端值，属取整边界翻转 |
| 元素不一致率（专家权重） | 7.8% | 其中绝大多数为 ±1 LSB |
| `weight_scale` max_rel | 17.2（但 max\|Δ\|=2.2e-4） | 分母接近 0 导致的相对误差放大 |

考虑到 A3 侧已实测 **W4A8 本身相对全精度无损**（GSM8K 200 题 8-shot 97.5% vs 官方报告 93.0），
而本次差异比 W4A8 量化本身的误差小 1–2 个数量级，**判定为"数值等价"**：
不影响推理可用性，但不满足逐位复现（bit-exact）要求。

---

## 6. 对 A2 交付包的影响与建议

### 6.1 直接回答"A2 拿到脚本后能不能复现同样的权重"

**不能逐位复现，但能在数值等价意义上复现，且链路本身可靠。**

- A2 用 8 卡（= DP8）跑，与产生我们当前真值的 DP16 不同 ⇒ 阶段 1 必然产生
  另一个"数值等价副本"，**不会**得到与 `models/out/v41-w4a8-stage1` 相同的 sha256。
- 但阶段 2–5 的脚本是**完全确定性的**：在主干输入不同的前提下，DSpark / Engram int8 /
  Vision+qrot / mtpq **四个阶段全部逐字节复现**了真值。这说明链路里除阶段 1 之外的每一步
  都可放心作为"可复现交付"。
- 结论：**A2 复现的是一份"等价权重"，不是"同一份文件"。任何以 sha256 作为验收判据的
  流程都会误判为失败 —— 这一点必须写进交付包验收章节。**

### 6.2 建议补进包的项

| # | 内容 | 依据 |
|---|---|---|
| A2-1 | **验收判据改为结构 + 容差**：键集合相同、标签分布相同、形状/dtype 相同、`weight_offset` 与 FLOAT 族 bit-exact、量化权重按族给出 max\|Δ\| 上限；**不要**拿分片 sha256 判等 | §4.1 |
| A2-2 | **明确记录 DP 宽度**：包内固定写死 `DEVICE_IDS` 的语义，并在文档注明"DP 宽度影响量化结果，不可比 sha256" | §5.2 |
| A2-3 | **把 `prepare_runtime_ckpt.py` 收进链路**：`quant_dp_inner.sh` 只跑 msmodelslim，产出的 `config.json` **没有** `quantization_config`（本次实测 `None`），而真值是 `{"quant_method":"ascend","model_quant_type":"W4A8_DYNAMIC"}`。交付包的 quant 脚本应串上这一步 | §4.5、`logs/stage1_quant.log` |
| A2-4 | **修正设备号写法**：包内 `docker/enter.sh` 的 `ARTV`（容器外物理号 8–15）与 `--device_id`（容器内 0–7）是两套编号；文档若照抄 `DEVICE_IDS="8 9 … 15"` 会 *`ExchangeDevice`* 失败。建议在 `quant_dp_inner.sh` 里加一句容器内重编号说明或直接默认 `0 1 2 3 4 5 6 7` | §2.1 |
| A2-5 | **补一份"期望指纹"文件**：把 `index.json` 键数、标签分布、各族张量数、`quarot.safetensors` sha256、各阶段分片 sha256（阶段 2–5 可 bit-exact 比对）冻结成 `expected/`，供 A2 离线自检 | §4.2–4.5 |
| A2-6 | 说明 `partial7` 历史模型目录不可用（缺 `models/staging`，会被路径白名单拦截），避免 A2 误用 | §5.2 |

### 6.3 不需要改的部分

- `make_dspark_ckpt.py` / `add_draft_vocab.py` / `engram_convert_int8.py` /
  `add_vision_weights.py` / `make_qrot_vision_product.py` / `mtpq_quantize_draft.py`
  **六个脚本本次全部 bit-exact 复现**，无需改动。
- `mtpq_quantize_draft.py --verify` 自校验（1226 权重 / 0 error）可用作交付包内建门禁。

---

## 7. 未完成部分与后续

1. ~~**DP 宽度的收官 A/B**~~ **已完成**：`ab_model6`（6 层子模型）DP8 vs DP4 对照实验跑通，
   结果 16,541 bit-exact / 11,323 有差异（40.6%），直接证明"DP 宽度改变量化结果"。
   详见 §5.2 证据 3。
2. **未做端到端精度回归**：本任务范围是权重复现，未起服务跑 GSM8K / 视觉验收。
   A3 侧已有结论（GSM8K 97.5%、视觉 WIP 43.5%），本次差异幅度远小于量化本身误差，
   预计不影响；但如要以"等价权重"入库，建议补一次 GSM8K 200 题。
3. **未复现 `v41-w4a8-engram-dr` / `-vision` 中间目录的完整组装**（`engram_dr_build.py`
   与 `mtpq_make_vision_dir.py` 的整目录装配）。已复现的是其中的权重级产物
   （engram int8、vision、qrot vision、mtpq），目录级软链布局未逐一比对。

---

## 8. 证据清单

根目录 `R=/path/to/models/out/quantval_20260915_2235`

| 文件 | 内容 |
|---|---|
| `$R/logs/env_fingerprint_20260915_223729.txt` | 主机/镜像/源码/配方/标定 指纹 |
| `$R/logs/device_id_mapping.txt` | 容器内设备号重编号证据 |
| `$R/logs/stage0_setup.log` | venv 建立与 CLI 可用性 |
| `$R/logs/stage1_quant.log` | 阶段 1 全量日志（5.0 MB） |
| `$R/logs/stage2_dspark.log` `stage3_engram.log` `stage4_vision.log` `stage5_mtpq.log` | 阶段 2–5 日志 |
| `$R/logs/cmp_stage1_all.log` / `.json` | 阶段 1 全量逐张量比对（185,734 键 / 292.2 GB） |
| `$R/logs/cmp_stage1_families.json` | 按族聚合的差异幅度 |
| `$R/logs/cmp_stage1_perlayer.json` | 逐层差异分布 |
| `$R/logs/ref_stage1_sha256.tsv` `ref_dspark_sha256.tsv` `ref_mtpq_shards_sha256.tsv` `ref_engram_sha256.tsv` `ref_vision_sha256.tsv` | 真值侧哈希 |
| `$R/logs/new_engram_sha256.tsv` | 新产物 engram 哈希 |
| `$R/logs/env_load_snapshot.txt` | 外部租户负载快照 |
| `$R/logs/dp_ab_dp8.log` `dp_ab6.log` | DP 宽度 A/B（partial7 失败记录 + ab_model6 进行中） |
| `$R/logs/cmp_dp8_vs_dp4.json` / `cmp_dp8_vs_dp4_families.json` | **DP 宽度 A/B 收官比对结果** |
| `$R/logs/npu_before.txt` / `npu_after.txt` | 运行前后 `npu-smi` 证据（chip 8–15 占用与释放） |
| `$R/stage1_run.sh` `stage2_run.sh` `stage3_run.sh` `stage4_run.sh` `stage5_run.sh` `ab6_run.sh` | 带 `quantval_*` 路径守卫的复现脚本 |
| `$R/compare_all.py` `compare_all2.py` `perlayer.py` `summarize.py` | 比对工具 |

产物目录：`$R/stage1`（273 GB）、`$R/dspark`、`$R/engram-int8`（206 GB）、
`$R/dspark-vision`、`$R/qrot-vision`、`$R/dspark-mtpq`、`$R/ab_model6`。
**未覆盖任何既有产物**；所有写入均在 `quantval_20260915_2235/` 之下。

---

## 9. 资源占用与释放证据

### 9.1 chip 隔离（全程只用 chip 8–15）

- 容器以 `PRESET=back8 NAME=本任务量化容器` 启动：`cpuset=320-639`、`mems=4-7`、
  `ASCEND_RT_VISIBLE_DEVICES=8,9,10,11,12,13,14,15`（`docker inspect` 实测）。
- 8 个量化 worker 进程全部登记在物理 chip 8–15（`npu-smi` 输出中对应 "NPU 4–7 die 0/1"）；
  **chip 0–7（NPU 0–3）上没有任何本任务进程** —— 那里只有该外部租户的 8 个 python 进程。
- 证据：`$R/logs/npu_before.txt`（运行中）、`$R/logs/env_load_snapshot.txt`。

### 9.2 停容器与释放

量化与 A/B 全部跑完后执行 `sudo -n docker stop -t 15 本任务量化容器`，随后 `npu-smi` 证据：

```
=== teardown timestamp ===
2026-09-16T00:54:48+08:00

=== docker ps after stop ===
他人容器 Up 6 days
他人容器   Up 6 days
他人容器    Up 6 days
   ← 本任务容器已停止；其他租户容器未被触碰

=== npu-smi: NPU 4–7（= chip 8–15）进程段 ===
No running processes found in NPU 4
No running processes found in NPU 5
No running processes found in NPU 6
No running processes found in NPU 7
```

**chip 8–15 已释放。** 完整输出见 `$R/logs/npu_after.txt`。

### 9.3 磁盘占用

`du -sh $R` = **608 GB**（阶段 1 273 GB + engram-int8 206 GB + dp_ab 89 GB + dspark 30 GB +
dspark-mtpq 11 GB + 其余 ~1 GB）。`/home` 剩余 8.7 TB，占用约 7%，**未清理**以保留复现证据；
若需腾空间，`$R/dp_ab`（89 GB，仅 A/B 对照）可优先删除，不影响报告结论的可追溯性。
