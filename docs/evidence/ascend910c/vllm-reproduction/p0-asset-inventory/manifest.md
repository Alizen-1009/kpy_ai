# P0 manifest 与差异表

## 判定

**只读盘点已结束；P0 验收 BLOCKED，未进入 P1。** 远端采样起点 UTC 2026-11-21 06:41:02。本目录名为证据批次 ID，不是服务 run ID；未创建远端工作区或容器、未下载、未占用 NPU。全部结论限于索引指向的有界盘点范围，不能推断全机不存在目标资产。

## 源码与证据身份

- 本地参考 HEAD `ab88ff84efa7970875f3f8cc38dfcb06c491b154`；dirty 文件 `experiments/upstream950/PROGRESS.md`。
- `local/` 保存项目及参考状态、staged/unstaged patch、参考 untracked 清单及 9010 个 tracked 文件的 SHA256。未 commit/reset/stash，保留既有 staged gitlinks。
- [参考研究](reference-summary.md)：入口、所需资产、质量与性能口径及确切源文件。
- [远端总结](remote/remote-summary.md)：资产路径、身份、限制。`remote/` 内三个输入脚本及 stdout/stderr 为原始证据。首次查询部分失败已记录并用 sysfs/完整镜像名补查，不将失败输出当作资产不存在的充分证据。

## 候选配方（尚未锁定）

选用 **2026-10-04 TP8 发布入口**作为后续补齐资产的候选，不采用 88.172 tok/s 的 BI 实验适配器。入口 `scripts/serve_a3.sh → serve_a2.sh → serve_v2.sh`。旧补丁快照与当前 HEAD 的身份映射未完成，因此目前只能规划为**适配复现候选**，不能宣布严格同配置复现。

恢复臂：TP8/EP8、DP1、dies8–15、BF16 activation/KV、ascend 混合 W4A8_DYNAMIC（允许配方的 W8/BF16 例外）；DSpark5、DRAFT_GRAPH=1、PREFIX=1、MAX_SEQS=32、BAT_TOKENS=8192、GPU_UTIL=0.92、ENGRAM=1/index0、PATCH_MODE=mount、V41_KV32_REPACK=0、PYTHON_PGO=0。完整捕获尺寸和来源见参考研究。P1 诊断臂另设 SPEC=0/PREFIX=0、短上下文低并发。

任何启动脚本均需隔离改造：HOST=127.0.0.1、唯一任务身份、DROPCACHE=0、不使用 ALLOW_BUSY、不继承未经审核的 CPU_BIND。这里不是可直接执行的启动命令。

## 必要资产与差异

| 必要项 | 当前证据 | 判定 |
|---|---|---|
| 发布 W4A8 checkpoint | ModelScope 候选 `chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend`；未核实发布 revision/全文件 hash/总字节/官方源 revision | 阻塞；不能标为官方1017等价 |
| 本机目标权重 | 有界盘点仅确认官方1017 FP4/FP8及旧V4 W8A8，不满足目标身份 | 阻塞；不是宣称全机没有 |
| Engram int8 DR 重组 | 发布脚本及最终文件未核实 | 阻塞；不得执行未审阅重组脚本 |
| QuaRot/draft/vision | 原始官方相关键不证明发布配套；目标装配未确认 | 阻塞 |
| 发布 A3 镜像 | 期望标签 `quay.nju.edu.cn/ascend/vllm-ascend:deepseek-v4.1-flash-a3` 未出现在镜像清单 | digest及内容身份未锁定 |
| 现有镜像 | 旧V4 ID `fe705b00b250b7b40e4103b668ed2434c9bfec257611f4a9674315223f138af3`；v0.30 ID `77aea90962507771cfaf5304c926ee3f3539907eb59d37edb560177e7e7b4033` | 均不能直接冒充目标镜像；旧镜像 RepoDigest 见远端总结 |
| vLLM/vLLM-Ascend/torch_npu/CANN/OPP | 没有目标服务框架固定 commits 与完整二进制 manifest；未新建容器核验内部包 | 阻塞；历史包版本不作 fresh 验收 |
| 宿主 | driver25.5.1、toolkit8.5.0 | 已盘点，不代表目标容器兼容已通过 |
| 设备 | dies8–15映射物理NPU4–7，采样时无进程 | 已盘点；启动前重新检查，不是预留 |
| 存储 | root4.4G、数据卷816G、data2 725G、Docker分区56G可用 | 禁root下载；未通过容量门 |
| host/NUMA | available980GiB；四NUMA节点详细数据已归档 | 瞬时余量，非承诺；不自动绑核 |
| 评分与语料 | 参考历史不同版本各有结果，未绑定本次模型/评分器/语料 | P2门待定义，不能继承历史通过 |

官方1017视图48/48分片引用可解析、原归档inventory84/84文件大小匹配；只重新hash小元数据，**未重算权重payload**。旧W8资产不能替代发布W4A8。

## 性能口径修正

- 88.172 tok/s 是 2048/256 的 BI/DSpark 实验适配器证据，需要独立源快照和 batch_invariant OPP，非发布默认配置。
- 10-04候选历史为1024/256，单流多轮中位106.8 tok/s；历史 regress2 为5/6，并非全质量通过。该数值不成为本机承诺或自动验收门。
- 当前A3默认 BAT_TOKENS=2048、KV32_REPACK=1 与旧配方不同，不能隐式继承后宣称严格复现。

## 解除阻塞顺序

1. 只读查询发布模型及镜像来源，取得固定 revision/digest、完整文件清单/大小/哈希及可用性；目前未访问发布站点，不能将“未核定”写成“不可获取”。
2. 根据真实清单计算下载缓存、最终文件、Engram重组临时副本和保留空间；选任务自有数据卷目录，禁止root落大文件。镜像需单独核算Docker空间。
3. 审阅下载和重组脚本，确认凭据/许可需求。若确需下载，在上述门通过后按原计划隔离获取，禁止覆盖官方归档或共享环境。
4. 校验目标分片、tokenizer/config、量化配置及全部配套资产；绑定框架、SDK、OPP及补丁。取得所有必要资产证据后重新判P0。

**本次交付是可审计的 P0 盘点和阻塞清单，不是已完成部署前置验收。**
