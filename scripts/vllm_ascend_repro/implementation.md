# P1 prepare_launch：部分实现，BLOCKED

已完整阅读 reference AGENTS.md 与 2270 行 serve_a2.sh，以及 launch-safety-review.md。
没有修改 reference、container_gate 或下载器；没有执行 SSH、Docker、NPU 或原 DRY_RUN。

实现了可运行的离线拒绝门：默认仅输出 JSON，所有四个路径/身份参数显式提供，拒绝可变镜像标签、不安全关键环境覆盖、已有目标、软链祖先、非调用者所有或组/全局可写的目标父目录。记录审核输入 SHA256，列出拟用环境白名单、模型及不可变镜像参数。默认与 --prepare 均返回 2，且不创建任何文件。digest 格式不是 arm64 child 身份证明。

## 明确未实现（不可当安全启动副本交付）

没有复制冻结树，没有生成或声称安全 diff，没有启动路径。完整冻结清单核验尚未实现。未逐项实现 privileged 删除、宿主与 payload ro 改写、按 NAME 清理删除、dropcache 分支删除、loader 强制值删除、任务目录写入重定向、环境封闭。所列白名单只是拟定值，不是已经施加到 shell 的安全控制。

停止原因是脚本不仅包含 Docker 参数：603–884 行动态软链发现决定最终模型挂载，1680–1707 行 admission patch 失败继续且缺应用前后 hash，1995–2034 行生成未引用 heredoc 并调用 serve_v2.sh。只改字符串和默认环境无法证明上述执行链安全；需要独立审完 helper/serve_v2 与闭合挂载清单、补丁 hash 契约，再进行精确变换。1529–1656 行创建结果丢弃且后续按 NAME 操作，外层 CID 交接也没有在本工具假装实现。

因此未提供“生成副本 bash -n/危险命令消除通过”的测试：没有安全副本可测，拿原脚本或不可运行包装器通过语法检查会造成虚假验收。当前测试只验证离线拒绝门及无目标写入。

## 仍需 runtime 验收

即使未来静态修补完成，仍需独立验证 child digest/arm64、冻结模型与补丁身份、fresh idle/设备映射与租约、非特权兼容性、实际 HostConfig/Devices/最深 Mounts 只读、控制设备隔离能力、所有监听归属与回环限制、精确 CID 所有权、权重加载与补丁命中、内存预算与 KV32 块数、唯一 served model 和真实生成。失败仅报告，清理由外层核验完整 CID 后处理，不得按 NAME 删除。
