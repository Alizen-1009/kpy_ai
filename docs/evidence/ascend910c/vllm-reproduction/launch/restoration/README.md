# P2 分步恢复输入（仅本地生成，未启动）

锁定 reference HEAD `ab88ff84efa7970875f3f8cc38dfcb06c491b154`；镜像 ID、基础 map/report 哈希见两个 variant 的 provenance。没有修改原 map、源码、现有服务；没有 SSH。`build.py` 可本地重复生成，且断言三个 draft payload 字节等于 HEAD。

## 下一轮：GRAPH1 / SPEC0

使用 `graph-runtime-map.json`，selected mounts 与当前 map 完全相同，**额外 payload 为零**。只变 GRAPH=1、EAGER=0、CAPTURE_SIZES=1；SPEC=0、index=0、MAX_SEQS=1、MAX_LEN=4096、GPU_UTIL=.85 保留。DRAFT_GRAPH=0 与 capture metadata=0 显式固定。serve_v2 生成 FULL_DECODE_ONLY，无 enforce-eager，无 speculative-config。NPUGRAPH_EX=0、STATIC_KERNEL=0 和所有融合关闭，不能偷偷恢复 A3 默认。

这不是把 Engram device-index 恢复为 1：后者需要两个额外模块、host_register 及 Engram 表最终 inode 可写，非本阶段最小变更。当前 host-resident 图输入已有固定镜像 worker 在 capture/replay 前刷新：`model_runner_v1.py.source:2985-2989` 调用三参 prepare_engram；Vision wrapper 与 payload 两层同签名，见 `graph-interface-audit.json`。未发现这一接缝必须先修的实质不兼容，不需要换 worker 或新 main。

## 后续：DSpark5 / DRAFT_GRAPH1

`dspark-runtime-map.json` 是完整独立 map，不是会重复 mount 的叠加片段。新增两文件 spec_decode/{dspark_proposer,llm_base_proposer}.py；attention/dsa_v1.py 替换为 draft 版（同 destination 只保留一条）。每条 source/destination/SHA256 在 additional_payloads 和 mounts 中，均只读。无需动态推测 patch_cudagraph；SP_SCHEDULE 保持空。

新增 env：SPEC=1、SP_TOKENS=5、SPEC_EAGER=0、DRAFT_GRAPH=1；DSPARK_GRAPH_CAPTURE_METADATA=1、DSPARK_DRAFT_USE_CUDAGRAPH=1、DSPARK_DRAFT_METADATA_MODE=sync，以及 CAPTURE_VALUE_FIX/SWA_INDICES_RESIDENT/CAPTURE_NCTX_FIX/DISPATCH_QUERY_LEN_FIX 四个 DSPARK 开关全部为 1。禁运行时 flags 与 device metadata。serve_v2 本身不解释 DRAFT_GRAPH，真正有效的是上述 explicit SPEC_EAGER 与 DSPARK 环境，因此不能只设外层开关。

逐个 from-import 的模块、符号、行号及供应者在 `import-audit.json`；三个 payload 之间依赖由本 variant 供应，forward context/rope 由已选基础 payload 供应。torch/torch_npu/vllm 及其他 ascend 依赖预期来自固定镜像，不新增包。**未捕获源码的依赖不冒称已验证**：尤其 dflash_proposer、spec_decode/utils、triton spec decode utils 的接口，本地 image/runtime 未包含这些文件，必须从同一镜像补齐离线捕获或下一轮受控 preflight 验证，不能换新 main 来填缺口。

已核对具体 runner→draft 接缝：固定镜像 worker:4216-4225 将 block sizes 归一为 list[int]，调用 initialize_attn_backend(config, sizes)；draft:312 接收同参数并按 gid 取 int。此处没有必须先修的签名不兼容。尚不能据此宣称全部 DSpark 依赖闭合，DSpark 执行门保持未通过。GRAPH0 服务成功不是 draft 图可用证据。

## 尺寸差异与 guard

本轮低并发：graph SPEC0 只捕获 1；DSpark5 捕获 1,2,3,4,6，MAX_SEQS=1，覆盖单请求 6-token verification 与较小 draft 桶。这是受控启动候选，不是已经实机证明安全。

serve_a2:931-974 当前 HEAD 的完整默认（K5/MAX_SEQS32）为 `1,2,3,4,6,12,18,24,30,36,42,48,60,72,96,192`；MAX_SEQS1 默认仍强制至少 32，为 `1,2,3,4,6,12,18,24,30,32`。不要把旧注释中的几何表误作现行生成结果。我们主动缩小尺寸、并发、上下文，且关闭 device-index/融合/静态核等，**后续性能不是同配置严格复现**。

serve_a2:1940-1950 原 guard 仅检查 live dspark_proposer 含 DSPARK_GRAPH_CAPTURE_METADATA 且容器变量=1；本次绕过外层脚本，需在下一轮显式执行等价检查，并逐文件核对三个 SHA。四件套来源 serve_a2:1504-1512；SPEC_EAGER 翻转来源 :1984。原 guard 不能替代 import/真实生成验证。

官方 tools/draft_graph_guard.sh 采用 concurrency=1,2,4,8 得到 conc1 八发中位，不能在 MAX_SEQS1 的首轮宣称完整执行同配置 guard：先八次串行质量/接受长度检查；扩到 MAX_SEQS8 并补齐至少 1,2,3,4,6,12,18,24,30,36,42,48 后再执行正式 guard。A>=1.3，连续两次 A=1 且 accepted throughput=0 为失败；必须同时看文本质量与 (ms/step,A,tok/s)。

## 验证门 / 放行边界

1. 保留原 image/runtime/runtime_report.json 为前置证据；两份 variant 的 runtime_report=null，不能复制 true。原报告哈希绑定旧 map，不认证新图路径。
2. 下一轮先完成 Code8 任务并获得明确资源/服务切换许可；这次不碰它。
3. 逐项 hash、隔离 env、确认真实 image ID/CANN、CLI JSON，先 graph SPEC0；观察真实 capture 和 replay，不能以 fallback eager 当成功。
4. 小请求/GSM/Vision/Code 回归后再 DSpark；DSpark 先补上述缺失的固定镜像 import 证据及运行 preflight，再真实权重启动与接受长度 guard。
5. 任何新增 variant 的运行报告必须单独绑定其 map 哈希，记录 actual argv、env、所有 selected destination hashes、日志和质量结果。

结论：已核对的主图 Engram 接缝及 DSpark block-size 接缝没有发现必须先修的实质 compatibility；DSpark 尚有本地捕获缺口，是放行前证据门，不应虚构成确定代码错误，也不能直接当作通过。
