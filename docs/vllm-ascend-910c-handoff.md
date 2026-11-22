# Handoff：切换 vLLM-Ascend，先复现发布 W4A8 方案

## 从这里继续

用户最新决定：**改用 vLLM-Ascend，先复现开源方案**。此决定替代旧文档中的“最终必须用DeepInfer”和“只能官方原始FP4、不允许重量化”。优先W4路由专家，接受参考配方的W8/BF16例外。已完成首轮P0只读盘点并保存manifest，但必要资产身份未齐，**P0验收阻塞，vLLM部署尚未执行**。见 [P0 manifest与差异表](evidence/ascend910c/vllm-reproduction/p0-asset-inventory/manifest.md)。

执行顺序与验收以 [复现计划](vllm-ascend-910c-reproduction-plan.md) 为准。下一步是 **解除P0资产阻塞**：核定发布权重revision/清单/容量及发布镜像digest，再决定隔离获取；不是继续DeepInfer算子开发，也不是直接运行serve脚本。

## 当前服务：DSpark已验证运行（优先于以下历史阶段记录）

用户最新目标“支持DSpark推理并测试速度”已完成真实验收。服务保留：910c `http://127.0.0.1:18550`，model `dspark-fix-20261122T012300Z`，fullCID `7c2a3c7bf7c32ac25239f414d0392ba10e5ae711082cd4ecdac20a5afd5f42db`；TP8/EP8、SPEC1/K5、GRAPH1、MAX_LEN8192。实际draft capture和非零accepted counters已记录；主代理复核running=true/OOM=false及唯一models身份。

同短输入21 tokens/输出256 tokens，1预热+8实测：端到端中位97.1556 tok/s（87.3913–101.7041），TTFT中位248ms；原SPEC0同口径30.959，约3.14倍。草稿接受率62.57%，平均接受长度含目标token4.129。不是2048/256历史口径，不等于完整质量回归。证据 `docs/evidence/ascend910c/vllm-reproduction/dspark/dspark-fix-20261122T012300Z/RESULT.md` 及原始SSE/metrics。

本地修复 `patches/vllm_ascend_repro/dsa_v1_dspark.py` 仅删除模块级函数误用self的诊断代码，计算及shape guard未改；CPU oracle及负控通过。原ref/shared/权重不变。停止只针对上述完整CID：`ssh 910c docker stop <fullCID>`，操作前仍核归属；不要恢复旧服务或清理外部容器。旧全TODO的长针/完整DSpark质量回归等不能据此标全过。

## 早期执行进展

发布revision已锁定为 `50029772e7757c3d9cec50481661091b369af901`；全部120文件已真实hash验收，两个Engram文件已重组并独立hash复核。见 `download/recovery-3/RESULT.md` 与 `assets-final/recovery-3-*`（均在本轮证据根目录）。镜像ID已锁定为 `sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef`；前置CLI、payload导入及7类OP schema通过，见 `image/runtime/runtime_report.json`。这解除首轮资产阻塞，不是完整模型通过。

独立启动器已实际部署至 `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/deployment_yh/`，运行前置map为SPEC0/GRAPH0/MAX_LEN4096/GPU_UTIL0.85。正在执行P1真实启动；结果及任务CID以 `p1/` 实证为准，不能假定已ready。旧下载PID全部按证据已退出；禁止重启旧下载supervisor。质量门已运行前冻结到 `quality-preparation/ACCEPTANCE.md`，尚无模型质量成绩。

## P0首轮状态（历史快照）

只读采样已保存到 `docs/evidence/ascend910c/vllm-reproduction/p0-asset-inventory/`。root余4.4G、数据卷816G、data2余725G、Docker分区56G、host available980GiB；dies8–15采样时无进程，非预约。未确认目标W4A8、重组Engram、QuaRot/draft/vision及目标V4.1发布镜像；旧W8和官方FP4/FP8不能替代。目标框架/OPP身份未锁定。未下载、创建容器或修改远端。

参考核查发现88.172 tok/s属于BI实验适配器，不是发布默认配方。后续以10-04 TP8发布入口为适配复现候选，尚未锁定，不承诺历史性能。详见manifest。不要重复全量盘点代替解除具体阻塞。

## 首轮只读操作（已执行，复查时可用）

从项目根目录 `/Users/alizen/Dev/kpy_ai`：

```bash
git status --short
git -C ref/deepseek-v4.1-flash-ascend910B status --short
git -C ref/deepseek-v4.1-flash-ascend910B rev-parse HEAD
ssh -o BatchMode=yes -o ConnectTimeout=10 910c \
  'uname -m; df -h /root/yuhao; free -h; npu-smi info; docker image ls --digests --no-trunc'
```

此命令只读；缺权限不自动提权。读取参考仓库 `AGENTS.md`、`REPRO.md`、`EXPECTED_PERF.md`、`CORRECTNESS_STATUS.md` 及实际启动脚本；再按历史资产索引做有界盘点：`ref/DeepInfer/doc/ascend910c-syf-assets.md`、`ref/DeepInfer/doc/ascend910c-environment.md`。不要假定现有W8A8资产就是目标W4A8，不盲目全盘搜索。

产出P0 manifest：源码/dirty差异、镜像digest、vLLM与vLLM-Ascend版本、CANN/driver/custom OPP、目标W4A8 revision/hash、Engram重组、draft与vision资产、磁盘/host内存余量。先检查本机是否已有匹配权重，再决定下载。

## 当前已知与未知

- 参考repo：`ref/deepseek-v4.1-flash-ascend910B`，HEAD `ab88ff84efa7970875f3f8cc38dfcb06c491b154`，工作区有修改；没有锁定新部署完整manifest。
- 发布权重候选：ModelScope `chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend`。本机可用性、完整性、revision、是否对应1017尚未核定。允许采用发布量化方案，但不能将未证实的来源标成官方1017完全等价。
- 曾在现有镜像内盘点到torch2.10/torch_npu2.10及vllm_ascend扩展；仅说明资产存在，**不是配套发布服务已验收**。DeepInfer实验env则是torch2.13/torch_npu2.13rc1，不能混用证明兼容。
- 新独立工作区建议 `/root/yuhao/vllm_ascend_repro_yh`，尚未创建。新证据建议 `docs/evidence/ascend910c/vllm-reproduction/<run-id>/`，尚无部署证据。
- 最后设备实验记录均有自有容器清理证据；本次P0已重新查询服务器，采样时dies8–15无进程；**启动前必须新查**。

## 为什么暂停 DeepInfer

正确性bring-up已跑通，但大量FP4/FP8算子仍是Python分块参考路径。原decode约1180秒/forward，不是910C硬件上限。

最近真实layer30单dieFFN实验：
- 原FP4参考完整FFN中位8.950s；未校准W4A8原型2.305s。
- 独立分段：六路由专家含量化1.089ms；未替换的共享专家2.295s。
- 十二个真实GMM与有效scale oracle exact，但最终输出relativeL2约0.304，**没有质量通过**。不能将简单RTN作为发布权重。
- W4A8普通GMM ABI探针：先packed INT8做NZ再view INT32、bias=None；特定已安装路径weight scale低16位截断。仅该路径实证，不推广到vLLM融合算子。

详细背景按需读：
- `ref/DeepInfer/doc/ascend910c-fp4-performance.md`
- `ref/DeepInfer/doc/ascend910c-w4a8-prototype.md`
- `docs/evidence/ascend910c/performance/w4_real_20261121/20261121T142239534584983/`
- `docs/evidence/ascend910c/performance/grouped_probe_20261121/rounding-diagnosis.md`

DeepInfer代码、未提交改动、派生artifact及Stage5不可变证据全部保留。原Stage5 bundle不覆盖，不为回答性能问题重跑。

## 可引用的外部性能，不是本机复现成绩

参考仓库有910C八die TP8/EP8完整服务实测：2048/256串行请求，88.172 tok/s，28.634ms/step，平均接受长度2.525，TTFT均值0.322s。包含DSpark，不是普通forward耗时。见 `experiments/operator_stack/evidence/operator_revalidation_20261013/baseline2_client/RESULT.md`。

另一历史矩阵（1024/256、DRAFT_GRAPH=0）并发1/4/64聚合decode为87.1/237.7/719.5 tok/s，见 `results/bench/conc_dihuo_v8.json`。不同配置不可混比；原始token ITL并未由该表建立。8逻辑die与8物理卡不可混用。不得拿950 DeepGEMM性能或PR267离线W8A8当同口径结果。

## 必须继承的资源边界

仅SSH `910c`、授权dies8–15，fresh idle与精确设备曝光；忙则停，不操作外部容器。官方checkpoint和共享驱动/服务只读不变。新服务隔离部署、回环监听、唯一run ID、仅清理任务自有CID。禁全机page cache清理、未经审核NUMA绑定、ALLOW_BUSY绕过。大权重下载/解包先核空间与来源；需凭据/许可时向用户提出确切需求。保护dirty文件和staged gitlinks，不自动commit/reset。

## 接班时不要重复的问题

- 方案切换已由用户提出，不再要求用户重复选择DeepInfer/vLLM。
- 用户已允许调整权重，优先W4，但未批准牺牲质量。
- 当前任务是先复现成熟方案，不是继续构建自己的全模型量化器。
- 计划文档完成≠服务复现完成。每阶段用实际日志、质量结果和请求级时序验收。
