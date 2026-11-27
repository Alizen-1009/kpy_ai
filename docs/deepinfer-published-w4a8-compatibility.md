# 发布混合 W4A8 与 DeepInfer：兼容性调查

状态：本地源码/配方调查，补充真实 checkpoint header 验证；非已实现适配。

## 实际发布 header 补充

证据：[header 校验摘要](evidence/ascend910c/published-w4a8-contract/header-validation.json)。读取 8 个主 shard 与 6 个独立资产的 header，未加载大权重 payload。

- layer30 shared：w1/w3 I8 `[2304,5120]`，w2 I8 `[5120,2304]`，各自配套 F32 `[N,1]` weight_scale/weight_offset。
- routed 35/124：w1/w3 存储 I8 `[1152,5120]`；w2 I8 `[2560,2304]`；**w2.scale_bias 为 F32 `[5120,16]`**，不能按普通per-channel参数忽略。
- rotation：global_rotation F32 `[5120,5120]`，数值及应用方向待验证。
- Engram：索引指定独立大表；extra文件内同名 `[1,1]` 条目不能覆盖真实表。
- `validate_headers.py` 已验证摘录的字节数/shape、区间不重叠、索引映射和shared几何；篡改shape的负控被拒绝。payload完整性与计算公式未因此获得验证。

## 运行时实现与参数观察

源码结论来自对容器内文件的静态检查，不证明运行进程加载了这些文件，也不是对镜像完整性的认证。发布权重的加载记录见 [layer 30 CPU 校验结果](evidence/ascend910c/published-shared-load/result.json)。

- routed w2.scale_bias：先按TP切列，再transpose/sum成为bias并传入GMM；EP模式的该方法TP设为1。16列的exporter生成公式与kernel数学语义仍未闭环。
- 发布INT4沿输出N轴打包；当前msModelSlim加载分支转置已有bytes，不解包。低/高nibble及符号契约仍需exporter证据，不能借用另一格式分支的规则。
- 通用shared W8A8 scheme保存offset但apply不使用。另读取了 layer 30 shared 的六个 scale/offset 小 tensor，共 77,824 字节：**三个 scale 均有限且严格为正，三个 offset 全部为零**。CPU 校验结果记录了逐 tensor 的 SHA256；这一观察不推广到其他层。
- Engram gate使用global_rotation的位置已定位，主干QuaRot的完整离线/在线边界仍未闭环。

仍需验证shared实际dispatch、发布exporter、TP/EP与旋转；不能据此宣布后端接入完成。

路径缩写：
- DI：`ref/DeepInfer/deepinfer`
- PUB：`ref/deepseek-v4.1-flash-ascend910B/patches/files`
- 配方：`docs/evidence/ascend910c/vllm-reproduction/p0-asset-inventory/public/metadata/release/msmodelslim/recipes/deepseek_v4_1_flash_w4a8.yaml`

| 模块 | 差异/待办 | 源码依据 |
|---|---|---|
| 命名 | DI 合并 w1/w3 为 linear1，依赖 `.scale`；发布普通权重 loader 委托父类，需真实索引逐 tensor 映射 | DI `hugging_face/weights.py:113–147`；PUB `model.py:1614–1655` |
| scale | DI shared 是 E4M3 + 32×32 E8M0；发布是 INT8 per-channel 权重与 INT8 per-token 激活 | DI `quantization/linear.py:12–26,115–123`；配方13–36行 |
| packed weight | DI INT8 容器装的是 FP4，不是 INT4；发布 offset、nibble 顺序、设备布局仍需真实 header 与父类 loader 核实 | DI `hugging_face/weights.py:372–424`；配方20–24、117–120行 |
| 旋转 | 发布 block32 QuaRot；Engram 从 optional/quarot.safetensors 读取 global_rotation 并传入 gate；需对齐离线/在线位置 | 配方37–41行；PUB `model.py:998–1015,1502` |
| shared | DI 强制 OfficialFP8Linear；发布 shared W8A8，排除 routed AWQ/SSZ 流程 | DI `model_executor/models/v4_modules/official_backend.py:97–105`；配方60–64、106–115行 |
| routed | DI 要求 FP8 activation + FP4 weights；发布 INT8 activation + INT4/SSZ | DI `model_executor/models/v4_modules/official_backend.py:59–75,182–201`；配方93–105行 |
| attention | 发布只量化部分线性层，排除 wo_a/wo_b、compressor、部分 indexer；不能整体切 W8 | 配方76–92行 |
| Engram | 配方排除 Engram 不代表表格式可互读；发布独立处理 embed.scale，支持多种表格式，非表参数 BF16 | PUB `model.py:1621–1642`、`engram_hbm.py:288–323,458–461`；DI `hugging_face/official_engram_loading.py:35–41,117–177` |
| TP/EP | DI 按 EPLB ownership 加载且 CP=1；发布 Engram 要求 EP、PP=PCP=DCP=1，wkv 可按输出维 TP 分片 | DI `hugging_face/weights.py:365–378`、`model_executor/models/v4_modules/official_backend.py:46–80`；PUB `engram_hbm.py:352–373`、`model.py:1632–1637` |

## 下一步证据

1. 读取实际发布索引和 safetensors headers，输出名称、shape、dtype、scale/offset 关联，不复制整套权重。
2. 从固定镜像追踪 `vllm_ascend.models.deepseek_v4.model` 及量化 loader 的真实调用路径。
3. 每类模块建立单层 loader 与算子对照；旋转和量化共同验证。
4. 独立后端实现前不修改官方 FP4 默认路径。

配方仅证明量化意图；不证明发布资产的实际存储格式或运行时布局。P1 的官方 shared 再量化实验也不等于直接支持发布 shared 权重。
