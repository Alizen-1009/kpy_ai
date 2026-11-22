# P0 公共发布来源核查（2026-11-21 UTC）

## 结论

来源真实存在且匿名元数据/小文件可取得；**不是404、不是需要用户token**。本次未下载任何权重、镜像layer，未SSH、部署或占NPU。P0整体仍未通过。

- ModelScope 固定可解析 revision：`50029772e7757c3d9cec50481661091b369af901`。来自master列表最新README提交；已用该SHA重新请求递归文件列表，HTTP200/Success=true，结果与采样master文件记录完全相同。不是仅把master当不可变revision。git refs接口HTTP421，故不声称完成git协议HEAD验证。
- `model-files.json`：固定revision递归API返回的120个文件（另10目录），全部有64位SHA256和字节数；总计 **525,795,307,321 B**（约489.68 GiB），不是212.6GB。原始完整JSON保存在`ms-pinned-files.body`，没有截断、未返回分页字段。哈希是发布服务器声明，除README/重组脚本之外未重新hash payload；不能据元数据证明每个大blob均能实际传输。
- Engram 12片合计 **196,613,849,824 B**；保留分片并重组需额外同等空间，总文件预算至少 **722,409,157,145 B**（约672.8 GiB），另加下载缓存、文件系统余量、临时文件。若下载工具额外复制全量cache，预算再加525.8GB，不能认为当前数据卷必定够。
- `ms-reassemble.body` 保存完整脚本，SHA256 `41d1d467de45a8c34a36828101ffb026ccc543ff8a01d01afcd468a06408eb1d`，与固定文件清单匹配。README也独立hash匹配。
- NJU与原Quay index均HTTP200且字节SHA与Docker-Content-Digest一致：`sha256:2c906b38ad3cc9ed9badfe3d09451d194fa09a07e5c6d62a66b111731e626060`。该digest也被固定ModelScope README公开声明。
- linux/arm64 child：`sha256:16a57b897a2f475f85b0e90df1644c9870c2418b368b2adf447c5173eae211c3`，原Quay按digest请求HTTP200，payload hash一致。layer压缩大小合计 **10,357,254,631 B**，不是解压后的Docker磁盘需求；未读取layer或确认全部blob下载可达。完整layer清单在`quay-arm64.body`。

## 网络证据与真实性边界

初次继承本机网络配置，ModelScope cn/com及NJU均TLS EOF，**未得到源站HTTP状态**。curl显示代理CONNECT 200后TLS失败；CONNECT不是源站成功。禁用代理的Python标准库请求后，cn三个API及NJU manifest全部200，故原阻塞为访问路径问题，不能推断资产不存在。没有输出代理地址或凭据。

GitHub API HTTP403正文明确匿名rate limit，不是仓库不存在。raw GitHub固定commit `ab88ff84efa7970875f3f8cc38dfcb06c491b154` 的README与REPRO均200；README引用相同模型和镜像。固定README与main下载字节相同。这验证公开发布关联，并非独立证明量化质量或官方1017血缘。模型API标注base `deepseek-ai/DeepSeek-V4.1-Flash`、quantized、Apache2；尚无官方源commit映射证据。

## 重组脚本静态审阅

脚本在自身目录按00..05拼接两个大文件；检查PARTS.sha256（若存在）、最终硬编码hash后rename；默认保留分片。最终hash：
- layer1：`51d28f161232e3bf600b92ef4e3c38ceb9164b801bd456503bb1a29da496ea9f`
- layer14：`bee6e08838c75d40c4b1f5f8d7e4716aba34f90c03c17e77ad406e36188cccaa`

**不可无条件照跑**：无sha256sum仍可成功；PARTS.sha256缺项跳过；会`mv -f`覆盖目标；无signal trap，终止可能留下tmp；mv失败未显式纳入fail；`--delete-parts`删除分片。因此后续须外层强制逐个manifest hash、确保sha256sum存在、目标为任务自有且无旧target/tmp，不得delete-parts，重组后独立hash/size验收。脚本本次未执行。

## 确切下一步（仍不部署）

1. 在已授权910c仅做同样匿名metadata GET（必要时禁代理），确认远端网络；用以上revision与digest，不用浮动master/tag。可先在本机重跑`python3 docs/evidence/ascend910c/vllm-reproduction/p0-asset-inventory/public/probe-direct.py`，它只读取metadata。
2. 下载固定revision的小文件PARTS.sha256、config、量化描述、index（先核对清单大小并单独允许有界上限），检查全分片引用/Engram/draft/vision/quarot；补齐发布与10-04候选差异：当前模型README声明190,728 index键，明显不应直接继承旧187,226容差。
3. fresh只读核算数据卷/缓存/重组峰值及Docker解压峰值。至少722.4GB加余量；现有空间快照不足以自动过门。隔离目录、禁止root落大文件、禁止覆盖官方checkpoint。
4. 完成上述门及框架/SDK/OPP身份核验后，主代理才可决定开始固定revision分批下载；下载后全hash校验，再重组并复核最终hash。本次证据仅解除“发布是否存在/metadata身份未知”，不解除所有P0验收。

原始请求URL、UTC、状态、有限响应头和body SHA在`http-*-results.json`；脚本均只匿名GET，单响应上限1MiB，无token、无登录。`summary.json`为机械统计。
