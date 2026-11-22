# kpy_ai 工作区快照

本次提交收录主仓库其余未忽略的实验文档、原始证据、评测脚本与数据，并更新嵌套仓库gitlink。未提交缓存、.git内部数据或忽略文件。归档后已获授权发布到GitHub；子仓库先推送，随后推送主仓库。

## 嵌套仓库

- `ref/DeepInfer`：本地提交 `d4420f9` 保存官方runtime、量化/性能实验及证据。主仓库记录该gitlink，已推送到 `Alizen-1009/DeepInfer` 的 `feat/ascend910c-official-fp4` 分支。
- `ref/DeepInfer-ascend910c-pr267`：记录现有commit，无工作区修改。
- `ref/deepseek-v4.1-flash-ascend910B`：已通过 `4647bd6` 和 `cc77187` 解决macOS大小写文件名冲突。原 `experiments/upstream950/PROGRESS.md` 无损更名为 `PROGRESS-detailed.md`，小写 `progress.md` 保持原样；两个版本内容均逐字节保留。同步README链接，并从已提交HEAD计算对应MANIFEST条目。只改文档路径与校验清单，不改模型/部署代码。

补齐 `.gitmodules` 映射，不改变嵌套仓库结构。两个有新提交的子仓库均已推送。参考仓库现指向私有副本 `Alizen-1009/deepseek-v4.1-flash-ascend910B`（main：cc77187），原 `chiro2001` 仓库保留为本地 `upstream`。这是保留main完整祖先历史的私有副本，不是GitHub公开fork网络成员。拉取该私有子仓库需要相应账号权限；可用 `git submodule update --init --recursive` 获取所固定版本。

## 大文件

超过100MiB的profiler trace保存为同目录 `trace_view.json.gz`，原JSON不删除并通过精确路径忽略。压缩前和解压后的SHA256一致：

`976789bfebe77deef2a006199680fa5d563e0650210e9a5f2f6a813276d38b3f`

路径：`docs/evidence/ascend910c/performance/stage5_moe_batch_die8_20261121T130159252432753_yh/trace/b06d856cb3a7_1_20261121050220023_ascend_pt/ASCEND_PROFILER_OUTPUT/trace_view.json.gz`。

可在需要时使用 `gzip -dk trace_view.json.gz` 恢复（若原文件已在则无需操作）。原始日志中的空白/失败输出保留，不为了格式检查而改写证据。

本次是工作区归档，不表示旧DeepInfer全部实验已重新执行或通过。vLLM工具此前60项测试通过，DSpark实测详见 `vllm-ascend-experiment-results.md`。
