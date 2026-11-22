# P1 安全启动设计（只读审核，尚未实施）

## 状态与边界

本次只做本地源码审核；未 SSH、未运行参考启动/检查脚本、未建容器或下载资产。仅新增本文。已阅读计划、handoff、P0 manifest/reference-summary、参考 AGENTS.md 及下列源码。发布资产身份由另一 agent 核实；本文不填造镜像 digest、模型 revision、部署路径或可执行启动命令。**当前 P0 BLOCKED，本文不构成放行。**

下文 `R/` 指 `ref/deepseek-v4.1-flash-ascend910B/`，行号对应当前本地文件；基线 HEAD 为 `ab88ff84efa7970875f3f8cc38dfcb06c491b154`，实际冻结须同时使用 `local/reference-files.json`、dirty patch/untracked 清单，不将 HEAD 当工作树全部身份。后续只修改独立任务副本，原参考、DeepInfer、官方checkpoint和共享环境保持原样。

## 必须修正的源码风险

| 源码位置 | 实际行为 / 风险 | 任务副本拟定变更 |
|---|---|---|
| `R/scripts/serve_a3.sh:58–65,101–113,128–139` | 可变镜像标签、固定默认 NAME/PORT；CPU_BIND 默认1、Engram index默认1，PATCH_MODE=mount | 镜像必须来自已核验digest；缺身份即拒绝。强制唯一run/name/served-name；CPU_BIND=0、CPUSET=-1、MEMS=-1、ENGRAM_DEVICE_INDEX=0。不能只关外部cpuset而留下内部绑定。 |
| `R/scripts/serve_a3.sh:179–254` | 设备校验只校数量/数字，不检查重复或授权集合；I_KNOW可绕过；idle依赖进程表正则，缺npu-smi或解析失败会放行，ALLOW_BUSY可跳过 | 精确白名单集合且顺序固定8–15、每项唯一、TP8/DP1；拒绝I_KNOW与ALLOW_BUSY。idle查询失败、格式未知、映射不完整均失败关闭；不得自动换到其他空闲die。 |
| `R/tools/list_chips.sh:21–51,71–115` | 信息表按枚举序号推device、进程按npu*2+chip；无进程即空闲；会建议全机first8 | 只能当只读辅助，不能把其输出当授权或预约。对目标4–7物理NPU/8–15die与sysfs/设备节点交叉验证；保留原始输出和时间。无进程但异常HBM占用需解释，不自动清理。 |
| `R/scripts/serve_a2.sh:1417–1419,1529–1539` | 虽列举davinci设备且设visible env，但 **--privileged=true让设备白名单失去隔离意义**；宿主dcmi/driver/hccn/npu-smi/install.info挂载无ro | 删除privileged，不挂整个/dev、不开放全设备规则。仅8个davinci节点及经审核必要的manager/devmm_svm/hisi_hdc；宿主驱动和配置逐项ro，禁止Docker socket。非特权兼容性若不成立，阻塞而非恢复privileged。环境变量不是安全边界。 |
| `R/scripts/serve_a2.sh:188–190,1529; R/scripts/serve_v2.sh:66–69,104` | HOST默认0.0.0.0且host网络 | 显式并硬校验HOST=127.0.0.1。若保留host网络以兼容HCCL，审查实际所有监听（不仅API），不可声称网络命名空间已隔离。HCCL额外非回环监听需审核及访问限制。 |
| `R/scripts/serve_a2.sh:239–240,1465–1480` | A2默认dropcache，能够sync及写全机drop_caches；A3只改默认，环境仍可重新打开 | 在任务入口硬拒绝DROPCACHE非0并移除执行分支；禁止sudo自动提权（亦见425–427），无权限即阻塞。 |
| `R/scripts/serve_a2.sh:375–421,888–903,1484,1977–2034,2091–2098,2268` | OUT/CACHE默认写包内；早期mkdir发生在dry-run重定向之前；缓存GC删除ts目录；生成inner.sh/log；写包根.last_run_id | 在任何副作用前解析并验证任务自有OUT/CACHE/TMPDIR/LOG，禁止路径软链逃逸、重用已有run目录。GC只允许本run缓存，首次直接禁用。last_run_id改为run内元数据。原脚本DRY_RUN不是无写操作。 |
| `R/scripts/serve_a2.sh:582–586,603–674,746–884` | 可MODEL_MOUNT_ALL_RW；index路径可将Engram实体及中间目录rw覆盖；ancestor/EXTRA扩大暴露 | 诊断index0，MODEL_MOUNT_ALL_RW=0；禁止ancestor、none及任意EXTRA挂载，使用逐目录审核白名单，全部模型ro。检查最终Mounts最深覆盖项，不能只看父目录ro。任何O_RDWR要求均停止，不chmod/chown共享模型。 |
| `R/tools/model_mount_args.sh:38,46–47,70–78,91–104,125–143` | 入口realpath，递归字面软链；超深/超目录上限和listdir失败可静默返回；发现断链才失败；输出实际是裸路径而非头注释的-v | 任务副本把超限、权限错误、环和未覆盖入口别名改成明确失败；保留入口字面路径与所有中间跳及最终inode清单。拒绝共享宽祖先、越界路径与异常路径字符，逐文件核验全部分片可见。 |
| `R/scripts/serve_a2.sh:1096,1125–1126,1153,1195,1206,1255` | 多个Python补丁及DCP overlay以rw挂入；容器能反写源副本（不代表已发生反写） | 禁DCP overlay；已冻结payload逐文件ro，若必须运行期变更，先复制到任务运行层而非共享树。变更前后hash与patch留存。 |
| `R/scripts/serve_a2.sh:1680–1707,2035–2089` | admission补丁应用到容器vLLM树，失败只警告；可选OPP复制替换及缓存失效 | 仅容器自有可写层打已冻结补丁，前置目标hash与应用后hash验证，失败必须停止。禁止宿主框架目录rw挂载；不启用自定义融合/OPP override或BI实验资产。 |
| `R/scripts/serve_a2.sh:404–411,1483,1651–1656` | 启动前按NAME强删；失败按NAME清理；创建输出CID被丢弃，后续exec也按NAME | 删除预清理；名称冲突即失败。创建时独占cidfile并记录完整CID、run/owner标签、image ID。所有exec/inspect/stop/remove用完整CID，先核对标签、创建时间和run清单；不得按名称、模糊模式或全局prune清理。 |
| `R/scripts/serve_a2.sh:2107–2117; R/scripts/serve_v2.sh:104–106,176–181` | readiness仅health200可误认他人服务；trust-remote-code与自由EXTRA/KV_ARGS可能扩大代码/参数面 | 校验唯一served model ID及端口进程归属本CID；健康之后真实生成。冻结审核模型自定义代码，禁止在线拉取；EXTRA仅固定模板参数，KV_ARGS空，拒绝未知环境覆盖与重复host参数。 |

**是否会写共享路径/模型？** 脚本明确写OUT/CACHE/包根，并删除缓存；若直接从共享包起服就会污染共享路径。宿主驱动挂载默认rw、payload若来源共享则rw，具有反写权限。模型默认并非一律rw，但A3 index1会放开Engram实体目录，ALL_RW还能扩大为整个模型；这证明写权限风险，不等于已经观察到改写模型数据。必须同时消除privileged、rw共享挂载和越界路径，不能只设MODEL_MOUNT_ALL_RW=0。

## 拟定诊断配置（参数设计，非执行命令）

- TP=8、EP开启、DP=1；授权物理die严格为8,9,10,11,12,13,14,15；不做DCP/PD/CED/多副本。
- SPEC=0、PREFIX=0、DRAFT_GRAPH=0、SP_SCHEDULE空；真实发布权重，LOAD_FORMAT空（禁止dummy）。ENGRAM=1、ENGRAM_DEVICE_INDEX=0；保留发布混合量化ascend和BF16 activation/KV，不冒充纯W4。
- MAX_SEQS=1、MAX_LEN=4096；首轮请求prompt最多512 tokens、max output=64、串行1个请求；确认后做少量不同中文/代码提示，不执行并发矩阵或长针。
- 为不混入容量优先几何，BAT_TOKENS=8192与V41_KV32_REPACK=0成对显式保持10-04候选；短请求并不意味着偷偷降低BAT。GPU_UTIL初拟0.85，须模型加载预算与实际各rank空闲内存允许；不足则停并重评，不能自动加到0.94。短上下文不会自动限制总KV池分配，保留KV32门并要求实际块数证据；不能凭短请求豁免越界。
- 首次诊断可选择GRAPH=0/EAGER=1、NPUGRAPH_EX=0/STATIC_KERNEL=0，作为明确的eager诊断臂，先排除图捕获；在固定框架证实支持后才执行。恢复FULL_DECODE_ONLY为后续独立run，不与本臂性能混比。`serve_v2.sh:114–124`决定实际CLI，不能只保存外部环境。
- CPU_BIND=0、CPUSET=-1、MEMS=-1、PYTHON_PGO=0、DROPCACHE=0；拒绝ALLOW_BUSY/I_KNOW、融合、探针、动态spec、开发端点及用户遗留环境。MODEL/IMAGE等不允许引用作者机器示例路径或可变标签作为身份。
- HOST=127.0.0.1；唯一run/name/served-name和已确认空闲端口，明确no_proxy覆盖loopback。非回环监听即失败。128线程loader（`serve_v2.sh:160–162`，`serve_a2.sh:1995`附近强制LOADER_MT=1）也是共享CPU负载风险：任务副本取消强制、初始LOADER_MT=0；另审核容器CPU/host内存/PID预算，不能把无限memlock和512GiB shm当资源预约。

## 后续P1分步门（本次均未执行）

1. **资产门**：接收另一agent的固定模型revision/完整清单及重组结果、image digest、框架commits/dirty、CANN/torch_npu/OPP身份及容量核算；必要项未知则保持BLOCKED。镜像或补丁不配套不得自动更新main。下载/重组只在已审批任务数据卷，不落root或共享checkpoint。
2. **工作区门**：新独立工作区位置须实际容量确认；建议路径不是已存在事实。冻结原始源码快照只读，另建run副本和独占cache/output/tmp；记录安全补丁diff及全部SHA256。模型仅ro；若index0仍要求写权限，停止而不是放开共享。容器可写层、模型数据卷、编译/日志和shm分别核预算。
3. **离线展开门**：在任务副本实现无副作用plan模式，输出完整argv数组、inner配置、所有设备、最终挂载、环境白名单及清理目标；原DRY_RUN只输出部分摘要且前面已有写操作，不足验收。检查bash语法及run续行工具（AGENTS §3.1），运行前先审查selfcheck是否会写共享。负控包括重复die/0–7、busy/查询失败、privileged、rw驱动/模型、路径逃逸、NAME冲突、dropcache、CPU_BIND、未知资产及恶意环境，全部必须拒绝。
4. **fresh-idle门**：设备任务紧前重新采样，检查查询返回码、完整映射、目标进程与HBM，busy或未知就暂停，不杀外部进程。历史P0空闲不是预约；检查与启动间有竞态，尽量使用管理员资源租约/调度预约，启动后重新核对，出现外部竞争则仅停自己的CID。
5. **容器边界门**：创建但尚不起引擎时检查实际HostConfig非privileged、Devices精确白名单、无宽device rules、无宿主PID/IPC、所有共享Mounts为ro；核对容器实际可见设备与runtime枚举。不得靠尝试访问0–7来做负测；使用配置/节点权限证据。manager等控制设备的驱动权限边界也须确认，若仍可跨die操作则报告隔离不足而非宣称已强隔离。
6. **启动/验收门**：留存完整实际配置和8rank→授权设备映射、权重/补丁/OPP命中路径、实际加载数量、无fallback/OOM、host与各die峰值内存。确认监听进程属于唯一CID，再查唯一/v1/models与health，随后真实生成并检查非空文本、usage、finish_reason、无静默1-token空答。只算P1诊断通过，不代表P2质量或88/106.8 tok/s性能复现。
7. **失败/结束门**：保留日志、inspect、退出码和失败原因后，核验run标签及完整CID，只停止/删除该CID；无CID或归属不匹配则不清理并报告。删除前采集证据，删除后验证CID消失、目标设备无本任务残留、端口释放；不删共享缓存、不kill全机进程、不prune。默认不保留服务，保留须用户明确要求。

## 放行结论

原脚本不能直接运行：**privileged、共享rw挂载、按NAME强删、idle失败放行、health误认与dry-run副作用**均为P1阻塞项。以上仅为任务副本的待实施设计；资产身份与隔离能力未核实前不提供可执行部署命令，不声称已完成任何部署TODO。
