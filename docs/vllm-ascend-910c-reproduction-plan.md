# vLLM-Ascend / 910C W4A8 复现计划

## 决定与范围

用户最新决定：主线切换为 **vLLM-Ascend，先复现成熟开源方案**；允许派生/第三方量化权重，优先 W4，接受参考配方中 shared/attention 的 W8A8 或 BF16 例外。DeepInfer 暂停新增优化，不删除代码、权重、未提交改动或证据。是否将结果迁回 DeepInfer，留待复现完成后另行决定，不是本计划验收条件。

最新状态：已完成首轮P0只读盘点，必要资产未齐，P0验收阻塞；尚未启动 vLLM 服务、下载发布权重或完成复现。见 [P0 manifest与差异表](evidence/ascend910c/vllm-reproduction/p0-asset-inventory/manifest.md) 和 [handoff](vllm-ascend-910c-handoff.md)。

**目标**：在授权 910C dies8–15 上建立可复现、质量有证据、性能口径明确的 DeepSeek-V4.1-Flash W4A8 服务。先单实例 TP8/EP8，不做 PD/CED、DCP、DP 多副本、1M 上下文、自研算子或全模型自重量化。

## 参考与不可混淆的基线

- 本地参考：`ref/deepseek-v4.1-flash-ascend910B`，HEAD `ab88ff84efa7970875f3f8cc38dfcb06c491b154`。工作区有改动：HEAD 不代表全部实际文件，冻结时须记录 dirty patch 和文件 manifest，不 reset/stash 用户工作。
- 上游：https://github.com/chiro2001/deepseek-v4.1-flash-ascend910B 。先读其 `AGENTS.md`、`REPRO.md`、`EXPECTED_PERF.md`、`CORRECTNESS_STATUS.md` 及实际选用启动脚本。
- 发布权重候选：ModelScope `chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend`。尚未确认本机已有完整副本、发布 revision/hash、来源官方 revision及 Engram 重组状态。不能默认它严格等同官方1017。
- 优先选一套**有对应证据的固定发布配方**，冻结框架 commits、补丁、自定义OPP、镜像digest、CANN/driver/torch_npu、权重revision/hash。不能混合历史镜像、最新main补丁和另一组DSpark配置。
- 参考单流：8 die TP8/EP8，2048输入/256输出，28.634375 ms/step、接受长度2.524752、88.172083 decode tok/s、TTFT均值0.321815s。包含投机解码，来源参考仓库 `experiments/operator_stack/evidence/operator_revalidation_20261013/baseline2_client/RESULT.md`。
- 另一历史矩阵：1024输入/256输出，64请求/档、2rep、DRAFT_GRAPH=0；并发1/4/64聚合decode约87.1/237.7/719.5 tok/s。来源 `results/bench/conc_dihuo_v8.json`。不是上一单流配方的并发延伸；不拿峰值110或950内核数字当承诺。
- 以上为作者归档数据，非本项目独立复现。8个910C逻辑die按该设备映射为4张双die物理卡；启动前核实目标映射。

## 阶段与验收门

### P0 — 只读盘点、锁定复现配方

**状态：盘点结束，验收未通过。** 已归档源码dirty/hash、远端资源/镜像/已知模型证据；目标发布W4A8及配套资产、镜像/框架/OPP身份和下载容量尚未核定。候选改为明确的10-04 TP8发布入口适配复现，尚未锁定；88.172 tok/s属于另一BI实验适配器，不作为该发布候选的同配置基线。下面各项保留未勾选，避免将部分盘点误标为完整通过。

- [ ] 记录本地/远端源码状态；盘点授权工作区及已知权重位置、镜像、扩展、版本、磁盘容量和NUMA内存。不要全盘扫描其他用户数据。
- [ ] 查找可复用的发布W4A8权重，验证分片、config/tokenizer、量化配置、Engram及draft/vision资产是否配套；读取权重下载/重组脚本后再执行。
- [ ] 若需下载，先记录目标revision、预估磁盘和缓存/重组额外空间；使用隔离目录，不覆盖官方checkpoint。凭据/许可/容量不足则报告具体阻塞。
- [ ] 选定一个发布配置，产出manifest与差异表。若缺旧镜像/OPP等关键依赖，标记“适配复现”而非严格同配置复现。

**通过条件**：每个必要资产有位置、身份及可用性证据；明确全部未知项和所选精度/投机策略。无需占NPU。

### P1 — 隔离部署与启动门

- [ ] 在任务自有工作区创建容器/源码副本，复用经过核验的镜像和配方；dry-run检查展开后的完整命令、挂载、环境和设备。
- [ ] 初始正确性基线显式关闭投机与前缀缓存，短上下文、低并发；这是诊断配置，不用于宣称复现88 tok/s。
- [ ] 审核与继承fresh-idle、精确dies8–15曝光、无shared改动、CPU_BIND/DROPCACHE安全约束；禁止照抄ALLOW_BUSY或全机清缓存。
- [ ] 本地回环地址起服务，绑定唯一run ID，验证实际8rank/设备、量化算子、完整模型ready、健康请求、无静默fallback和OOM。记录峰值设备/host内存。

**通过条件**：真实生成成功且运行身份、模型、算子与资源匹配；容器running或HTTP200本身不够。失败只清理本任务资源。

### P2 — 质量基线与参考配置恢复

- [ ] 检查多轮/中文/代码等基础生成，再按参考冻结评分器做可取得且合法使用的GSM、编程、Vision及长针测试；测试语料未随包分发时明确获取来源。
- [ ] 区分已有发布成绩与本次实测，不以文本clean、一次token或者局部cosine通过质量门。
- [ ] 逐项恢复所选参考的DSpark/draft graph、Engram和其他设置；每次确认实际路径、模型资产及正确性。不要将RTN实验权重冒充发布量化权重。

**通过条件**：所选参考配置有对应质量结果和预先定义的评分门；未完成项明确列出。失败配置不得标“复现完成”。

### P3 — 同口径服务性能

- [ ] 先测单流，固定prompt/output长度、seed、投机、缓存、预热与采样规则；确保完整输出长度，保存请求级时序、usage及错误。
- [ ] 对齐选定参考的输入/并发；若原始语料不可用，明确只是同形状复现。
- [ ] 报告端到端output TPS、decode TPS、requests/s、TTFT p50/p95、实测token/chunk间隔（SSE块不能冒充token ITL）、失败率、峰值内存。
- [ ] 开投机时同时报告ms/step、实际接受长度A、实际输出tok/s；禁止假设全部草稿接受来计算TPS。
- [ ] 再扩并发1/4/8，资源允许再16/32/64；逐档质量/稳定性检查。128K、1M另设门，不为短流吞吐占用全部容量。

**通过条件**：独立可重跑的原始请求证据及汇总；与参考逐项列差异、速度差和误差区间。未预先约定性能容差时，只报告差距，不自行宣布“达到开源水平”。单流约88–90 tok/s是条件相关参照，不是硬件保底或SLA。

### P4 — 固化交付

- [ ] 固定启动/停止/复测命令及全部manifest；保存证据到 `docs/evidence/ascend910c/vllm-reproduction/<run-id>/`。
- [ ] 明确最终服务是否保留、容器ID/端口/设备owner；测试结束默认清理本任务容器，若用户要求保留则记录生命周期与停止方法。
- [ ] 更新handoff及状态索引，包含失败史、质量限制与未完成项。

**完成定义**：P0–P4均有实际证据，所选质量门通过、同口径服务测速完成、版本可重现、资源有明确归属。任何新scope（迁回DeepInfer、扩卡、全模型重新量化）另行决定。

## 操作边界

SSH别名 `910c`。延续仅dies8–15授权，每次设备任务前fresh idle检查；忙则暂停，不终止外部任务。原始checkpoint、共享驱动/服务/环境保持不变；只使用隔离副本和任务自有容器。已知DeepInfer工作区 `/root/yuhao/deepinfer_910c_yh` 是历史资产，不作为新方案默认覆盖目录。新工作区建议 `/root/yuhao/vllm_ascend_repro_yh`，**尚未创建**。不要在文档中保存凭据。未经请求不提交git、不处理无关dirty/gitlink。
