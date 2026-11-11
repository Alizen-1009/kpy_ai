# 参考仓库

| 目录 | 用途 |
| --- | --- |
| `DeepInfer/` | Alizen-1009/DeepInfer 工作 fork；本项目执行框架与移植修改主体。 |
| `deepseek-v4.1-flash-ascend910B/` | 910B/910C 算子、移植和测试参考；不是本项目执行框架。 |
| `DeepInfer-ascend910c-pr267/` | 上游 [PR #267](https://github.com/deepseek-ai/DeepInfer/pull/267) 的实验性 Ascend 910C 离线推理参考副本。 |

## PR #267 固定快照

- 来源：`https://github.com/deepseek-ai/DeepInfer.git`，`refs/pull/267/head`。
- 提交：`7c67f0617044ff416e63db73fe772e818a552a90`。
- 采用 shallow fetch、detached HEAD；未初始化 vendor 子模块，未运行构建或推理。
- 该路径使用 DeepInfer 执行模型，专用离线入口要求 ModelSlim 动态 W8A8；通用 loader 仍有原始 FP8/FP4 分支，且已有独立解码/参考 GEMM，但官方权重的完整 910C 执行路径仍有阻塞。作者提供了 12 个逻辑 NPU 的生成测试记录，尚未由本项目独立复现。
- 复用矩阵、官方 header 差异及本项目 CPU 检查见 [PR267 复用审阅](DeepInfer/doc/ascend910c-pr267-reuse.md)。
- 本项目仍要求官方 `deepseek-ai/DeepSeek-V4.1-Flash-1017` 原始 checkpoint 不变；参考该 PR 不代表改用 W8A8，也不代表官方原始权重已获 910C 支持。
- 本副本不替换 `DeepInfer/` 工作 fork；后续移植应按固定提交审阅与挑选，不直接覆盖现有代码。
