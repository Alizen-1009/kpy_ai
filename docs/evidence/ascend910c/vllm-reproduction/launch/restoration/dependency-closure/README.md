# 固定镜像 DSpark 依赖捕获（静态，未放行）

执行 `python3 capture.py`、`python3 check.py` 可重现。未运行 torch、模型、NPU；未启动、停止或重启任何容器，未挂载文件至活跃服务，未触碰 8192 质量评测。没有准备远端 payload 副本。

## 来源

实时 inspect 确认完整 CID `67993945c3595dc9bc76bbddc429c2c4d7d49be7cadd5b3d4b1bdbd7795e3525` 为 exited、Running=false、Pid=0，与历史任务 create-inspect ID/image 相同。固定 image `sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef`。通过 docker cp 的 tar stdout 精确捕获三个文件，无远端临时文件；不需要创建备用容器。每个路径均不在该容器 bind mount 下。`inspect.json` 保存来源；`sources.json` 绑定 image/CID/路径/SHA256。注意：这是该停止容器的非挂载文件证据，不是与 pristine image 层逐字节比对的证明。

## 结果与边界

补齐 `spec_decode/dflash_proposer.py`、`spec_decode/utils.py`、`ops/triton/spec_decode/utils.py`。三个 draft 输入逐字节匹配锁定 HEAD `ab88ff84efa7970875f3f8cc38dfcb06c491b154` 与 map SHA。

`ast-report.json` 列出这些模块中每个直接 from-import 的八个符号、调用与 context 字段。类构造函数和普通函数/Triton kernel 调用按 AST 提取签名、用标准库 Signature.bind 检查位置/关键字/必需参数。该有限检查未发现缺符号或参数绑定 blocking mismatch。不是全依赖闭包证明：未检查所有间接 import、动态属性、继承方法、装饰器行为、张量形状或 device metadata 语义；context 条目仅为字段清单。类继承可解析并不证明其初始化副作用兼容。

尤其停止镜像 dflash 在 FULL 路径读取 `_EXTRA_CTX.capturing`，draft 读取 `forward_context.capturing`、`cudagraph_runtime_mode`、`attn_metadata`。所选 ascend_forward_context payload 的代理声明 capturing，且初始化 forward_context.capturing=False；仍需验证实际 context 生命周期、图 capture/replay 时值与 metadata 对齐，不能把字段文本存在当 runtime 验证。

## 下一步具体 guard（仍需服务切换授权）

1. 8192 评测结束并获明确资源许可前，不执行运行 preflight/设备图启动。维持 DSpark runtime gate 未通过。
2. 核对实际 image ID、CANN、全部 selected mount SHA、三个 draft HEAD 字节；独立 task payload 路径只读挂载，不覆盖现有 payload。
3. 先 GRAPH1/SPEC0，MAX_SEQS1/MAX_LEN4096、capture=1；检查真实 capture/replay、禁止 eager fallback 冒充成功。
4. DSpark K5：capture=1,2,3,4,6；SPEC_EAGER=0，DSPARK_GRAPH_CAPTURE_METADATA=1、DSPARK_DRAFT_USE_CUDAGRAPH=1、DSPARK_DRAFT_METADATA_MODE=sync 及 map 四个修复开关。显式禁止 device metadata、device index、静态核与融合；SP_SCHEDULE 为空。
5. 隔离受控 preflight 验证所有间接 import、类初始化和继承调用；FULL capture/replay 处确认 capturing 字段、metadata、分组 block-size 和 slot mapping 的真实类型/形状/生命周期。不通过则不进入权重执行。
6. 八次串行质量与接受长度检查，同时记录 ms/step、A、tok/s；A>=1.3，连续两次 A=1 且 accepted throughput=0 判失败。MAX_SEQS1 不是官方 concurrency=1,2,4,8 guard 的同配置复现。
7. 新报告独立绑定 map/hash/argv/env/日志。当前未进行上述运行验证，不能从本报告推导图可用。
