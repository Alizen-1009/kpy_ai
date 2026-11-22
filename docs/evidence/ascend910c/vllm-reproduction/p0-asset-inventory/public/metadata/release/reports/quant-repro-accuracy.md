# 量化复现版本端到端精度验收（本机 A3 / chips 8–15）

> 执行者：`quantval_accuracy` 子代理　执行窗口：2026-09-16 01:35 → 01:57 (+08)
> 被测模型：`/path/to/models/out/quantval_20260915_2235/final`（本次现场装配，记 `$F`）
> 真值模型：`/path/to/models/out/v41-w4a8-engram-dr-vision-qrot-mtpq`（记 `$T`）
> 本文补齐 `reports/quant-repro-validation.md` **§7.2「未做端到端精度回归」** 留下的缺口。

---

## 0. 结论

**PASS —— DP8 复现出的「数值等价权重」在端到端精度上不可区分于真值。**

| 验收项 | 真值基线 | 本次复现版本 | 判定 |
|---|---|---|---|
| **Vision**（23 题短答） | 23/23 = 100%，0 空答 / 0 错误 / 负例 OK | **23/23 = 100%**，0 空答 / 0 错误 / 负例 OK | ✅ **完全一致** |
| **GSM8K-200**（chat 8-shot，conc4） | 198/200 = **99.0%**（150.0 s） | **198/200 = 99.0%**（两轮：160.5 s / 143.9 s） | ✅ **完全一致** |
| 装配目录结构 | — | index **190,728** 键逐键相同、分片桶分布相同、`config.json` 语义相同 | ✅ |
| 关键权重分片 | — | `vision-00001-of-00001` sha256 **逐字节相同**；`mtpq-0000{1..4}` **逐字节相同** | ✅ |

装配产物里唯一**非 bit-exact** 的是 `engram_extra.safetensors`：10 个张量中 8 个逐位相同，2 个
`wkv.weight` 各有 **39 / 51 个元素（占 2.5e-7）差 1 个 bf16 ULP**；已用 fp64 参考折叠证明这是
**同精度下的末位舍入**，不是算法或权重差异（§7.1）。

---

## 1. 任务背景与本报告的定位

`reports/quant-repro-validation.md` 已证明：本机 A3 后 8 chip 从零重跑的量化链路中，阶段 2–5 对真值
**逐字节复现**，阶段 1 主干 W4A8 因 **DP 宽度不同（真值 DP16 vs 本次 DP8）** 产生 47.5% 张量差异，
幅度为 int8 几个 LSB，判定为「数值等价级」；但该报告 §7.2 明确写着
**「未做端到端精度回归：本任务范围是权重复现，未起服务跑 GSM8K / 视觉验收」**。

本次工作的目标就是把这最后一环补上：**把该等价权重装成可服务目录、起服务、按真值同样的口径实测
Vision 与 GSM8K-200，并与真值逐项对照。**

---

## 2. 装配：命令与结果

### 2.1 输入

| 角色 | 路径 | 本次用途 |
|---|---|---|
| 主干 + BF16 draft（= 真值链的 `v41-w4a8-dspark`） | `$R/dspark` | `engram_dr_build.py` 的 `--src` |
| Engram int8（206 GB，4 文件） | `$R/engram-int8` | `--int8` |
| 旋转前 / 旋转后视觉分片 | `$R/dspark-vision` / `$R/qrot-vision` | 视觉分片来源 |
| mtpq 量化 draft | `$R/dspark-mtpq` | 合并进最终目录 |
| 官方 FP8 基座 | `/path/to/models/DeepSeek-V4.1-Flash` | `engram_extra` 的 wkv / q_weight / k_weight、266 个视觉张量 |

> 真值链的目录级装配（`v41-w4a8-engram-dr` → `-vision` → `-vision-mtpq` → `-qrot-mtpq`）此前也**从未被复现过**
> （§7.3 同样是缺口）；本次一并补齐。

### 2.2 装配脚本与执行方式

装配脚本落在持久路径，**只读**输入、全部写入落在 `$R/` 下的新目录，绝不覆盖既有产物：

```bash
R=/path/to/models/out/quantval_20260915_2235
bash $R/acc_assemble_run.sh          # 入口（内部用临时容器跑 $R/acc_assemble.sh）
```

`acc_assemble_run.sh` 用的是**一个不挂载任何 `/dev/davinci*` 设备**的临时容器
（本任务装配容器，只 `-v /path/to:/path/to`）——
装配全程纯 CPU，**没有任何一次调用能碰到任何 chip**；之所以要在容器里跑，是因为
`$R/*` 与 `$R/stage1/*` 是 **root:600**，且 mslim venv 的 `python3` 指向容器内的
`/usr/local/python3.12.13`（宿主机上不存在）。

### 2.3 四级装配（逐级复刻真值链）

```bash
PY=/path/to/dsv41/env/mslim-venv/bin/python          # 容器内可用
PA=/path/to/dsv41                                    # 装配脚本所在工程根
OFF=/path/to/models/DeepSeek-V4.1-Flash

# ① engram_dr_build.py：stage1 dspark + engram-int8 → engram-dr（含 QuaRot V 投影折叠）
$PY $PA/scripts/engram_dr_build.py --src $R/dspark --out $R/engram-dr \
    --official $OFF --int8 $R/engram-int8

# ② add_vision_weights.py：把官方 266 个视觉张量写成独立分片 + prepare_runtime_ckpt 注入 quantization_config
$PY $PA/scripts/add_vision_weights.py --official-dir $OFF --target-dir $R/engram-dr-vision
$PY $PA/scripts/prepare_runtime_ckpt.py --dir $R/engram-dr-vision

# ③ mtpq_make_vision_dir.py：把 mtpq draft 挂进 vision 目录（非 mtp 部分全部绝对软链）
$PY $PA/scripts/mtpq_make_vision_dir.py --vision-dir $R/engram-dr-vision \
    --mtpq-dir $R/dspark-mtpq --out $R/engram-dr-vision-mtpq

# ④ 最终目录：全软链指向 ③，再换入 qrot 视觉分片（真值就是这一层结构）
mkdir -p $R/final && for f in $R/engram-dr-vision-mtpq/*; do ln -s "$f" $R/final/; done
rm -f $R/final/vision-00001-of-00001.safetensors
cp $R/qrot-vision/vision-00001-of-00001.safetensors $R/final/vision-00001-of-00001.safetensors
```

**耗时：57 s**（01:38:22 → 01:39:19，含 629 MB `engram_extra` 与 0.97 GB 视觉分片写入）。

### 2.4 装配自检（`$R/logs_acc/step5_selfcheck.log`）

```
[check] index keys   = 190728
[check] desc entries = 191900
[check] missing shards = 0 []
[check] shards referenced = 82
[check] shard buckets = {'backbone': 72, 'mtpq': 4, 'engram_int8': 4, 'vision': 1, 'engram_extra': 1}
[check] quantization_config = {'quant_method': 'ascend', 'model_quant_type': 'W4A8_DYNAMIC'}
[check] engram_layer_ids    = [1, 14]
[check] max_position_embeddings = 1048576
[check] top-level entries   = 87
[check] SELFCHECK_OK
```

目录构成：**72 个主干分片**（真值 80 个，差异继承自阶段 1 的 DP8）+ `vision-00001-of-00001`
（实体文件，0.97 GB）+ **14 个软链**（`config.json` / `configuration.json` / `engram_extra.safetensors` /
`engram_int8` / `mtpq-0000{1..4}` / `mtpq_manifest.json` / `optional` / `quant_model_description.json` /
`quant_model_weights.safetensors.index.json` / `tokenizer_config.json` / `tokenizer.json`）；
合计 **87 项**，与真值归一化后**逐名相同**（真值 95 项 = 87 + 8，差值恰为 80−72 个主干分片）。

---

## 3. 起服

```bash
cd /path/to/dsv41-workspaces/wt-graph
MODEL=$R/final PORT=8022 PROFILE=0 \
NAME=dsv41-a22-qvacc SESSION=qvacc INNER=$R/logs_acc/inner_qvacc.sh \
RUN_ID=qvacc_20260916_0140 bash scripts/serve_a22.sh
```

用 `serve_a22.sh` 的**默认实验配置**（本机推荐配置：`STATIC_KERNEL=1 + mtpq + GATE_CHUNK=0 +
local-owner + hash 向量化 + jemalloc`），只改 `MODEL` / `PORT` / `PROFILE` / 容器名 / `INNER`。

| 项 | 值 | 证据 |
|---|---|---|
| 容器 | `dsv41-a22-qvacc`，`cpuset=320-639`、`mems=4-7`、`ASCEND_RT_VISIBLE_DEVICES=8..15` | `$R/logs_acc/docker_inspect_qvacc.txt` |
| 端口 | **8022** | 起服日志首行 |
| **READY** | ✅ **377 s**（`/health`=200） | `$R/logs_acc/watch_qvacc.log` |
| 权重加载 | **39.1154 GB**（与真值 mtpq 配置实测的 39.1154 GB 一致） | 起服日志 |
| **KV 容量** | **3,557,471 tokens** / 14.64 GiB / 3.39× | 起服日志 |
| jemalloc | ✅ `LD_PRELOAD detected`（未绕过 `serve_v2.sh`） | 起服日志 |
| 评测前负载 | `vllm:num_requests_running = 0` | `/metrics` 抓取 |

**起服日志（持久路径）**：`/path/to/dsv41-workspaces/wt-graph/logs/perf/qvacc_20260916_0140_serve.log`

> KV 3,557,471 vs 真值同配置的 3,557,594（差 123 tokens = 0.003%，属分配抖动），
> 与任务书「util 0.94 时 KV ≈ 3.39M tokens 属正常」一致。

---

## 4. Vision 验收

```bash
cd $P && python3 scripts/vision_accuracy_check.py --server http://127.0.0.1:8022 \
  --images-dir $OFF/inference/examples/images --official-dir $OFF \
  --out $R/logs_acc/vision_accuracy_quantval.json --expect-dspark
```

| 指标 | 真值（`logs/perf/vision_qrot_final.json`） | 本次（`$R/logs_acc/vision_accuracy_quantval.json`） |
|---|---|---|
| 通过 / 总题 | **23 / 23** | **23 / 23（100.0%）** |
| 空答 / 乱答 | 0 | **0** |
| 请求错误 | 0 | **0** |
| 强制负例（`neg-text-01` 纯文本不退化、`neg-swap-01` 换图问反） | OK | **OK** |
| verdict | PASS | **PASS** |
| 图像 token（carrots / corn） | 446 / 191 | **446 / 191（逐项一致）** |
| dspark 接受率 | 0.1872 | 0.1990 |

判据（≥80% 短答命中、0 空答、0 请求错误）**全部满足且为满分**。
（对照：真值在 qrot 修复**之前**的同一套题目是 11/23 = FAIL，见 `logs/perf/vision_final.json` ——
说明本套题目确实能分辨出 5 张视觉边界张量是否折叠了全局旋转，不是「怎么测都通过」的软判据。）

---

## 5. GSM8K-200 验收

```bash
cd $P && env HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  HF_ENDPOINT=https://hf-mirror.com \
  /path/to/venvs/lmeval311/bin/python scripts/acc_eval.py --task gsm8k --limit 200 \
  --mode chat --conc 4 --max-tokens 512 --base-url http://127.0.0.1:8022 \
  --out $R/logs_acc/gsm8k200_quantval{.json} --tag quantval
```

**离线环境变量已带齐**（`HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1
HF_ENDPOINT=https://hf-mirror.com`），数据集走本地缓存，未出现 §F3 记录的 15 分钟静默挂死。

| 轮次 | 得分 | 空答 | 错误 | 耗时 | 错题 |
|---|---|---|---|---|---|
| 本次 run1 | **198/200 = 99.0%** | 0 | 0 | 160.5 s | `gsm8k-93`（36→11）、`gsm8k-119`（95200→40） |
| 本次 run2 | **198/200 = 99.0%** | 0 | 0 | 143.9 s | `gsm8k-119`（95200→560）、`gsm8k-146`（2125→2625） |
| 真值 `static_mtpq`（推荐配置） | 198/200 = 99.0% | 0 | 0 | 150.0 s | `gsm8k-74`、`gsm8k-119` |
| 真值 `base`（static=0 基线） | 198/200 = 99.0% | 0 | 0 | 152.4 s | `gsm8k-12`、`gsm8k-119` |

**逐题对照（关键）**：`gsm8k-119` 在真值的两轮基线与本次两轮里**全部答错** —— 是这套题里的
固有难点，不是本次权重引入的退化；而「第二道错题」在真值是 `{12, 74}`、本次是 `{93, 146}`，
**随运行轮次抖动**（同一模型同配置的 run-to-run 方差）。两轮结果与真值**同为 99.0%**。

> 分辨率提示：200 题样本的标准误约 ±0.7%，99.0% 与 99.0% 只能判「同级」，不能判「更优/更差」；
> 若要更细的判别力需扩样（本次范围外）。

---

## 6. 与真值逐项对照

对照脚本：`$R/acc_compare.py`，日志 `$R/logs_acc/compare_vs_truth.log`。

| # | 对照项 | 结果 | 判定 |
|---|---|---|---|
| 1 | 顶层条目名集合（分片名归一化） | ours 87 / truth 95，`only_ours=[]`、`only_truth=[]` | ✅ |
| 2 | `quant_model_weights...index.json` 键集合 | **190,728 == 190,728**，双向差集 0 | ✅ |
| 3 | 每键指向分片的「桶」（主干/engram_int8/engram_extra/mtpq/vision） | 190,728 键**逐键一致**，mismatch 0；桶计数两边各为 `backbone 185,734 / mtpq 4,718 / vision 266 / engram_extra 6 / engram_int8 4` | ✅ |
| 4 | index 引用的分片全部可解析 | missing = 0 | ✅ |
| 5 | `quant_model_description.json` 键集合 | **191,900 == 191,900** | ✅ |
| 6 | description 标签分布 | 两边同为 `W4A8_DYNAMIC 188,928 / FLOAT 2,169 / W8A8_DYNAMIC 799 / 1.0.0 1` | ✅ |
| 7 | `config.json` 语义相等 | 0 个顶层键不同（含 `quantization_config`、`engram_rotation_config`、`engram_layer_ids`、`max_position_embeddings`） | ✅ |
| 8 | `vision-00001-of-00001.safetensors` sha256 | 两边 `db6f1a7c1f0bd24b…` **逐字节相同** | ✅ |
| 9 | `mtpq-00001` / `mtpq-00004` sha256 | `1d1fa8b12a31770e…` / `13533833b4477f2f…` **逐字节相同** | ✅ |
| 10 | `engram_extra.safetensors` sha256 | **不同**（见 §7.1，1 ULP 级舍入） | ⚠️ 等价 |
| 11 | `mtpq_manifest.json` | 仅 `generated_utc` / `src` / `out` 三个元数据字段不同（其余全同） | ✅ 预期 |
| 12 | **端到端精度**（Vision / GSM8K） | 23/23 vs 23/23；198/200 vs 198/200 | ✅ |

### 6.1 判定

**PASS。** 采信理由：

1. 两项端到端精度与真值**逐项相同**（Vision 满分、GSM8K 同为 99.0%，且难点错题集合交集为真值侧同样答错的 `gsm8k-119`）；
2. 装配产物在**键集合、分片布局语义、标签分布、config** 四个层面与真值**逐项一致**，index 键数 190,728 精确相等；
3. 权重层面，除阶段 1 已归因的 DP 差异外，视觉分片与 mtpq 分片**逐字节相同**；唯一新增的
   `engram_extra` 差异已被证明是末位舍入（§7.1），不是内容差异。

---

## 7. 异常、归因与未验证项（诚实披露）

### 7.1 新发现：`engram_extra.safetensors` 非 bit-exact（已归因，判为等价）

这是本次装配**新暴露**的一处差异（既有的 §4 对照没有覆盖 `engram_extra`，因为原任务没做目录级装配）：

| 张量 | 结果 |
|---|---|
| `layers.{1,14}.engram.embed.weight` / `.scale` | **逐位相同**（[1,1] 占位） |
| `layers.{1,14}.engram.q_weight` / `.k_weight` | **逐位相同**（BF16 直接拷贝） |
| `layers.1.engram.wkv.weight` | 39 / 157,286,400 个元素不同（**2.5e-7**），max\|Δ\| = 6.10e-5（**1 个 bf16 ULP**） |
| `layers.14.engram.wkv.weight` | 51 / 157,286,400（**3.2e-7**），max\|Δ\| = 1.22e-4（**1 ULP**） |

**归因实验**（`$R/attr_engram_extra.py` → `$R/logs_acc/attr_engram_extra.log`）：
用 **float64** 重算 `rotation.T @ W32` 作为参考折叠，分别度量两边与参考的 bf16 距离：

```
--- layer 1 ---
  ours : vs fp64-ref  n_diff=8055  max|d|=0.000488281  max_ulp(|ref|>1e-3)=2.000
  truth: vs fp64-ref  n_diff=8060  max|d|=0.000488281  max_ulp(|ref|>1e-3)=2.000
  ours vs truth: n_diff=39  max|d|=6.10352e-05  frac=1.240e-06
  K rows (未折叠) ours==truth: True
--- layer 14 ---
  ours : vs fp64-ref  n_diff=8073  max|d|=0.000488281
  truth: vs fp64-ref  n_diff=8084  max|d|=0.000488281
  ours vs truth: n_diff=51  max|d|=0.00012207  frac=1.621e-06
  K rows (未折叠) ours==truth: True
```

读数：**两边偏离 fp64 参考的程度几乎相同**（8055 vs 8060、8073 vs 8084，都是 ≤2 ULP 的
双重舍入误差），彼此只差 1 ULP 且只涉及 1e-6 量级的元素 —— 这是 fp32 BLAS 归约顺序
（线程数/机器不同）在 bf16 舍入边界上翻转的典型指纹，**不是**折叠公式、旋转矩阵或
FP8 反量化链路的差异（旋转矩阵 `optional/quarot.safetensors` 本身在阶段 1 已证明 bit-exact）。
未折叠的 K 行**逐位相同**，也说明输入与公式两边一致。

### 7.2 已知且预期内的差异（沿用 `quant-repro-validation.md` 的结论）

* 主干分片 **72 vs 80**：DP8 打包布局差异，键集合与总字节相同；本次实测**不影响可服务性与精度**。
* 阶段 1 主干 W4A8 有 47.5% 张量非 bit-exact（DP 宽度导致）：本次端到端精度实测证明**精度等价**。
* `mtpq_manifest.json` 的三个元数据字段（时间戳/路径）本来就不同。

### 7.3 文件属主与权限（本次装配与真值的非功能差异）

本次装配在**临时容器内以 root** 执行，所有新增文件均为 `root:root`，权限沿用输入产物的 umask 结果：

| 类型 | 本次装配 | 真值 |
|---|---|---|
| 权重分片（`final/vision-…`、`dspark-mtpq/mtpq-*`、`stage1/*.safetensors`、`engram-int8/*`） | `root:root 600` | `普通用户 644` |
| JSON（`config.json` / `index.json` / `quant_model_description.json`） | `root:root 644` | `普通用户 644` |

服务容器以 **root** 运行，实测加载正常（39.1154 GB、0 报错），**未做 chmod/chown**
以避免改动既有量化产物；若后续要让非 root 消费者直接读该目录，需要额外 `chmod`/`chown`。

### 7.4 未验证 / 存疑项

1. **样本分辨率**：GSM8K-200 的 0.5%/题 分辨率下，「同为 99.0%」只能判同级；未扩样，
   也未跑 C-Eval / MMLU 等其他任务。
2. **未测长上下文**：本次只跑短答与 GSM8K，未做 8K/128K/512K 长上下文下的精度抽样。
3. **未复现真值的 `mtpq`-only 191/200 异常**：`lmeval_out/mtpq_gsm8k200.json` 那轮 95.5% 未在本配置下复现
   （F3 报告已判为运行方差），本次的推荐配置两轮均为 99.0%。
4. **`engram_extra` 差异未做「先固定线程数再重建」的正向复现**：归因是统计 + fp64 参考论证的，
   没有在同一线程数下重跑真值侧装配来做到 bit-exact（真值侧运行环境已不可复现）。
5. **KV 容量 3,557,471 vs 3,557,594** 的 123 tokens 差异未逐项深挖（属显存分配抖动）。
6. **本轮只验证了服务可用性与精度**，未做性能对照（性能线在另一台 A3，按纪律未触碰）。

---

## 8. 证据清单

根目录 `R=/path/to/models/out/quantval_20260915_2235`

| 文件 | 内容 |
|---|---|
| `$R/acc_assemble.sh` `$R/acc_assemble_run.sh` | 四级装配脚本 + 容器入口（本次新增，已提交进仓库 `scripts/`） |
| `$R/acc_compare.py` | 装配产物 vs 真值的结构性对照（本次新增，已提交进仓库 `scripts/`） |
| `$R/attr_engram_extra.py` `$R/attr_engram_extra_run.sh` | `engram_extra` 1-ULP 差异的 fp64 归因实验（`.py` 已提交进仓库 `scripts/`） |
| `$R/cmp_engram_extra.py` `$R/cmp_engram_extra_run.sh` | 逐张量比对 `engram_extra` + diff `mtpq_manifest.json` |
| `$R/logs_acc/assemble_main.log` + `step1_engram_dr.log` `step2_vision.log` `step2_prepare_runtime.log` `step3_mtpq_merge.log` `step4_prepare_runtime.log` | 装配全程日志 |
| `$R/logs_acc/step5_selfcheck.log` | 装配自检（190,728 键 / 0 缺失 / 桶分布） |
| `$R/logs_acc/compare_vs_truth.log` | 12 项对照结果 |
| `$R/logs_acc/cmp_engram_extra.log` | `engram_extra` 逐张量 + `mtpq_manifest` diff |
| `$R/logs_acc/attr_engram_extra.log` | fp64 参考折叠归因 |
| `$R/logs_acc/watch_qvacc.log` | READY/STALL 三终态监听（READY after 377s） |
| `$R/logs_acc/vision_quantval.log` `vision_accuracy_quantval.json` | Vision 逐题 + 汇总 |
| `$R/logs_acc/gsm8k200_quantval.log` `.json` `.jsonl` | GSM8K run1（198/200） |
| `$R/logs_acc/gsm8k200_quantval_run2.log` `.json` `.jsonl` | GSM8K run2（198/200） |
| `$R/logs_acc/docker_inspect_qvacc.txt` | 容器 cpuset/mems/设备隔离证据 |
| `$R/logs_acc/npu_before.txt` `npu_after.txt` `docker_before.txt` `docker_after.txt` | 起服前/停服后 `npu-smi` 与 `docker ps` |
| `$P/logs/perf/qvacc_20260916_0140_serve.log` | 起服全量日志（`$P=wt-graph`） |
| 真值侧对照记录 | `$P/logs/perf/vision_qrot_final.json`（23/23）、`logs/perf/vision_final.json`（qrot 前 11/23）、`~/lmeval_out/{base,static_mtpq,mtpq}_gsm8k200.json` |

产物目录：`$R/engram-dr`（618 MB）、`$R/engram-dr-vision`（954 MB）、`$R/engram-dr-vision-mtpq`（29 MB）、
**`$R/final`（87 项，926 MB 实体 + 软链到 273 GB 主干 / 206 GB engram-int8）**；
**未覆盖任何既有产物**，所有写入均在 `$R/` 之下。

---

## 9. 资源占用与释放

* 装配（本任务装配容器）**不挂任何 NPU 设备**；归因实验容器加了 `--cpuset-cpus 320-639 --cpuset-mems 4-7`。
* 服务容器 `dsv41-a22-qvacc`：`cpuset=320-639`、`mems=4-7`、`ASCEND_RT_VISIBLE_DEVICES=8,9,...,15`，
  8 个 `VLLMWorker_TP*` 进程全部登记在物理 chip 8–15（`npu-smi` 的 NPU 4–7 两个 die）。
* 其他租户（chip 0–7）与其他容器全程未被触碰；另一台 A3 未被触碰。
* 收尾：停服后 `docker ps` 与 `npu-smi` 证据见 `$R/logs_acc/docker_after.txt` / `npu_after.txt`。
