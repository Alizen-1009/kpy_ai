# DeepSeek-V4.1-Flash 在 910C 上的优化：当前理解与已有工作

## 1. 项目决定与文档范围

本项目确定以 **DeepSeek-V4.1-Flash** 为主优化模型，硬件为现有 SSH 别名 `910c` 对应的 Ascend 服务器。不再以 V4、GLM 或 Qwen 作为当前主线。

后续决定：最终目标是在用户 fork 的 **DeepInfer** 内支持 910C 推理，不以另起 vLLM 服务替代目标。新增参考仓库 `ref/deepseek-v4.1-flash-ascend910B` 已有 A3 路径，可参考其量化、Engram、算子及验收经验，但不能直接将 vLLM 补丁应用到 DeepInfer。权重来源、格式差异与接入计划见 [`ref/DeepInfer/doc/ascend910c-port.md`](../ref/DeepInfer/doc/ascend910c-port.md)。其中第三方 W4A8 发布权重的原始 revision 尚未确认，不能当成已锁定的 1017 权重。

最新确定的输入路线：**直接使用官方 `deepseek-ai/DeepSeek-V4.1-Flash-1017`，不采用第三方 W4A8 权重或离线重新量化/转换链。** 第三方仓库仅提供算子实现与适配经验参考。必要的运行时局部解码、精度提升、布局重排封装在 DeepInfer 的 910C 后端中，保留官方权重和 scale 语义；当前尚未实现或验证这条整模型路径。

本机优先考察的具体 checkpoint 是 **V4.1-Flash-1017**，包括原始权重归档和 Ascend W8A8 权重。后续应固定 checkpoint、配置、框架版本和镜像 digest，不能假设其他 V4.1 发布版本完全等价。

本文整理本轮只读盘点和讨论。证据分为：

- **本轮检查**：实际读取远端目录、配置、状态文件及报告。
- **历史记录**：已有实验报告中的测量结果；本轮没有重新运行验证。
- **待验证/计划**：尚未完成的模型加载、算子适配及端到端评估。

本轮没有启动模型、运行 benchmark、修改远端环境、停止服务或重新计算大权重文件散列。本文是工作起点，不是整模型性能验收报告。

## 2. 模型结构与优化含义

### 2.1 总体结构

官方模型说明将 V4.1-Flash 描述为原生多模态 MoE，采用 **Causal Encoder-Decoder（CED）**：40 层主干分为 20 层 causal encoder 和 20 层 decoder。

官方口径的 backbone 参数量为 **552B**，每 token 激活参数约为 **prefill 8B / decode 16B**。这不是显存占用或实测 FLOP 的直接换算。Engram 参数的统计边界应沿用原始模型说明，不在本文自行加总。

主要组成：

1. 局部滑窗注意力与 **CSA2（Compressed Sparse Attention 2）**。
2. 跨层共享 main KV、Indexer K，以及复用 Top-K 索引。
3. Decoder 的分层稀疏 Indexer。
4. MoE、Single-Pass mHC、Engram 条件记忆。
5. 视觉编码器和投影器，以及 DSpark 推测解码相关路径。

### 2.2 本地 1017 checkpoint 的配置事实

以下字段已从本地原始版和 W8A8 版配置中核对，主要位于 `text_config`：

| 项目 | 值 |
| --- | --- |
| 架构 / model type | `DeepseekV41ForCausalLM` / `deepseek_v41` |
| 主干层数 / hidden size | 40 / 5120 |
| Attention heads / head dim | 64 / 512 |
| Q low-rank / O low-rank | 1280 / 1024 |
| 路由专家 / 共享专家 / 每 token 选中专家 | 384 / 1 / 6 |
| Sliding window | 128 |
| Indexer heads / head dim / Top-K | 32 / 128 / 512 |
| KV source layers | `[2, 8, 14, 20]` |
| Index source layers | `[2, 8, 14, 20, 24, 28, 32, 36]` |
| Candidate source layer | 20 |
| Candidate Top-K blocks / block size | 2048 / 8 |
| mHC mult / Sinkhorn iterations | 4 / 20 |
| Engram layers | `[1, 14]` |
| Next-N predict layers | 3 |
| 最大位置数 | 1,048,576；不代表当前环境已能运行该长度 |

配置的 `compress_ratios` 前 40 项为：第 0–1 层为 0，第 2–19 层为 2，第 20–39 层为 1。数组另有预测层对应的尾项。**不能据此认为每层独立生成自己的压缩 KV**，必须结合 source-layer 配置和实际代码理解。

### 2.3 CSA2 与 V4 的区别

V4 的本地配置主要在压缩倍率 4 和 128 间交替，对应 CSA / HCA 两种路径。V4.1 不能视为“只删掉 HCA 的 V4”。

V4.1 的 CSA2 有三类静态模式：

- **Full**：建立相应的 main KV 和索引信息。
- **Reindex**：共享相应缓存，但重新计算稀疏选择。
- **Reuse**：进一步复用已有 Top-K 索引。

Decoder 后续索引层还可以受第一个 Full 层产生的候选池约束。优化必须考虑 producer/consumer 层之间的依赖、缓存所有权、写入时机、索引有效区间及 Graph 下的生命周期。

官方说明中的 main KV 为 FP4 E2M1、每 16 通道一个 E4M3 scale。**已有 V4 算子实验用的 MXFP4 block32/E8M0 格式与此不同，不能直接认定兼容。** 实际部署还须核对框架是否保留该格式、转为其他格式，或使用独立的 Ascend KV 量化路径。W8A8 权重量化不等于 KV Cache 格式已确定。

### 2.4 优化方向：假设，不是已测热点

- Main KV / Indexer K / Top-K 的跨层复用，减少重复投影、筛选和搬运。
- 分层 Indexer 的候选池构造、评分、Top-K 和稀疏读取。
- 低精度 KV 的读取、解码、gather 与 attention 的协同。
- MoE 量化专家 GEMM、路由、dispatch/combine 和多卡通信。
- mHC 的残差流变换及相关归约。
- Engram 的查表、存储放置和数据搬运。
- 分别测量 prefill、decode；后续再单独评估 DSpark 和视觉路径。

优先级必须由真实运行的 profiling 决定，不预先断言 attention 一定是最大瓶颈。

## 3. 910C 服务器与运行边界

### 3.1 硬件及环境快照

- 连接：`ssh 910c`；远端用户为 `root`。
- `npu-smi` 显示 8 个 NPU 编号，每个含 2 个 chip/die，共 **16 个 die**，每 die **64 GiB HBM**，合计约 1 TiB。
- 所有设备健康状态显示 OK；检查时多个 die 的 AICore 利用率为 0，但有常驻进程和显存占用，**不能由 0 利用率推断设备可独占**。
- CPU 为 aarch64 Kunpeng，系统可见 640 个逻辑 CPU；主机内存约 1 TiB。
- 宿主驱动：`25.5.1`。
- 宿主 CANN：`/usr/local/Ascend/cann-8.5.0`，OPP 版本为 `8.5.0`。
- 历史算子实验容器记录：CANN `9.0.1`、Torch `2.10.0+cpu`、torch_npu `2.10.0.post2`。

宿主 SDK 与实验容器 SDK 不同。不能直接在宿主环境重编译并假定与已有产物等价。

### 3.2 现有服务

检查时发现以下运行中容器及设备映射：

| 容器 | 映射的 `/dev/davinci*` |
| --- | --- |
| `vllm-qwen35-9b` | 0、1 |
| `sglang-speech-npu` | 6、7 |
| `step-audio2-npu` | 8、9 |
| `qwen3-asr-realtime` | 12 |

这是检查时快照，不是完整或永久资源预留表。运行前必须重新核对 `npu-smi info`、容器和设备占用。已有实验使用过 die 13，但其伙伴 die 12 有服务，不应直接假定不存在共享资源干扰。

### 3.3 存储

| 路径 | 状态 |
| --- | --- |
| `/root/syf/data_yf` | 独立 XFS 数据卷挂载；约 3.5T，总使用率 85%，剩余约 540G |
| `/data2` | 约 3.5T，总使用率 94%，剩余约 217–218G |
| `/data` | 指向 `/root/FrySong/inference16_20260921_1645_FrySong/weights_volume_FrySong` 的软链接；目标检查时为空 |

`/root/syf/data_yf` 不能按普通根目录文件夹估算空间。下载说明称该挂载为 runtime-only、未修改 fstab；重启后应先核对挂载，防止写入根分区。

当前不宜在 `/data2` 再复制完整大权重；转换 checkpoint 和创建加载视图前需要计算额外空间。

## 4. 权重与参考代码清单

### 4.1 当前主线：V4.1

| 路径 | 本轮发现 | 使用边界 |
| --- | --- | --- |
| `/root/syf/data_yf/DeepSeek-V4.1-Flash-1017-original_yf` | 48 个 safetensors 文件，权重约 475.25 GiB；有配置、索引、tokenizer 和参考代码 | 下载归档，不是已验收的服务加载目录 |
| `/data2/modelzoo/DeepSeek-V4.1-Flash-1017-w8a8` | 142 个 safetensors 文件，约 727.68 GiB；索引引用的分片均存在 | Ascend W8A8；本轮未测试加载 |
| `/data2/syf/DeepSeek-V4.1-Flash-1017-original_yf` | 元数据、`inference_yf/`、`encoding_yf/`，没有权重分片 | 可用于阅读参考实现 |

原始归档的下载记录：

- `/root/syf/v41_download_status_yf.json` 记录在 `2026-11-03T06:53:25+08:00` 完成。
- `verified_files=84/84`，`all_weights_verified=true`，记录总字节数 `510311045870`。
- 这是历史下载器的 SHA256 验证记录；本轮未重新计算文件散列。
- `/root/syf/v41_inventory_yf.json` 记录上游路径、本地命名、commit 和 SHA256 映射。
- `/root/syf/README_v41_download_yf.txt` 明确说明：本地文件/目录使用 `_yf` 命名，源内容不变；直接服务前需要显式 loader 或标准文件名视图。不要直接改名破坏原始归档。

W8A8 目录额外注意：两个 Engram 分片各约 101.38 GB。索引 `metadata.total_size` 为 `577940550344` 字节，与实际 142 个分片约 727.68 GiB 的总文件大小不一致。**文件齐全不代表统计口径一致，也不代表内容完整性已重新验证**，部署前需解释差异并核对量化描述、张量和加载器。

### 4.2 V4：保留为历史对照

| 路径 | 配置 / 权重 |
| --- | --- |
| `/root/syf/data_yf/DeepSeek-V4-Flash-0731-w8a8` | `deepseek_v4`，74 分片，约 293.03 GiB |
| `/root/syf/data_yf/DeepSeek-V4-Flash-w8a8-mtp` | `deepseek_v4`，70 分片，约 279.41 GiB |

这些不是 V4.1 权重，不得混用配置、索引、格式或性能结论。

### 4.3 V4.1 参考实现

阅读目录：`/data2/syf/DeepSeek-V4.1-Flash-1017-original_yf/inference_yf/`。

| 文件 | 内容 |
| --- | --- |
| `README_yf.md` | 参考推理、转换与运行说明；明确不是生产 serving engine |
| `model_yf.py` | Attention、Compressor、Indexer、跨层共享状态、MoE、mHC、DSpark 等 |
| `kernel_yf.py` | 参考 kernel |
| `engram_yf.py` | Engram 相关支持代码 |
| `vision_yf.py`、`image_processor_yf.py` | 视觉路径 |
| `convert_yf.py`、`generate_yf.py`、`run_yf.sh` | 转换与运行入口；不代表已在 Ascend 验证 |

当前文件定位：`Compressor` 附近约第 430 行，`Indexer` 第 488 行，`Attention` 第 614 行，共享状态说明约第 1172 行。行号只对应本次读取的快照。

参考 README 的 self-test 使用未初始化权重，只检查形状/路径，不能作为模型数值正确性证明。脚本中的上游标准文件名也不能在 `_yf` 归档下未经适配直接照抄执行。

## 5. 已有算子工作

### 5.1 工作目录与入口

核心目录：`/root/syf/kernel_agent_v4_yf/`。

| 文件/目录 | 作用 |
| --- | --- |
| `sources_yf/inference_model_yf.py` | V4 风格模型参考，包含 Compressor、Indexer、Attention、Gate/Expert/MoE |
| `sources_yf/inference_kernel_yf.py` | FP8/FP4 GEMM、稀疏 attention、Sinkhorn 等参考 |
| `csa_triton_v3_yf.py`、`csa_triton_panel_yf.py` | Triton 实验 |
| `csa_optimized_yf.py` | 冻结 BF16 分派器，组合 Triton 与 CANN FIA |
| `csa_soft_row_fullcache_v2_yf.py` | 当前历史比较基线 row-v2 |
| `csa_ascendc_dense_decode_yf.py`、同名 `.cpp` | 原生批量 MXFP4 解码，衔接冻结 BF16 CSA；历史选定入口 |
| `csa_ascendc_attention_clamp_yf.cpp` | 完整融合诊断版本，正确性通过但性能不接受 |
| `native_attention_benchmark_yf.py` | 候选/参考匹配性能测试 |
| `csa_standard_benchmark_yf.py`、`csa_graph_benchmark_yf.py` | 数值和 Graph 测试 |
| `*profile_yf/`、`/root/syf/logs_yf/` | Profiler 结果和日志 |

优先读取的证据文件：

- `CSA_NATIVE_PIPELINE_REPORT_yf.md`：2026-11-03 的原生流水与低精度实验报告。
- `native_continuation_summary_yf.json`：选定入口、验收范围、硬件和性能摘要。
- `native_dense_final_status_yf.json`：历史作业完成状态。
- `native_final_codegen_yf/final_native_build_manifest_yf.json`：源和库散列清单。
- `pipeline3_triton_audit_yf.md`、`csa_native_isa_audit_yf.md`：编译/ISA 检查边界。

### 5.2 已记录的性能收益

下面引用历史报告，**本轮未重测**。候选为 `csa_ascendc_dense_decode_yf.csa`，参考为 `csa_soft_row_fullcache_v2_yf.csa`。延迟单位为微秒；加速比是 5 个 ABBA pair 的逐 pair 比值中位数。

| Case | 模式 | Reference | Candidate | 匹配加速比 |
| --- | --- | ---: | ---: | ---: |
| `d2048_h64` | eager | 217.297 | 208.806 | 1.036× |
| `d8192_h64` | eager | 263.170 | 210.143 | 1.249× |
| `d2048_b16_h64` | eager | 620.488 | 420.405 | 1.473× |
| `p2048_q128_h64` | eager | 554.484 | 440.124 | 1.262× |
| `p512_full_h64` | eager | 926.082 | 894.813 | 1.035× |
| `d8192_h64` | Graph | 242.871 | 123.387 | 1.971× |
| `p2048_q128_h64` | Graph | 516.873 | 373.015 | 1.382× |

约 3.5% 的差异在原报告中按接近处理。收益来自原生批量缓存解码加 BF16 attention，**不是原生 FP4/FP8 Cube 峰值计算的证明**。

历史验收记录包括 84 个解码 component 窗口、60,217,344 个解码元素、5 个形状 × 2 个格式 × 7 组 eager 检查，以及部分 case 的 Graph 输入更新和输出保护检查。覆盖的是既定 fixture，不是任意输入或整模型验收。

### 5.3 已知失败与经验

- Triton FP32 SSA 组装曾触发 cbuf→cbuf 编译错误；显式 UB 版本出现后端编译崩溃。
- 原生完整融合版本修复了 `CompareScalar` calCount 字节对齐问题，改用有限下界 `Maxs`；功能及 Graph 检查通过。
- 但完整融合版 Graph 延迟 Q1 约 237.4 µs、Q128 约 1751.5 µs，慢于对应 row-v2 基线约 157.6 / 581.8 µs。
- Q128 fixture 中，逐 query 解码选中槽位导致 81,920 行解码，而整个缓存只有 2,560 行，出现大量重复工作。
- 当前选定方案改为每次调用每个缓存行解码一次，再交给冻结 BF16 CSA；仍有 GM 中间张量。

结论：融合任务数更少不代表更快。V4.1 的跨层共享背景下，更要核算重复解码、共享范围和缓存生命周期，不能机械复制“整缓存每次全解码”的方案。

### 5.4 这些结果不能证明什么

历史摘要明确记录：

- `selection_scope = isolated operator evaluation`。
- `model_or_service_promoted = false`。
- `full_model_mfu_measured = false`。
- `v41_main_kv_format_validated = false`。

实验 Q、KV 和稀疏索引主要是模型尺寸的合成输入；真实 checkpoint payload 仅为 V4 layer2 的 64 个 FP32 sink，共 256 字节。实验 MXFP4 使用 E2M1 block32/E8M0，448 量化通道加 64 BF16 RoPE 通道。

因此，已有结果**不是 V4.1 模型正确性、真实缓存接入、端到端吞吐或整模型 MFU 的结果**。报告中的约 11.41% 是注意力有用 FLOP 相对估计 BF16 分母的归一化值，不是整模型 MFU；当前 die 的实测 GEMM roof 也尚未建立。

### 5.5 隔离运行环境

- `run_npu_yf.sh`：旧入口，绑定 `/dev/davinci2`。
- `run_soft_npu_yf.sh`：后续入口，绑定 `/dev/davinci13`；伙伴 die 12 有服务。
- 两者均引用固定镜像：`sha256:fe705b00b250b7b40e4103b668ed2434c9bfec257611f4a9674315223f138af3`。
- 后者限制容器内存 12G、CPU 4、禁网，适合隔离算子实验，**不是整模型部署入口**。
- host 的 `/root/syf` 映射为容器内 `/syf`；物理设备编号和容器内逻辑编号不可混淆。

运行前应重新检查入口脚本、设备空闲检查及镜像存在性。文档只记录入口，不授权直接占用设备或停止服务。

## 6. 当前缺口与下一步

### 阶段 A：固定可运行的 V4.1 基线

1. 确定使用本地 `1017-w8a8` 还是原始归档；核对配置与框架支持的精确版本。
2. 核对镜像内部模型实现、CANN、torch_npu、算子包及启动参数。已有 V4 命名镜像不等于支持 V4.1。
3. 处理原始归档 `_yf` 文件名视图，或采用可直接加载的 W8A8 目录；保留归档不动。
4. 解释 W8A8 索引大小元数据与文件总大小的差异，核对量化描述及张量格式。
5. 评估权重、Engram、KV、运行时工作区、并行布局及转换所需资源；协商可用设备窗口。
6. 在新建隔离环境做小输入文本生成，记录完整版本、启动命令和输出。不改现有服务。

**验收**：精确 checkpoint 在确定的 Ascend 环境中可加载并生成，资源占用有记录；不能仅以加载成功替代模型质量验证。

### 阶段 B：获得真实 workload 与热点

1. 记录 prefill/decode、多种输入长度和并发的端到端 TTFT、TPOT、吞吐及显存。
2. 采集实际层模式、张量形状、布局、稀疏索引和缓存更新行为。
3. 分别观察 Indexer/Top-K、KV 读取/解码、attention、MoE、通信、mHC、Engram。
4. 建立可复现的单算子/子图 fixture，保留真实格式和边界条件。

**验收**：能明确解释主瓶颈及其占比，不再仅凭 V4 合成 case 推断 V4.1 热点。

### 阶段 C：适配并评估已有工作

1. 将主 KV 格式、scale、RoPE 处理、索引语义及全 invalid 行行为与 V4.1 对齐。
2. 在真实跨层共享约束下选择解码和复用粒度；按需比较 selected 解码、整缓存解码和分块缓存复用。
3. 保留历史参考和候选，先过数值、eager、Graph 和缓存生命周期关卡，再测 ABBA 匹配延迟。
4. 集成后重新测端到端结果，验证单算子收益是否被额外转换、通信或状态维护抵消。

**验收**：明确说明适用版本、输入范围、误差和真实性能收益；没有整模型测量就不宣称整模型加速。

## 7. 工作约束

- 尊重 `/root/syf/OWNERSHIP_yf.txt`：新任务远端文件使用 `_yf` 命名，不修改已有服务或归档。
- 默认只读盘点；任何模型启动、转换、编译和 profiling 需先确认资源及输出目录。
- 不使用 V4 结果冒充 V4.1 结果，不使用软件解码后的 BF16 计算冒充原生低比特计算。
- benchmark 必须注明 reference、形状、格式、设备、环境、eager/Graph、计时方法与数值门限。
- 最终交付指标仍待进一步确定：算子延迟、端到端吞吐、长上下文成本、TTFT/TPOT 或其他目标；本文未自行承诺加速倍数。

## 8. 资料与证据入口

### 外部模型说明

- [DeepSeek-V4.1-Flash 官方模型说明](https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash/blob/main/README.md)：CED、CSA2、FP4 KV、Engram、mHC、DSpark 及参数口径。在线 main 可能变化，后续应固定 revision。

### 本轮直接读取的远端证据

- `/data2/modelzoo/DeepSeek-V4.1-Flash-1017-w8a8/config.json`
- `/data2/modelzoo/DeepSeek-V4.1-Flash-1017-w8a8/quant_model_weights.safetensors.index.json`
- `/data2/modelzoo/DeepSeek-V4.1-Flash-1017-w8a8/DeepSeek-V4.1-Flash_best_practice.yaml`
- `/root/syf/data_yf/DeepSeek-V4.1-Flash-1017-original_yf/config_yf.json`
- `/root/syf/README_v41_download_yf.txt`
- `/root/syf/v41_download_status_yf.json`
- `/root/syf/kernel_agent_v4_yf/CSA_NATIVE_PIPELINE_REPORT_yf.md`
- `/root/syf/kernel_agent_v4_yf/native_continuation_summary_yf.json`
- `/root/syf/kernel_agent_v4_yf/run_npu_yf.sh`
- `/root/syf/kernel_agent_v4_yf/run_soft_npu_yf.sh`
- `/data2/syf/DeepSeek-V4.1-Flash-1017-original_yf/inference_yf/README_yf.md`
- `/data2/syf/DeepSeek-V4.1-Flash-1017-original_yf/inference_yf/model_yf.py`

设备与空间数据来自本轮 `npu-smi info`、`docker ps/inspect`、`df -h`、`findmnt` 以及版本文件读取，均为动态快照。
