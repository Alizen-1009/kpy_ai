# P0 本地参考配方研究（只读调查结果）

## 范围和结论

本次仅读取本地参考源码、启动脚本与归档证据；未 SSH、启动服务、下载权重或实施部署。按后续授权只新增本文。远端资产核查由另一 agent 负责。

**不能把 88.172 tok/s 直接标成当前发布 `serve_a3.sh` 的复现目标。** 该数据来自固定 SDK/源快照的实验适配器，不是发布入口的默认配置；README 也明确该适配器“不是已经完成的通用发布包”。建议以 **2026-10-04 TP8 发布入口交付配方**作为第一套候选，明确冻结其显式配置，不叠加最新容量默认或 BI 实验栈。只有补齐镜像、框架和权重身份后才能称“固定配方”；目前 P0 尚不能通过。

路径约定：以下 `R/` 均为 `/Users/alizen/Dev/kpy_ai/ref/deepseek-v4.1-flash-ascend910B/`。

已阅读：`docs/vllm-ascend-910c-reproduction-plan.md`、`docs/vllm-ascend-910c-handoff.md`，以及 `R/AGENTS.md`、`R/REPRO.md`、`R/EXPECTED_PERF.md`、`R/CORRECTNESS_STATUS.md`。

本地实查 HEAD：`ab88ff84efa7970875f3f8cc38dfcb06c491b154`；`git status --short` 唯一列出 ` M experiments/upstream950/PROGRESS.md`。主代理已将 9010 个 tracked files 的 SHA256 和 dirty patch 保存至同目录 `local/`（本文未重新核验该清单内容）。HEAD 不等于工作区 manifest。

## 1. 建议候选：显式固定的 2026-10-04 TP8 配方

主依据：`R/docs/TP8-DELIVERABLE-CONFIG-20261004.md` §1、§2、§5。实际入口链：

`R/scripts/serve_a3.sh` → `R/scripts/serve_a2.sh` → 容器 `/opt/dsv41/scripts/serve_v2.sh`（源码 `R/scripts/serve_v2.sh`）。

文档原始模型位置为 `/home/l00886679/models/out/v41-flat-verify3`；这是作者路径，不证明本项目远端存在，也不证明与 ModelScope 当前 revision 逐字节相同。

候选核心配置（描述，不是已经执行的命令）：

```text
TP=8 DP=1 DEVS="8 9 10 11 12 13 14 15"
SPEC=1 SP_TOKENS=5 DRAFT_GRAPH=1 SP_SCHEDULE=<空>
MAX_SEQS=32 BAT_TOKENS=8192 PREFIX=1 GPU_UTIL=0.92
ENGRAM=1 ENGRAM_DEVICE_INDEX=0
PATCH_MODE=mount
CAPTURE_SIZES=1,2,3,4,6,12,18,24,30,36,42,48,60,72,96,192
V41_KV32_REPACK=0
PYTHON_PGO=0
```

其中 `V41_KV32_REPACK=0` 是在当前入口上显式恢复旧几何所必需：当前 `serve_a3.sh` 已改成 `BAT_TOKENS=2048 V41_KV32_REPACK=1`，不可无意识继承。旧配方文档本身未给完整版本/文件 manifest，所以以当前 HEAD 的补丁运行旧参数仍可能只是**适配复现**。

实际通用 CLI 包括 `--tensor-parallel-size 8 --enable-expert-parallel --dtype bfloat16 --kv-cache-dtype bfloat16 --quantization ascend`；主图为 `FULL_DECODE_ONLY`，DSpark 的 speculative config 使用 `method=dspark`，并未另传 draft-model 路径（draft 在同一装配 checkpoint）。见 `serve_v2.sh` 的 `ARGS`、`_spec_cfg`。

A3 基础镜像标签是 `quay.nju.edu.cn/ascend/vllm-ascend:deepseek-v4.1-flash-a3`，不是 A2 的 `dsv41-a2:v9`，也不是 REPRO 中旧的 openeuler 标签。该标签不是不可变 digest。A3 默认 `PATCH_MODE=mount`，否则官方镜像内没有本包补丁而可能静默跑错栈。

恢复投机时需完整 draft 补丁及配套 metadata/value/nctx/query-length 修复；`serve_a2.sh` 的 DRAFT-FOUR-PIECE、DRAFT-GUARD 和 `DSPARK_GRAPH_CAPTURE_METADATA` 是关键检查点。不得仅设 `DRAFT_GRAPH=1` 就宣称实际图路径已验证。

安全适配必须单列差异：回环监听、唯一 NAME/PORT/run ID、`DROPCACHE=0`、禁止 ALLOW_BUSY、审核 `CPU_BIND`。`serve_v2.sh` 默认 HOST 是 `0.0.0.0`；当前 A3 默认 `CPU_BIND=1`，不可未经审核照抄。P1 的 `SPEC=0 PREFIX=0`、短上下文、低并发属于诊断臂，不冒充上述性能配方。原始配方长上下文不属于本轮初始启动范围。

### 配套质量和性能证据

`TP8-DELIVERABLE-CONFIG-20261004.md`：1024 输入/256 输出地火口径，四轮独立运行合并中位 N=1 为 106.8 tok/s、A=2.79、26.2 ms/step；不是 2K 的 88 tok/s 基线。质量记录为 regress2 **5/6**，并发一致性 6–7/8（称仅空白差异）、144K 四针通过、1M 四针 4/4、并发双针三轮通过。**不是所有质量用例全过，也没有由该文档建立同版本 GSM/Vision 完整门。** 不把这些历史结果认作本项目实测或 SLA。

## 2. 权重及必需资产

依据：`R/REPRO.md` §1、§3；`R/quant/README.md` §1–3。

发布候选：`chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend`（ModelScope）。本地文档给下载大小 212.6 GB，但其他位置给主干 273 GB、完整加载量等不同数字；**不能据此确定发布总大小、展开大小和磁盘预算**。未访问外网，发布 revision、文件列表/哈希、官方源 revision（尤其是否 1017）仍未知。

| 资产 | 本地配方要求 | 待核验 |
|---|---|---|
| 主干 | 装配名 `v41-w4a8-engram-dr-vision-qrot-mtpq`；`quantization_config={"quant_method":"ascend","model_quant_type":"W4A8_DYNAMIC"}` | 发布具体 revision、完整分片 index/tokenizer/config 与对应哈希 |
| 混合精度 | 路由专家 W4A8_DYNAMIC；文档标签 W4A8 184320、W8A8 744±1、FLOAT 2162±40；并非全模型纯 W4 | 发布实际张量/tag 对照；shared/attention 等例外不能省略 |
| QuaRot | `optional/quarot.safetensors`，`global_rotation` F32 [5120,5120] | 旋转与主干、vision、MTP 是否同源 |
| Engram | layers 1、14 的 int8 表 + fp32 group32 scale；FP8→INT8，DR 构建；常驻 host 约 206 GiB | 发布表分片、重组后字节/哈希、实际 host 内存预算 |
| Engram 重组 | 下载后 `engram_int8/reassemble_engram_weights.sh`；两个大权重各 6 片 | 本地参考树未找到该脚本，须先读取发布包脚本再决定操作；未执行 |
| Vision | 266 张量，BF16，约 0.9705 GB；QuaRot 折叠到 aligner.w2.weight/bias、image_start/end/newline | 缺该修复历史约 10/23，修复后 23/23；不能只看有 vision 分片 |
| DSpark/MTP | 官方 MTP 反量化 BF16 阶段 1224 张量/4 分片/26.5 GiB，main_proj 预旋转后再 mtpq；补 draft 词表 | 26.5 GiB 是中间产物不是最终 draft 下载量；日志要求 loaded 74 params、无 Sharing target model embedding |
| 评测资产 | 官方 Vision23 图片、官方 encoding/chat 模板、GSM 本地 datasets 缓存；地火正文另取 | 未证实本项目已有或许可/来源已核验 |

最终结构参考 index 187226（允许 ±32）、72–87 分片；这些是重量化结构容差，不是发布身份。文档“不能用 SHA256 验收主干”只针对 DP8/DP16 **重新量化**差异，**不妨碍对固定发布文件逐字节 SHA256 冻结和传输校验**。本次不建议重量化。

若使用软链装配，需解析全部中间目录，不能只挂最终 MODEL 或 realpath。`R/tools/model_mount_args.sh` 是对应工具入口。device-index=1 需 Engram 实体 inode 可写挂载以满足 O_RDWR/MAP_SHARED 注册；代码称只读数据。候选 index0 不应因此扩大所有模型写权限。

## 3. 88.172 tok/s 实验基线的真实身份：单独保留，不混入发布配方

证据根 `R/experiments/operator_stack/evidence/operator_revalidation_20261013/`：

- `baseline2_client/RESULT.md`：2048/256，1 excluded warmup + 8 串行 measured requests；三元组 `(28.634375 ms/step, 2.524752, 88.172083 tok/s)`，TTFT mean 0.321815 s。8/8 clean 只是文本完整性，不是语义评分。
- `base2_runtime/base2_launch.sh`：实际执行 `/work/delivery_matrix_generic_20261013_v7/delivery_matrix/run_service.sh --source /work/src_dspark_general_quality_v11 ... --form a2-tp8-a3sim --max-model-len 196608 --device-index 0 --execute --physical-chips 8,9,10,11,12,13,14,15`。
- `base2_runtime/README.md`：GPU utilization=0.7、TP8/DCP1、DSpark5、async、BI、Engram host/index0；source-v11 220/220、generic-v7 36/36 哈希检查。模型 config SHA `40ebd329d3cb2d99d7176091afb580c182c21f48b88b63b550264a97e9c0d424`，不等于全部权重身份。
- Launcher SHA `ef04c733256a907c7b7fd834e0e5aba742246193dbfffcc2277ccb6a4d60cfb1`。运行 SID `3cbd844d9f684c43867b4b85c9c78ebe`；fingerprint `79513a0f20932cf696374573323b715aab0d04df774721fbee92f2f780da4319` 是 plan/config 指纹，非硬件指纹。
- 实际设置 `VLLM_BATCH_INVARIANT=1`、`HCCL_DETERMINISTIC=strict`、`DSPARK_ASYNC_SCHEDULING=1`、双流、draft graph；不能从旧发布基线默认推导这些设置。
- 必需 BI OPP：`/usr/local/Ascend/cann-9.1.0/opp/vendors/batch_invariant`。`version.info` SHA `cc3e7001ed18e748e400d78bbcd3a8c51c6d292bd7f252a3ed9c4268dc1a5371`；`op_api/lib/libcust_opapi.so` SHA `ff82d965a8a08bfa2862567022a04a1fd04df56d142f4393f1fb527592111069`。见 `base2_preflight_20261013.txt` 和 README。
- `draft_graph_evidence/README.md` 提供后续捕获日志审计入口；客户端 selector counters 本身不是每次底层 replay 回执。

README §1.2.1 明确此体系是固定 SDK/最优源快照的实验适配器，非通用发布包。历史 **A2模拟 v4** 有 GSM100 100/100、Vision23 23/23、147456针4/4、编程8题128用例全过，但 **base2 是另一实例**，不能自动继承这些质量结论。精度原件审计入口：`R/experiments/delivery_matrix/evidence/a2sim_tp8_v4/quality/strict_quality_audit.md`；本文未逐项复算其原始评分。

## 4. custom OPP 与版本边界

必须区分三种东西：

1. 发布镜像自带 vllm-ascend 算子及本包 Python 补丁：发布候选的基础依赖；精确二进制/框架 commit/digest 待核。
2. 上述实验基线的 **batch_invariant OPP**：88 tok/s 配方必需，不能凭普通 A3 镜像存在就认为具备。
3. `V41_HC_OPP_PKG`/`hcfuse_opp/vendors/custom_transformer`、`libhc_pre_norm_ops.so`、`deploy/a3-tp8-fusion/`：可选融合实验，不是默认发布必需；AGENTS 明确其中 lnorm-fusion 不发布、不建议启用。不得为追历史数字擅自加入。

`serve_a2.sh` 的 OPP-OVERRIDE 说明仅设 ASCEND_CUSTOM_OPP_PATH 可能被镜像 vendor 前插覆盖，替换算子后静态缓存也可能继续使用旧核。故身份需核对实际优先级和命中路径，不只是环境变量。

当前仅确定 A3 标签和实验路径中的 `cann-9.1.0` 字样，**不足以确立完整 CANN build/driver/torch/torch_npu/vLLM/vLLM-Ascend 兼容矩阵**。未从所读文件取得候选发布镜像 digest 或这些组件的固定版本。量化工具有独立身份：msmodelslim 基线 `92e219fa9565a5bad84d90474a27bb11524d691c`，补丁 `quant/patches/msmodelslim_v41_w4a8.patch` md5 `ff375f28e6cf5d7492e71b353d34ba5e`；它不是服务框架版本。

## 5. 质量证据不可过度外推

`CORRECTNESS_STATUS.md` 为 2026-09-16 历史记录：Vision23 23/23、GSM200 198/199/197；`HCCL_DETERMINISTIC=true` 为 91/100，明确否决。strict 不提供普遍逐位确定保证。数值 clean（重复 top1/logprob）、文本 coherent、地火完整性 clean 三种口径不同，不能替代任务质量。

`EXPECTED_PERF.md` 的 v8 并发矩阵是 1024/256、每档64请求、2rep、MAX_SEQS64/PREFIX1/DRAFT_GRAPH0/ASYNC0/无PGO；并发1/4/64总decode约87.1/237.7/719.5 tok/s。它不是 base2 的并发延伸。

文档含不同年代默认值和已更正判断：REPRO 的 KV>3Mi 被后来的 EXPECTED_PERF 修正；A3 默认 draft_graph、Engram index、BAT/repack 也已变更。因此不能把四份顶层文档拼成一个未经验证的配方。

## 6. P0 未完成项 / 交给远端核查

- 候选发布 ModelScope revision、全文件清单/总字节/哈希、官方源 revision、是否已完整下载与重组；本地引用大小不能当容量预算。
- 发布模型与 `v41-flat-verify3`、旧 qrot-mtpq 及实验 config 的身份映射。
- 镜像不可变 digest、框架 commits/dirty、CANN build、driver、torch/torch_npu 与 custom OPP 完整 manifest。
- 旧交付补丁快照是否仍可取得；当前 HEAD 是否已变化到只能做适配复现。
- draft/vision/quarot/Engram 的完整配套检查；评测数据、评分器版本及可合法使用性。
- 目标机容量、host/NUMA 内存、精确设备映射和 fresh idle：本次完全未查，由远端 agent 给证据。

**建议决策**：先冻结上述 10-04 发布入口候选及其缺口，不把“88 tok/s/BI 最优栈”纳入本次成熟发布复现承诺；若远端只有新 SDK/BI 资产而缺旧镜像，应显式改名为适配复现并重新验质量。P1 诊断臂先 SPEC0/PREFIX0；P2 通过独立质量门后再恢复固定 DSpark5 配置。没有完整身份与质量证据之前，不宣布配方锁定或 P0/P2 已通过。
