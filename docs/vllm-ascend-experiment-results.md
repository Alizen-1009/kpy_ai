# 910C vLLM-Ascend 实验结果快照

## 本次提交范围

提交当前DSpark成功实验的完整小型证据目录、SPEC0测速原始记录、阶段结果摘要，以及隔离部署工具/测试和最小DSpark修复。不提交权重、下载的大型模型索引/描述、缓存、旧DeepInfer实验或预先暂存的gitlink。其余历史原始证据仍在工作区，本文及交接中的某些历史链接可能尚未纳入本次提交。

## 固定资产

- 模型：ModelScope `chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend`，revision `50029772e7757c3d9cec50481661091b369af901`。
- 混合W4A8：路由专家W4A8_DYNAMIC，其余按发布配方保留W8/BF16；不是自重量化，也未证明与官方1017严格等价。
- 全部120发布文件hash验收，两个Engram目标重组后独立hash通过。
- 镜像ID：`sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef`。
- vLLM HEAD `6e448d0ea9bf3d88d898b65449ca6dc2aec170ac`；vLLM-Ascend HEAD `e43cf1e9f5d9bead076853aa6bcacb671465de94`；CANN9.1.0、torch2.10.0+cpu、torch_npu2.10.0.post4。

## 已实测

| 配置 | 结果 | 限制 |
|---|---|---|
| GRAPH1 / SPEC0 | 30.959 tok/s，3次实测 | 短输入21/输出256；含TTFT |
| GRAPH1 / DSpark5 | 97.156 tok/s，8次实测，87.391–101.704 | 同短输入/输出口径，非2048/256参考基准 |
| DSpark5 | TTFT中位248ms；草稿接受率62.57%，含目标token接受长度4.129 | 无独立kernel step时延 |
| GRAPH1 / SPEC0质量 | GSM198/200、Code128/128、Vision23/23 | GSM仍1次length；不能标完整质量门通过 |
| DSpark5质量 | 中文、多轮、完整短代码生成成功 | 有界smoke，不等于完整质量回归 |

DSpark相对SPEC0端到端输出速度约3.14倍。两者都是串行、temperature0、固定输出256；强制length结束仅用于吞吐测试，不能混入质量评测。

## 修复与失败记录

- VISION0导致视觉参数未实例化而strict loader仍加载；最终采用VISION1/MM_LIMIT_IMAGES1，未丢弃视觉权重。
- DSpark参考补丁模块级函数错误访问self；独立副本仅删除诊断字段引用，保留tensor计算及shape检查，CPU oracle/负控通过。
- 下载遇提前EOF后采用有界Range续传，最终全hash通过；未将partial当完整文件。

## 证据入口

- 当前成功run：`evidence/ascend910c/vllm-reproduction/dspark/dspark-fix-20261122T012300Z/RESULT.md`；同目录含原始SSE、metrics前后、inspect、实际配置、代码diff和CPU测试。
- SPEC0基线：`evidence/ascend910c/vllm-reproduction/current-tps.jsonl`。
- 交接：`vllm-ascend-910c-handoff.md`。

服务器工作区 `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/`；成功环境 `deployment_dspark_fix_yh/`，模型目录 `model/`。成功服务在提交前核查仍运行，回环18550，model `dspark-fix-20261122T012300Z`。运行状态是时间快照，不是永久承诺。
