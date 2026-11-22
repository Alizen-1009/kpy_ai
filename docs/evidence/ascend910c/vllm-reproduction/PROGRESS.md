# 部署执行状态

## 已实际执行

- 固定发布revision `50029772e7757c3d9cec50481661091b369af901`；120文件、525795307321 bytes。元数据和13个小文件已hash核验。
- 已创建隔离数据目录 `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh`，未覆盖官方checkpoint或DeepInfer。
- 下载已启动；初次因CDN重定向失败。增加精确HTTPS `cdn-lfs-cn-1.modelscope.cn`白名单并通过14测试后重启。PID2207298，身份及日志见download/。最新快照首个LFS `engram_extra.safetensors` 629310402 bytes已hash通过，正在下载Engram scale；不是全部完成。
- arm64镜像child digest `sha256:16a57b897a2f475f85b0e90df1644c9870c2418b368b2adf447c5173eae211c3` 已验证，实际pull PID2206757仍运行。仅获取镜像，不创建容器。image/内保存日志及容量保护。
- 下载器及容器gate合计23测试通过；启动参数检查6测试通过；Engram重组12小fixture测试通过。均不是模型验收。

## 实施路线

原serve_a2动态挂载和清理存在安全风险，不直接执行。最小SPEC0/GRAPH0运行映射已冻结到launch/runtime-map.json，包含10个Python payload和serve_v2脚本的hash。独立launcher实现中；此前prepare_launch.py只是参数检查，不能作为已实现启动器。

## 尚未完成

- 全部120文件下载与hash验收；两个Engram目标实际重组及独立hash。
- 镜像pull完成、image ID及内部框架/SDK/OPP身份核验。
- 独立launcher审查/测试及真实设备、容器、监听检查。
- P1真实生成、P2质量门、P3服务性能、P4归档及任务资源清理。

正在运行的下载/pull是任务自有资源，不能标成已清理。进程存在及容量均是瞬时快照，后续先核对PID start_ticks/任务日志，禁止按模糊名称停止进程。不使用GOAL_COMPLETE，P0仍未通过。
