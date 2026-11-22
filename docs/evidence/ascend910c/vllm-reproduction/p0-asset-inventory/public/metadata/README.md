---
license: Apache License 2.0
base_model: deepseek-ai/DeepSeek-V4.1-Flash
base_model_relation: quantized
tasks:
  - image-text-to-text
frameworks:
  - PyTorch
  - vLLM-Ascend
language:
  - zh
  - en
domain:
  - multi-modal
metrics:
  - accuracy
tags:
  - Ascend
  - "910"
  - W4A8
  - 量化
  - MoE
  - DeepSeek-V4.1
  - vLLM-Ascend
---

# DeepSeek-V4.1-Flash W4A8（Ascend 910）

基于 [DeepSeek-V4.1-Flash](https://www.modelscope.cn/models/deepseek-ai/DeepSeek-V4.1-Flash)
的 **Ascend W4A8 量化版本**，面向 **单机 8 chip**部署。量化后模型可整体常驻 HBM，
支持最长 **1M** 上下文，并可开启 DSpark 投机解码。

> **本卡片 2026-10-14 更新**：修正第 8 节「修改版 vLLM 暂未发布」的过时表述
> （**已发布**，见上文「起服前必读」）；**交付默认改为 `BAT_TOKENS=2048` + KV32 重排
> ⇒ KV 容量 4,010,585 tokens**（原 2,987,727）；补充 A3 单机 8+8 PD 分离 + CED 形态
> 与各镜像包 Release 入口。权重本身**未变**，仍是 2026-09-16 冻结的同一份量化产物。

---

## 性能速览（先看这个）

> **口径**：**单台 A3 = 8×910C / 8 chip**、真权重、全补丁、**交付默认配置**
> （`--max-num-batched-tokens 2048` + KV32 slot 重排 + `--gpu-memory-utilization 0.92`）。
> **`tok/s = A × 1000 ÷ ms/step`**（`A` = 接受长度）。

### 单流（1 条请求独占）

| 场景 | ms/step | A | 单流 tok/s |
|---|---:|---:|---:|
| 1024 prompt / 256 out，**DSpark 草稿入图**（低并发推荐） | **23.9 – 24.9** | 2.40 – 2.74 | **100.7 – 109.8** |
| 128K 长上下文，单流独占 | **30.2 – 31.6**（最好 26.9） | 2.75 | **85 – 90** |

### 多流（并发聚合）

| 并发 | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---:|---:|---:|---:|---:|---:|---:|
| 单流 tok/s | 90.3 | 89.2 | 80.0 | 59.3 | 42.5 | 31.3 | 20.2 |
| **聚合 tok/s** | 87.1 | 151.5 | 237.7 | 324.4 | 432.6 | 583.9 | **719.5** |

> 多流口径：每条 prompt **精确 1024 token**、输出 256、并发上限 64 + 前缀缓存、
> 每档跑同一批 64 条、2 rep 取中位（**与上表单流不是同一个开关组合**）。
> 单流效率随并发下降（并发 8 时 65.6%、64 时 22.3%）—— **聚合上界是算力，不是槽位数**。

### 预期 KV cache 容量（HBM 内常驻）

| 形态 | 容量 |
|---|---:|
| **A3 单实例 8 chip · 交付默认** | **4,010,585 tokens**（≈ 1M 上下文 × 3.82 并发） |
| 旧口径（`--max-num-batched-tokens 8192`，不重排） | 2,987,727 tokens |

> 4.01M 靠 **`--max-num-batched-tokens 2048` + KV32 slot 重排**两条**成对**拿到；
> 只降这个值会让 KV 池越过 32 位块号边界、**长文静默读错** —— 机制与代价见 §3.1，
> 逐档明细见 §4.1。

---

## ⚠️ 起服前必读

### 1. 必须先重组 Engram 权重

受平台单文件 50 GB 上限约束，Engram 的两个大权重已切成 6 片存放。**直接起服会失败**，
必须先执行重组脚本：

```bash
cd engram_int8
bash reassemble_engram_weights.sh
```

脚本会：① 逐片校验 sha256 → ② 按序拼接还原 → ③ 校验还原结果与原始 sha256 一致
（不一致会报错退出，不会留下坏文件）。校验通过后分片默认保留，加 `--delete-parts` 可删除。

### 2. 需要专门修改版的 vLLM / vLLM-Ascend（**已发布**）

本模型**不能**直接用官方 vLLM-Ascend 加载，依赖以下修改。修改版运行时与配套脚本
已开源，见 **[chiro2001/deepseek-v4.1-flash-ascend910B](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B)**：

| 组件 | 修改内容 |
|---|---|
| vllm-ascend | 替换 `models/deepseek_v41/` 下的 Engram 运行时代码（`engram_hbm.py`、`engram_gate.py`、`engram_hash.py`），实现 Engram 表 host 常驻与 local-owner 路径 |
| vllm-ascend（v8 新增） | **Engram device-index**：表仍常驻 host DRAM，但改由**设备算子直接索引**（`aclrtHostRegister` + `MAPPED` 映射），整条 host 路径（d2h/分片/all_gather/all_to_all/broadcast/h2d）消失、查表进主图。需 AIC/AIV 能直读 host 映射内存；脚本默认 `ENGRAM_DEVICE_INDEX=auto`，**探测不通过会自动回退**到 host 路径（功能不变、性能按旧路径） |
| vllm core | `admission_gate` 补丁（预填充隔离，防止 decode 被 prefill 饿死） |

基础镜像：`quay.nju.edu.cn/ascend/vllm-ascend:deepseek-v4.1-flash-a3`
（digest `sha256:2c906b38ad3cc9ed9badfe3d09451d194fa09a07e5c6d62a66b111731e626060`）。
**仅使用该基础镜像不足以运行本模型**，需叠加上述修改。

仓库里包含：12 个补丁（9 个性能 + 1 个调度 + 2 个量化适配，带 git 历史、可 `git am`；两种形态——整文件与 patch 系列——已机器验证逐字节等价）、
A2/A3 一键起服脚本、自检与验收工具、并发压测与出图脚本，以及每项结论的实验记录。
部署按仓库 `README.md` 走即可，第 3 节的命令是其中的精简版。

---

## 1. 权重构成

| 部件 | 文件 | 体积 | 精度 |
|---|---|---|---|
| 主干（backbone） | `quant_model_weights-00001..00072.safetensors` | 273 GiB | W4A8_DYNAMIC |
| Engram | `engram_int8/`（4 个逻辑文件，其中 2 个分片存放） | 206 GiB | int8 |
| **DSpark draft（mtpq）** | `mtpq-0000{1..4}.safetensors` + `mtpq_manifest.json` | **9.9 GiB** | **见 §1.1** |
| Vision（含 QuaRot） | `vision-00001-of-00001.safetensors` | 926 MiB | bf16 / W8A8 |
| 旋转矩阵 | `optional/quarot.safetensors` | 101 MiB | — |
| 索引与描述 | `*.json` + `engram_extra.safetensors` | 635 MiB | — |
| **合计** | **87 项 / 72 分片** | **约 490 GiB** | |

主干索引键数 **190,728**（backbone 185,734 / mtpq 4,718 / vision 266 / engram_extra 6 /
engram_int8 4），`quant_model_description.json` 共 **191,900** 键。

### 1.1 DSpark draft 与 mtpq 是什么

**mtpq = MTP 量化版（MTP quantized）**，是 DSpark 推测解码所用 draft 模型的权重。

模型内置 **3 层 MTP（Multi-Token Prediction，多 token 预测）**，即 `mtp.0` / `mtp.1`
/ `mtp.2`（`config.json` 的 `num_nextn_predict_layers=3`，其 target 层为主干
第 37/38/39 层，见 `dspark_target_layer_ids`）。
它作为**投机解码**（speculative decoding）的 draft 模型使用：主模型每步生成 1 个
token，draft 并行预测后续多个候选 token 再交主模型校验，从而在输出质量不变的前提下
提升解码吞吐。该 draft 由 **DSpark** 方案驱动，预测深度由运行时的
`num_speculative_tokens` 控制。

#### draft 权重的三种形态（避免混淆，请对照阅读）

| 形态 | 精度 | 体积 | 说明 |
|---|---|---|---|
| ① 官方原始 | 专家 **FP4**（int8 打包 + E8M0 分块 scale）、注意力/共享专家/`main_proj` **FP8**、norm BF16 | **7.39 GiB** | 基座模型里的存储格式，共 2,401 个张量 |
| ② 反量化中间态 | **BF16** | **28.97 GiB** | 上表 ① 反量化而来（含 draft 词表分片） |
| ③ **本次发布（mtpq）** | 专家 **W4A8**、注意力/共享专家 **W8A8**、其余 BF16/F32 | **9.90 GiB** | 由 ② 量化，运行时实际加载的就是它 |

**为什么不是直接用 ①？** 官方 ① 使用的 FP4/FP8 分块量化格式不是 Ascend 的量化格式。
本模型的运行时通过 Ascend ModelSlim 量化路径加载 draft（按 `quant_model_description.json`
里的 `mtp.*` 条目查表），因此需要 Ascend W4A8/W8A8 格式的权重。

**mtpq 的价值**：若 draft 以 BF16（形态 ②）常驻，需 28.97 GiB；改用 mtpq（形态 ③）
后为 9.90 GiB，**减少 19.07 GiB**，在 8 chip 上相当于每 rank 回收约 **2.38 GiB**，
可直接转为 KV cache 容量。（注意：mtpq 的 9.90 GiB 大于官方 ① 的 7.39 GiB，
因为两者是**不同的量化方案**，不可直接按体积比较。）

#### mtpq 的量化明细

对形态 ② 的 draft 做了一次**离线量化**（数据无关，不占用标定数据，与主干量化相互独立）：

| 张量类别 | 精度 | 张量数 |
|---|---|---|
| 路由专家 `ffn.experts.*.w1/w2/w3` | W4A8_DYNAMIC | 1,152 |
| 注意力 `attn.wq_a/wq_b/wkv`、共享专家 `ffn.shared_experts.*` | W8A8_DYNAMIC | 18 |
| `main_proj`、`wo_a/wo_b`、各类 norm、`markov_head` / `confidence_head`、词表 | 保持 BF16 / F32 | 56 |

量化前 1,226 个张量；量化时每个线性层会展开出权重/scale 等附属张量，
因此最终在索引里占 **4,718** 个条目。

`mtpq_manifest.json` 记录了逐张量的量化前后字节账与分片清单，供核对。

## 1.2 各部分量化方案总览

以下为全仓库 **191,900** 个量化条目的实际分布（取自
`quant_model_description.json`，"张量数"按 `*.weight` 计数）：

| 部件 | 子模块 | 量化方案 |
|---|---|---|
| **主干** | 路由专家 `ffn.experts.*.w1/w2/w3` | **W4A8_DYNAMIC**（int4 per-channel SSZ + int8 per-token） |
| | 注意力 `attn.wq_a/wq_b/wkv` | **W8A8_DYNAMIC** |
| | 共享专家 `ffn.shared_experts.*` | **W8A8_DYNAMIC** |
| | `attn.indexer.wq_b` | **W8A8_DYNAMIC** |
| | 其余（`ffn.gate`、`wo_a/wo_b`、`compressor.*`、`indexer.wk/weights_proj`、各类 norm、`hc_*`、`embed`、`head`、`attn.other`） | **FLOAT**（保持 BF16 / F32） |
| **DSpark draft** | 路由专家 `mtp.*.ffn.experts.*` | **W4A8_DYNAMIC** |
| | 注意力 `mtp.*.attn.wq_a/wq_b/wkv`、共享专家 | **W8A8_DYNAMIC** |
| | 其余（`main_proj`、`wo_a/wo_b`、norm、`markov_head`、`confidence_head`、词表） | **FLOAT**（BF16 / F32） |
| **Engram** | `engram_int8/` 全部 | **int8**（per 32 通道 + FP32 scale） |
| **Vision** | `vision.*`（含 aligner） | **FLOAT**（BF16，含 QuaRot 旋转后权重） |
| **旋转矩阵** | `optional/quarot.safetensors` | FLOAT（F32） |

主干内部的精确张量计数：

| 模块 | W4A8_DYNAMIC | W8A8_DYNAMIC | FLOAT |
|---|---|---|---|
| 路由专家 `ffn.experts.*` | 46,080 | — | — |
| 注意力 `attn.wq_a/wq_b/wkv` | — | 120 | — |
| 共享专家 `ffn.shared_experts.*` | — | 120 | — |
| `attn.indexer.wq_b` | — | 8 | — |
| `attn.indexer.wk/weights_proj` 等 | — | — | 16 |
| `attn.wo_a/wo_b` | — | — | 80 |
| `attn.compressor.*` | — | — | 11 |
| `ffn.gate` | — | — | 40 |
| 各类 norm | — | — | 81 |
| `embed` / `head` | — | — | 2 |
| 注意力其他（`attn_sink` 等） | — | — | 80 |
| **主干合计** | **46,080** | **248** | **310** |

> 上表按**模型参数张量**（`*.weight`）计数。`quant_model_description.json` 共
> **191,900** 个条目，另含每个量化层的 scale / offset 附属条目、骨架与偏置参数
> （如 `ffn.gate.bias`、`hc_*`、`attn_sink`）及配置项，故总量大于上表之和。
>
> 若按**索引键**口径（`quant_model_weights.safetensors.index.json`），主干占
> **185,734** 个键，其标签分布为 `W4A8_DYNAMIC 184,320` / `W8A8_DYNAMIC 744` /
> `FLOAT 670`。

## 2. 下载

```bash
pip install modelscope

# ① 全量下载：量化权重 + 发布材料（约 490 GiB）
modelscope download --model chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend \
  --local_dir /models/DeepSeek-V4.1-Flash-w4a8-Ascend

# ② 只下载发布材料 release/（不到 1 MiB）
#    已有官方基座权重、想自行复现量化流程，或先查阅配方与补丁时使用
modelscope download --model chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend \
  --local_dir /models/dsv41-release \
  --include 'release/*'
```

`release/` 内含补丁、量化配方、标定数据、复现脚本与验收报告，单独下载仅不到 1 MiB，
可先查阅确认后再决定是否拉取 490 GiB 权重。各项内容见第 9 节。

下载后先执行文首的 Engram 重组脚本。重组完成后的目录应为：

```
engram_int8/
├── layers_1_engram_embed.weight.safetensors     ← 98,305,579,120 B
├── layers_1_engram_embed.scale.safetensors      ←  12,288,197,488 B
├── layers_14_engram_embed.weight.safetensors    ← 98,308,270,704 B
└── layers_14_engram_embed.scale.safetensors     ←  12,288,533,936 B
```

## 3. 起服

需配合修改版 vLLM / vLLM-Ascend（见文首说明，仓库地址
[chiro2001/deepseek-v4.1-flash-ascend910B](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B)）。

**推荐用仓库里的一键脚本起服**（自动处理补丁烘焙、模型软链挂载、静态内核缓存、
选卡校验与 CPU 绑核）：

```bash
# A3（910C）：先看哪些卡空着，再指定自己那 8 张
bash tools/list_chips.sh
DEVS="8 9 10 11 12 13 14 15" \
  MODEL=/path/to/DeepSeek-V4.1-Flash-w4a8-Ascend \
  bash scripts/serve_a3.sh

# A2（910B3）
bash scripts/build_image.sh
MODEL=/path/to/DeepSeek-V4.1-Flash-w4a8-Ascend bash scripts/serve_a2.sh

# 低并发（1–2 条流）想更快：加 DRAFT_GRAPH=1（单流 +12 ~ +22%）
# ⚠️ 并发 ≥ 4 时反而更慢（总吞吐 −5 ~ −10%）⇒ 按场景选，见 §4.1 的 C 表
DRAFT_GRAPH=1 PORT=8077 SERVED_NAME=deepseek-v4-flash \
  MODEL=/path/to/DeepSeek-V4.1-Flash-w4a8-Ascend bash scripts/serve_a2.sh
```

> 端口与模型名都可自定义：`PORT=<端口> SERVED_NAME=<模型名>`（API 请求 body 里的
> `"model"` 字段要填 `SERVED_NAME` 的值）。默认分别是 `8100`（A2）/`8000`（A3）与
> `deepseek-v41`。

**部署形态与镜像包**：上面是单实例 TP8 的精简命令。仓库里还提供多种形态与
**已构建好的镜像层补丁包**，无需自己烘焙补丁：

| 形态 | 硬件 | 镜像包 |
|---|---|---|
| A3 单机 **8+8 PD 分离 + CED**（长上下文） | 1 台 A3 的 16 个 device 全用 | [Release `a3-ced-pd-v3`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/releases/tag/a3-ced-pd-v3) |
| A3 单实例 TP8 | 8 个 device（= 4 块卡） | [Release `a3-tp8-v1`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/releases/tag/a3-tp8-v1) |
| A2 单实例 TP8 | 1 台 A2（8×910B3） | 见仓库 `scripts/serve_a2.sh` |

⚠️ **验收边界**：2026-10-13 起对上述多形态做过一轮复测，**尚未全部验收** ——
`A3 TP8 + DCP8` 的严格精度未达标（GSM8K 99/100），`CED P8+D8` 的设备回归未完成。
因此交付口径以仓库 [`README.md`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/blob/main/README.md)
的 §1.2 与 [`experiments/delivery_matrix/STATUS.md`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/blob/main/experiments/delivery_matrix/STATUS.md)
为准；**不要引用未标注「已验收」的数字**。

服务 READY 后必查四项（静态内核未降级 / KV 容量 / 起服口径 / Engram 快路径）：

```bash
PORT=8020 NAME=<容器名> SLOG=results/<run_id>/serve.log bash tools/attach_test.sh
```

**手动起服**（等价的最小命令）：

```bash
vllm serve /models/DeepSeek-V4.1-Flash-w4a8-Ascend \
  --served-model-name deepseek-v41 \
  --tensor-parallel-size 8 \
  --enable-expert-parallel \
  --max-model-len 1048576 \
  --max-num-batched-tokens 2048 \
  --block-size 128 \
  --gpu-memory-utilization 0.92 \
  --additional-config '{"enable_engram":true,"enable_cpu_binding":true,"ascend_compilation_config":{"enable_npugraph_ex":true,"enable_static_kernel":true},"engram_storage":"int8"}' \
  --tokenizer-mode deepseek_v41 \
  --reasoning-parser deepseek_v41 \
  --tool-call-parser deepseek_v41 \
  --enable-auto-tool-choice \
  --enable-prefix-caching \
  --default-chat-template-kwargs '{"enable_thinking":false}'
```

> 注意 `--tokenizer-mode` 用 **`deepseek_v41`**（不是 `deepseek_v4`）：
> 前者才能正确处理 agent 工具调用的 chat template；旧版 `deepseek_v4` 的
> DSML 标签形态不同、默认 thinking 开关也不同。
>
> 功能开关（环境变量）：`ENGRAM=1 ENGRAM_STORAGE=int8 VISION=1 SPEC=1`、`KV_DTYPE=bfloat16`、
> `ENGRAM_WKV_TP=1`（默认开：engram gate 的 `wkv` 投影按输出维分片，KV 容量 +5.9%）。
>
> ⚠️ 上面这段是**精简**命令：`--max-num-batched-tokens 2048` 必须**配 KV32 slot 重排**
> （覆盖 `vllm_ascend/core/deepseek_v41.py`）才能起得来 —— 只降这个值会让池越过
> 32 位块号边界。**推荐直接用仓库的一键脚本**（已内置重排挂载 + 上限夹取），
> 手动起服请按仓库 `README.md` §4 挂上 `patches/files/deepseek_v41.repack.py`。

### 3.1 `--max-num-batched-tokens`：容量杠杆 + 一个已修复的长上下文坑（重要）

**一键脚本 `scripts/serve_a3.sh` 的交付默认是 `--max-num-batched-tokens 2048`**
（= `BAT_TOKENS=2048`），并且**同时**开启 KV32 slot 重排。两者**必须成对**，见下。

#### 它是什么

`--max-num-batched-tokens` = chunked prefill 的**分块上限**，所以它同时决定
**activation 峰值** ⇒ 是个纯粹的**容量杠杆**（不影响输出质量；§5 的精度验收在
两档下都通过）。

| | `BAT=8192`（旧默认） | **`BAT=2048`（2026-10-14 起默认）** |
|---|---:|---:|
| activation 峰值 | 3.21 GiB | **0.79 GiB** |
| KV 容量（8×910C、`GPU_UTIL=0.92`） | 2,987,727 tok | **4,010,585 tok（+34.2%）** |
| prefill（8K prompt） | ~7.2K tok/s | 6,478 tok/s（−11%） |

#### ⚠️ 为什么必须与「KV32 slot 重排」成对

只降 `BAT` 会让长上下文**静默算错**（HTTP 200 + 空回复）—— 但原因**不是**分块粒度，
而是**容量增益把 KV 池推过了 32 位块号边界**：

* 降 BAT 后自动 profiling 多给约 9,000 块 KV ⇒ 池 33,994 块，越过该几何的
  32 位安全上界（块号 × 页步长越过 2³²）⇒ **块号回绕 ⇒ 读到错数据**；
* 实测：池越界 2,342 块的那一档，长文探针 **12/12 FAIL**；
* 修法 = **slot 重排**（四槽页步长全 131,072 ⇒ 池 stride 540,928 → 524,288、
  块上限 29,076 → **32,768（+12.7%）**）+ 载荷自带的**上限夹取** `[V41-KV32-CAP]`。

决定性对照：**同一个 `BAT=2048`、chunk 数完全相同**，只把越界从 2,342 块改成 0 ⇒
**12/12 FAIL → 24/24 PASS**。⇒ 根因是越界，不是分块。

> 本卡片早期版本把该退化归因为「chunked prefill 每刀约 2% 偏离」，
> 那条机制**已作废**（见配套仓库 `docs/KV32-OVERFLOW-DOSE-RESPONSE-20261006.md` §6）。

#### 怎么用

* 用仓库的一键脚本起服即可（默认已同时开启 2048 与重排）；
* 手动起服：`--max-num-batched-tokens 2048`，并按仓库 `README.md` §4 挂上重排载荷
  `patches/files/deepseek_v41.repack.py`（覆盖 `vllm_ascend/core/deepseek_v41.py`）；
* **不要手动钉 `KV_CACHE_MEMORY_BYTES`** —— 上限夹取会按运行期几何自动算；
  钉死一个大值会在可用 KV 更小的机器上 OOM（A2 的可用 KV 比 A3 少 2.2 GiB）。
* 要 **prefill 优先**：`BAT_TOKENS=8192` 并关掉重排 ⇒ 回到 2,987,727 token、prefill 最快。

> 该默认目前只在 **A3** 入口生效；**A2 入口（`scripts/serve_a2.sh`）仍是 8192**
> （重排载荷按 A3 镜像移植，A2 上尚未实测）。

#### 完整验收（发布默认配置下）

| 项目 | 结果 |
|---|---|
| 长上下文检索 8K / 32K / 128K | **10/10 / 10/10 / 10/10** |
| 长上下文检索 256K | **10/10** |
| 长上下文检索 580K（压力点） | **10/10** |
| **真实 agent 轨迹**（27 工具、多轮） | **10/10、10/10** |
| Vision | **23/23** |
| GSM8K-200 | **199/200** |
| `static_kernel` 降级 | **0 次** |
| Engram-int8 常驻 | ✅ |

其中那两条真实 agent 轨迹在修复前分别是 **0/3 和 0/4**。

#### ⚠️ `MAX_SEQS=64` 的组合注意

`BAT=8192`（旧口径）会让 activation 峰值从 0.79 GiB 涨到 3.21 GiB。若同时把
`--max-num-seqs` 开到 64（capture 桶要覆盖到 384），`GPU_UTIL=0.94`
会在 ACL graph 重放时 **OOM**：

```
torch.OutOfMemoryError: NPUGraph.cpp:281
Resource_Error_Insufficient_Device_Memory(EL0019)
```

| 组合 | 结果 |
|---|---|
| `MAX_SEQS=32` + `BAT=8192` + `0.92`（**脚本默认**） | ✅ |
| `MAX_SEQS=32` + `BAT=8192` + `0.94` | ✅ 但长 prompt 的 prefill 慢 6~7×，见下 |
| `MAX_SEQS=64` + `BAT=8192` + `0.90` | ✅（KV 降到 2.56M） |
| `MAX_SEQS=64` + `BAT=8192` + `0.94` | ❌ OOM |

一键脚本已加提示，检测到危险组合会打印建议。

#### ⚠️ `--gpu-memory-utilization` 是长 prompt 首 token 延迟的命门

**默认值的 0.92 不是为了贪显存，而是留 activation 余量。** 实测（8×910C、真实权重、
`BAT_TOKENS=8192`、关前缀缓存保证真跑 prefill。下表 KV 列是 **BAT=8192 口径**）：

| `GPU_UTIL` | 设备余量 | 8K prompt 首 token | KV tokens |
|---:|---:|---:|---:|
| **0.92（脚本默认）** | **7.36 GiB** | **1.14 s** | **2,823,080** |
| 0.94 | 6.11 GiB | **8.0 s** | 3.09M |
| 0.88 | 9.80 GiB | 1.28 s | 更少 |

机制：vLLM 在 startup profiling 阶段量到的 activation 峰值（3.21 GiB）是
**在 KV cache 分配之前**测的；而真实 8K prefill 需要**约 6 GiB**。
差额靠显存余量兜 —— 余量不足时分配器要反复向驱动申请/归还，
模型 `forward` 慢 2.1×，每条新请求还要多等约 6 秒把显存池撑大。

**收益随 prompt 变长而放大**（chunked prefill，每 chunk 8192 token）：

| prompt tokens | `GPU_UTIL=0.94` | **`GPU_UTIL=0.92`** | 改善 |
|---:|---:|---:|---:|
| 8 192 | 8.0 s | **1.14 / 1.16 / 1.17 s** | 7.0× |
| 32 768 | 29.1 s | **4.22 s** | 6.9× |
| 131 072 | 102.3 s | **18.17 s** | 5.6× |

⇒ prefill 吞吐约 **7.2 K token/s**，且 **per-chunk 成本恒定（1.03–1.18 s）**，
与序列长度无关。

**取舍**：`GPU_UTIL` 从 0.94 降到 0.92 会让 KV 池少约 8.6%
（3,088,412 → **2,823,080** tokens，BAT=8192 口径）。若你的场景极度依赖 KV 容量、
且几乎不跑长 prompt（上下文主要在 20K 以内），可以显式 `--gpu-memory-utilization 0.94`，
但要知道代价是首 token 从 1.1 s 涨到 8 s。

> ⚠️ **别再叠加这一条**：交付默认已经用 `BAT=2048` + 重排把容量拿到 **4,010,585**
> （见 §3.1）。`GPU_UTIL` 与 `BAT_TOKENS` 是**两条方向相反**的容量杠杆
> （降 BAT 拿容量、升 GPU_UTIL 也拿容量），但**两个都伤 prefill** ⇒
> 默认只用了前者，不要再把 `GPU_UTIL` 往上推。

完整机制、原始显存轨迹与单变量对照见配套仓库的
[`docs/prefill-memory-headroom.md`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/blob/main/docs/prefill-memory-headroom.md)。

#### 这不是模型能力问题

同一批 prompt（逐字节相同）发给官方 `api.deepseek.com`：**12/12 全部通过
（含 252K token）**；我们的服务在同长度上约 0%。⇒ 模型有能力，是推理栈的
**KV 池 32 位块号回绕**问题（已修，见上）。

#### 代价与取舍

| 项 | **`BAT=2048` + 重排（交付默认）** | `BAT=8192`（无重排） |
|---|---:|---:|
| KV cache（8×910C、`GPU_UTIL=0.92`） | **4,010,585 tok** | 2,987,727 tok |
| activation 峰值 | **0.79 GiB** | 3.21 GiB |
| prefill（8K） | 6,478 tok/s | ~7.2K tok/s |

⇒ 交付默认**同时拿容量与安全**（重排把上界抬到 32,768 块才装得下）；
代价是 prefill 分块更细（约 −11%）与首 token 更慢。
若你的场景 **prefill 优先、且容量够用**，可显式回退：
`BAT_TOKENS=8192` 并关掉重排。

> ⚠️ **不要靠调大 `--gpu-memory-utilization` 把 KV 补回来** —— 实测会 OOM：
>
> | 配置 | KV tokens | 结果 |
> |---|---:|---|
> | `BAT=8192` + `util=0.92`（当时的默认） | 2,823,080 | ✅ 稳定，prefill 最快 |
> | `BAT=8192` + `util=0.94` | 3,088,412 | ✅ 但 prefill 慢 6~7× |
> | `BAT=8192` + `util=0.95` | 3,221,350 | ❌ 第一个真实 prefill 就 OOM |
> | `BAT=6144` + `util=0.94` | 3,415,799 | ❌ ACL graph 重放 OOM |
>
> 原因是**真实请求的 activation 峰值远高于启动 profiling 报告的值**：
> profiling 在 KV cache 分配**之前**量到 3.21 GiB，真实 8K prefill 需要**约 6 GiB**
> （差额约 2.8 GiB）。实测需留 **≥ 7 GiB** 设备余量才不让 prefill 变慢。
> 若必须满足更高的 KV 门槛，应评估裁剪 `cudagraph_capture_sizes`
> （代价：高并发 decode 退回 eager），而不是调 `gpu_memory_utilization`。

#### 自查方法

配套仓库提供长上下文检索探针：

```bash
python3 tests/agent_trace/longctx_retrieval.py \
    --base http://127.0.0.1:8020 --tokens 60000 --reps 10 --out /tmp/needle.json
# 正常应输出 10/10
```

完整分析见配套仓库的
[`reports/longctx-accuracy-fix.md`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/blob/main/reports/longctx-accuracy-fix.md)。

## 4. 实测性能与验证范围

> **验证范围**：下列性能数据在**单台 A3 的 4 卡 8 chip** 上测得；**A2（8×910B3）**
> 另做过真机验证（`DRAFT_GRAPH`、Engram host 路径、自检与起服链路，见 §8 第 1 条），
> 但下表未逐格在 A2 上复测。其他配置下的实际表现可能不同，请以实测为准。

配置：单机 4 卡 8 chip、TP8，`static_kernel=1` + mtpq + Engram gate `CHUNK=0` + local-owner +
hash 向量化 + jemalloc。

> **口径**：A3-node1（8×910C，chips 8-15）｜**全补丁 + CPython PGO**｜quote 单流、
> `max_tokens=256`、`temperature=0`。**`tok/s = A × 1000 ÷ ms/step`**。
>
> ⚠️ **`A`（接受长度）在中短上下文明显更低**（8K ≈1.7、32K ≈1.8、128K ≈2.75）
> ⇒ **不要拿 8K 的 tok/s 代表整机性能**。

| 上下文 | ms/step | A | 单流 tok/s | 备注 |
|---|---:|---:|---:|---|
| 8K | 28.9 | 1.67 | 58.0 | faB 臂 2 发中位 |
| 32K | 30.5 | 1.84 | 60.4 | 同上 |
| **128K** | **30.2 – 31.6**（最好 26.9） | **2.75** | **85 – 90** | 163 发全量重算 |
| 512K | 46.0 | 1.50 | 32.6 | 长上下文 A 掉到 1.5 ⇒ tok/s 随之下滑 |

**开 `DRAFT_GRAPH=1`（投机解码入图）后单流还能再快一截**
（1024 prompt / 256 out、`conc=1` 档 8 发中位）：

| | ms/step | 单流 tok/s |
|---|---:|---:|
| A3（8×910C）eager → 入图 | 36.9 → **23.9 / 24.9** | 66.5 → **100.7 / 109.8** |
| A2（8×910B3）eager → 入图 | 64.8 → **34.3** | 54.7 → **88.7** |

> A2 的收益（−30.5 ms/step、+62%）比 A3 更大 —— 910B3 的 CPU 更弱，
> draft 的 eager 派发开销更大。**但收益与并发强相关：并发 1–2 开、≥4 关**，
> 见 §4.1 的 C 表。开关**只能在起服时决定**。

| 资源项 | 实测 |
|---|---|
| 首次起服耗时 | READY 377 s（含静态 kernel 编译，约 8–12 min） |
| 权重占用 | 约 39 GiB |
| KV 容量 | **4,010,585** tokens（A3 交付默认：`BAT_TOKENS=2048` + KV32 slot 重排 + `GPU_UTIL=0.92`；= 1M 上下文 × 3.82 并发。旧口径 `BAT=8192` 无重排为 2,987,727，见 §3.1） |
| 长 prompt 首 token | 8K **1.14 s** / 32K **4.22 s** / 128K **18.17 s**（发布默认配置实测，见 §3.1） |

### 4.1 并发吞吐（单机 4 卡 8 chip，`MAX_SEQS=64` + prefix caching ON）

每条 prompt **精确 1024 token**（用服务端 `/tokenize` 校准，64/64 命中）、
输出 256 token（强制生成满）、**每档跑完同一批 64 条请求**，2 次取中位数：

> **`decode step`（ms）＝ `1000 × 接受长度 ÷ 单流吞吐`** —— 服务**走一步**的总时间。
> 并发越高、一步里塞进的流越多 ⇒ 它必然变大；但它变大的同时**一步产出的 token 也更多**
> （一步产出 ≈ 并发数 × 接受长度）。**不能**用 `decode step` 单独判断好坏。

#### A. `DRAFT_GRAPH=0`（eager draft —— 历史默认）

| 并发 | 单流吞吐 | **decode step** | 总吞吐 | 加速比 | 单流效率 | 接受长度 | TTFT |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **90.3** tok/s | **31.1 ms** | 87.1 tok/s | 1.00× | 100% | 2.81 | 0.20 s |
| 2 | 89.2 | **31.7 ms** | 151.5 | 1.74× | 99% | 2.82 | 0.36 s |
| 4 | 80.0 | **35.0 ms** | 237.7 | 2.73× | 89% | 2.80 | 0.55 s |
| 8 | 59.3 | **48.6 ms** | 324.4 | 3.72× | 66% | 2.88 | 0.94 s |
| 16 | 42.5 | **65.4 ms** | 432.6 | 4.97× | 47% | 2.78 | 1.83 s |
| 32 | 31.3 | **91.3 ms** | 583.9 | 6.70× | 35% | 2.86 | 3.82 s |
| 64 | **20.2** tok/s | **139.9 ms** | **719.5** tok/s | **8.26×** | 22% | 2.82 | 7.16 s |

#### B. `DRAFT_GRAPH=1`（draft 入图 —— 低并发推荐开启）

| 并发 | 单流吞吐 | **decode step** | 总吞吐 | 加速比 | 单流效率 | 接受长度 | TTFT |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | **110.3** tok/s | **25.1 ms** | 108.3 tok/s | 1.00× | 100% | 2.77 | 0.22 s |
| 2 | 100.4 | **28.6 ms** | 164.1 | 1.52× | 91% | 2.87 | 0.43 s |
| 4 | 76.8 | **36.1 ms** | 225.8 | 2.08× | 70% | 2.77 | 0.67 s |
| 8 | 54.7 | **51.0 ms** | 308.2 | 2.85× | 50% | 2.79 | 1.14 s |
| 16 | 40.9 | **67.4 ms** | 407.5 | 3.76× | 37% | 2.76 | 2.14 s |
| 32 | 29.6 | **94.4 ms** | 542.1 | 5.01× | 27% | 2.80 | 4.35 s |
| 64 | **19.2** tok/s | **145.9 ms** | **646.2** tok/s | 5.97× | 17% | 2.80 | 8.60 s |

#### C. ★ 同并发对比：`DRAFT_GRAPH=1` 相对 `=0`

| 并发 | 1 | 2 | 4 | 8 | 16 | 32 | 64 |
|---|---:|---:|---:|---:|---:|---:|---:|
| **单流吞吐** | **+22.2%** | **+12.6%** | −4.0% | −7.6% | −3.8% | −5.4% | −5.0% |
| **总吞吐** | **+24.4%** | +8.3% | −5.0% | −5.0% | −5.8% | −7.2% | **−10.2%** |
| **decode step** | 31.1 → **25.1** | 31.7 → **28.6** | 35.0 → 36.1 | 48.6 → 51.0 | 65.4 → 67.4 | 91.3 → 94.4 | 139.9 → 145.9 |

**⇒ 收益与并发强相关，按场景选**：**并发 1–2（交互式）开**
（单流 +12~22%、总吞吐 +8~24%）；**并发 ≥4（批量）关**（总吞吐反而低 5~10%）。
接受长度全程持平（2.76–2.87）⇒ **不是质量退化**，是"瓶颈从 CPU 侧 draft 派发
转移到设备侧"的表现。开关**只能在起服时决定**。

> A / B 两表为 **2026-09-20 重采**（A3，`MAX_SEQS=64 PREFIX=1 GPU_UTIL=0.92` +
> Engram device-index 入图；7 档 × 2 次重复，**两组各自 64/64 全成功**；
> 同语料、同 prompt 校准 —— 64/64 精确命中 1024 token、切片互不重叠）。
> A 表（eager）与上一版（96.3 / 595.8）相比：**总吞吐 +20.8%**、TTFT −26%、单流 −6.2%
> —— 那是 Engram device-index 入图 + 其它优化的累积效果
> （同机共租负载与 KV 容量差异都会影响单流；两版口径一致、都可复现）。
> 与上一版（96.3 / 595.8）相比：**总吞吐 +20.8%**、TTFT −26%、单流 −6.2%
> （同机共租负载与 KV 容量差异都会影响单流；两版口径一致、都可复现）。

* **单流吞吐** = 每个请求自身的 decode 速率中位数（回答"我自己发一条能有多快"）
* **总吞吐** = 全部输出 token ÷ decode 窗口（回答"服务整体每秒吐多少 token"）
* **交互式场景**（要低延迟）建议并发 **2–4**；**离线批量**（要总吞吐）拉到 **32–64**
* 接受长度全程 **2.56–2.86**（正常范围）—— 这个值很重要：异常高（> 3.5）通常意味着
  模型掉进复读循环，吞吐会被虚高

![并发吞吐曲线](https://raw.githubusercontent.com/chiro2001/deepseek-v4.1-flash-ascend910B/main/docs/img/conc_dihuo_cn.png)

复现见仓库 [`tools/bench_concurrency.py`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/blob/main/tools/bench_concurrency.py)；
测量方法论（为什么"单流 tok/s"必须配上下文看）见
[`docs/BENCH-METHODOLOGY.md`](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B/blob/main/docs/BENCH-METHODOLOGY.md)。

### 4.2 都做了哪些性能优化（按瓶颈分类）

每项都**独立门控**、默认关闭、由起服脚本显式打开 —— 任何一项出问题都能单独关掉定位；
下面的收益都是**同会话配对 A/B** 的实测值。

| 类别 | 优化 | 做法 | 实测收益 |
|---|---|---|---|
| 通信/调度 | **MoE 走 AllGather** | TP=EP 时改走 AllGather，把标量开销按 token 数摊薄 | 128K **−4.25 ms**、32K −1.35、8K −1.23；**KV 池 3.39M→4.16M** |
| 通信/调度 | **admission gate** | 调度器给 prefill 加门控，不让长 prefill 饿死 decode | 首 token 后不再长时间不出字 |
| Engram | **INT8 表 host 常驻 + local-owner** | 表放 DRAM，省一次 metadata all_gather 与 ids all_to_all | 释放 HBM 给 KV；route 步明显变短 |
| Engram | **★ device-index 入图**（v8） | 表仍常驻 DRAM，但由**设备算子直接索引**，host 路径整体消失、查表进主图 | 同步 host 时间 **3.379 → 0.058 ms/步**；decode 并发 1 **29.5 → 28.4 ms/步** |
| Engram | **hash / plan numba JIT** | host 两条热路径改 JIT（带磁盘缓存） | hash 0.427→**0.076 ms**；plan 0.261→**0.068 ms** |
| Engram | **gate 分块** | 按 chunk 计算，去掉固定 2048 行 padding | 8K **−1.56 ms**，KV 反而更省 |
| 算子/访存 | **QLI 无候选快速路径** | 无候选时短路去重/排序链 | 99.3→50.3 µs ⇒ **−0.49 ms** |
| 算子/访存 | **rope 取表融合** | cos/sin 取表链 6 kernel → 2 | **−0.45 ~ 0.62 ms** |
| 算子/访存 | **`wo_a` 2D matmul** | 退化的 batch matmul 改 2D，并缓存转置 | **−0.31 ~ 0.76 ms** |
| 算子/访存 | **expert mask 范围比较** | 省掉 Index + IndexCheck 两个大 kernel（掩码本身保留） | **−0.51 ms**，GSM8K 100/100、Vision 23/23 |
| 运行时 | **CPython PGO**（A2 尤其有效） | 在**目标机**上按指纹自动编译解释器（不打包二进制） | 宿主微基准 −16~23%，服务侧 −4.4% |
| 运行时 | **static kernel 缓存** | 挂对产物目录（`/workspace`），命中后重启不再冷编译 | 起服 878 s → **346 s** |

> 详细的补丁清单、门控 env、逐项证据与复现命令见
> [仓库 README §4](https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B#4-补丁清单)。


## 5. 精度验收

| 项 | 结果 |
|---|---|
| Vision 图文问答 | **23/23 = 100%**（0 空答、0 错误） |
| GSM8K-200 第 1 轮 | **198/200 = 99.0%**（160.5 s） |
| GSM8K-200 第 2 轮 | **198/200 = 99.0%**（143.9 s） |

### 5.1 `--max-num-batched-tokens=8192` 下的复测（2026-09-18）

配置 = **当时**起服脚本的默认值（`BAT_TOKENS=8192` / `MAX_SEQS=32` / `GPU_UTIL=0.92` / `PREFIX=1`），
所有数据来自**同一次运行、同一个服务实例**。
（2026-10-14 起交付默认改为 `BAT_TOKENS=2048` + KV32 slot 重排 ⇒ **4,010,585** tokens；
容量与正确性证据见 §3.1。）

> 注：本轮验收当时用的是 `GPU_UTIL=0.94`。`GPU_UTIL` 只决定显存分配与吞吐，
> **不改变任何计算结果**，因此下列精度结论在默认的 0.92 下同样成立
> （差别仅在于 KV 池为约 2.99M 而非 3.09M tokens，远大于验收用到的 580K）。

| 项 | 结果 |
|---|---|
| Vision 图文问答 | **23/23** |
| GSM8K-200 | **199/200 = 99.5%**（另一次 198/200） |
| 长上下文检索 8K / 32K / 128K | **10/10 / 10/10 / 10/10** |
| 长上下文检索 256K | **10/10**（258,476 token） |
| **长上下文检索 580K**（压力点） | **10/10**（579,913 token） |
| 真实 agent 轨迹 A（40 条消息 / 27 工具） | **10/10** |
| 真实 agent 轨迹 B（11 条消息 / 27 工具） | **10/10** |
| `static_kernel` 降级次数 | **0** |
| KV cache | **3,088,412 tokens**（本轮 `GPU_UTIL=0.94` 时；`BAT=8192` + 0.92 下为 2,987,727。当前交付默认 4,010,585，见 §3.1） |

> 其中那两条真实 agent 轨迹在修复前（`BAT=2048`）分别是 **0/3 和 0/4**。
> 详见 §3.1。

## 6. 版本指纹

| 项 | 值 |
|---|---|
| 量化并行度 | 8 chip（DP8） |
| 冻结日期 | 2026-09-16 |
| msmodelslim 分支 | `dsv41-w4a8`，打补丁后 HEAD `e05b47190392bace361a012f115d64f4abcca30d` |
| 上游基线（补丁 apply 目标） | `92e219fa9565a5bad84d90474a27bb11524d691c` |
| 主配方 | `deepseek_v4_1_flash_w4a8.yaml`，sha256 `d3d9bdc6f2f249407dbbdb9faea8414a7d448a153c38f9ea1c36e3451deb7345` |
| 标定数据 | `mix_calib.jsonl`（75,929 B），sha256 `802b21aef7585794e534643d17a4c316b6eed1f0ea22fe405e6d228ac4024f8b` |
| 主 patch | `msmodelslim_v41_w4a8.patch`（1687 行），sha256 `15f8368ea7813dbb337267d02136d330c36e23f681b892c5e866b2a9e286acfb` |

### 完整性校验

`release/CHECKSUMS.sha256` 列出仓库内每个文件的路径与 sha256；
分片与还原后文件的对应关系见 `engram_int8/PARTS.sha256`。

## 7. 复现量化

`release/` 内含完整复现材料：

```bash
# 1) 取 msmodelslim 并切到上游基线
git clone <msmodelslim 仓库> && cd msmodelslim
git checkout 92e219fa9565a5bad84d90474a27bb11524d691c

# 2) 打补丁（推荐用脚本：强制校验基线、逐补丁 --check、并建好 editable 安装所需软链）
bash release/msmodelslim/scripts/apply_msmodelslim_patch.sh --dir "$PWD"

# 等价的手工做法
git apply --check -p1 release/msmodelslim/patches/msmodelslim_v41_w4a8.patch
git apply         -p1 release/msmodelslim/patches/msmodelslim_v41_w4a8.patch

# 3) 量化（容器内，工作目录 = msmodelslim 根）
python3 -m msmodelslim quant \
  --model_path /models/DeepSeek-V4.1-Flash-stage1 \
  --save_path  /out/stage1 \
  --config     release/msmodelslim/recipes/deepseek_v4_1_flash_w4a8.yaml \
  --device npu --device_id 0 1 2 3 4 5 6 7 \
  --model_type deepseek_v41 --trust_remote_code true --log_level info
```

> 请务必将补丁打在**上游基线 `92e219f`** 上。若 checkout 到已包含该改动的较新 commit，
> `git apply` 会因文件已存在或内容不匹配而失败。

**补丁适用范围**：本补丁只覆盖**主干 W4A8 量化（stage1）**这一步，即「如何把官方基座量化
成主干权重」。补丁内的模型实现（`deepseek_v41/model.py`）**仅供量化标定阶段使用**，
标定样本按整条序列送入，因此它只走 `start_pos == 0` 的完整前向、未实现逐 token 的增量路径。
**这不影响权重的推理能力**——推理由运行时（vLLM-Ascend）自身的实现完成，
prefill 与 decode 均完整支持（本版本的精度验收即包含逐 token 生成）。

该补丁**不包含**：activation 的 fp8/fp4 量化、candidate 两级筛选、Engram、DSpark MTP、
VL 的适配代码。完整权重还包含 4 个后处理阶段（DSpark draft / Engram int8 / Vision+qrot /
mtpq），由 `release/msmodelslim/scripts/` 下的脚本完成。

标定数据：`release/msmodelslim/calib/mix_calib.jsonl`。

## 8. 已知限制

1. **性能数据以单台 A3 的 4 卡 8 chip 为准**（§4）。**A2（8×910B3）**已做的真机验证：
   * `DRAFT_GRAPH=1`：单流 **54.7 → 88.7 tok/s（+62%）**、`[bneck] hp` 64.8 → **34.3 ms/step**，
     Vision **23/23**；**A2 的收益比 A3 更大**（910B3 CPU 更弱 ⇒ draft 的 eager 派发更贵），
     打开后 A2 单流**追平 A3**；
   * **Engram 算子入图在 A2 上不可用**（整表 `aclrtHostRegister` 返回 `207001`）⇒
     A2 必须用 `ENGRAM_DEVICE_INDEX=0` 走 host 路径（功能与精度不变，只是没有该项加速）；
   * 起服脚本、自检、挂载权限（`engram_int8` 需 `:rw`）与端口/模型名自定义均在 A2 真机跑通。

   A2 的其它项（并发表、长 prompt 首 token、GSM8K）**未逐项复测**。
2. 需要修改版 vLLM / vLLM-Ascend（**已发布**，见上文「起服前必读」第 2 条与第 3 节）——
   原版 vLLM-Ascend 不带本模型所需的 Engram host 常驻 / 设备索引与调度补丁，
   直接用官方版加载会失败。
3. GSM8K-200 分辨率为 0.5%/题，只能反映量级，不足以判定微小的精度差异；
   未跑 C-Eval / MMLU 等更广泛的评测。
4. ~~未测长上下文（8K / 128K / 512K）下的精度抽样~~ → **已测并已修复**：
   长上下文正确率曾随 chunk 数下滑，**根因是 KV 池越过 32 位块号边界**（不是分块粒度），
   已由 slot 重排 + 上限夹取修复；10K–260K token 全部 100%，另经真实 agent 轨迹、
   Vision 23/23、GSM8K 199/200 复测。见 §3.1。
5. **KV cache 容量**：A3 交付默认（`BAT_TOKENS=2048` + 重排 + `GPU_UTIL=0.92`）
   为 **4,010,585 tokens**；旧口径（`BAT=8192`、无重排）为 2,987,727。
   这是 prefill 速度与容量的取舍，见 §3.1。
6. 补丁除新增 V4.1 适配代码外，还会改动 msmodelslim 的既有文件
   `msmodelslim/model/deepseek_v4/model.py`（V4.1 复用其中的构建块）。
   新增能力全部由开关控制，默认值与 V4 一致，**不影响既有的 V4 量化流程**。

## 9. release/ 目录

```
release/
├── CHECKSUMS.sha256                 全量上传文件的 sha256 清单
├── msmodelslim/
│   ├── patches/msmodelslim_v41_w4a8.patch        主补丁
│   ├── patches/PATCHES.md                        补丁说明（基线/用法/md5）
│   ├── scripts/apply_msmodelslim_patch.sh        一键打补丁
│   ├── recipes/deepseek_v4_1_flash_w4a8.yaml     主配方
│   ├── calib/mix_calib.jsonl                     标定数据
│   └── scripts/                                  阶段 2–5 后处理脚本
├── reports/
│   ├── quant-repro-validation.md                 链路复现判定
│   └── quant-repro-accuracy.md                   端到端精度验收
└── tools/check_release.sh                        结构自检脚本
```

## 10. 许可

权重继承基座模型
[DeepSeek-V4.1-Flash](https://www.modelscope.cn/models/deepseek-ai/DeepSeek-V4.1-Flash)
的许可（Apache License 2.0）。使用时请同时遵守基座模型的使用条款。
