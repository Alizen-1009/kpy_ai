# 远端只读 P0 资产核查

采样始于远端 UTC 2026-11-21 06:41:02。仅 `ssh 910c`；没有创建/exec容器、下载、部署、框架导入或NPU计算，没有读取敏感env/凭据。未扫描其他用户目录。仅列出授权根目录、指定模型目录、自己的源码及已知inventory。该范围未发现目标发布W4A8，不等于全机不存在。

## 原始证据与执行

本目录 `inventory.sh`、`metadata.py`、`followup.py` 为完整输入，各自 `.stdout` / `.stderr` 为原始输出。执行形式：

```sh
ssh -o BatchMode=yes -o ConnectTimeout=10 910c 'bash -s' < inventory.sh > inventory.stdout 2> inventory.stderr
ssh -o BatchMode=yes -o ConnectTimeout=10 910c 'python3 -' < metadata.py > metadata.stdout 2> metadata.stderr
ssh -o BatchMode=yes -o ConnectTimeout=10 910c 'python3 -' < followup.py > followup.stdout 2> followup.stderr
```

首命令退出2：numactl未安装、短镜像名不存在，以及未匹配的OPP glob；之后用sysfs采NUMA、完整镜像名复核。没有安装工具修复。后两命令退出0。

## 资产表

|项目|fresh证据|结论/限制|
|---|---|---|
|root|4.4G可用，94%|禁止把大权重/缓存放root|
|数据卷 `/root/syf/data_yf`|816G可用，78%|不是已批准下载预算；必须另计缓存/Engram重组/保留量|
|`/data2`|725G可用，79%|未创建目录或写入|
|`/home`（Docker所在分区）|56G可用，84%|镜像解包/层缓存可能紧张；未拉镜像|
|host RAM|available980GiB，free309GiB|瞬时值，非预留|
|NUMA|node0/1/2/3 total分别262757552/264089504/264218528/263089468 kB；free157937724/59092760/46531128/60989256 kB|完整sysfs meminfo/cpulist见metadata.stdout；MemFree非MemAvailable；未绑核|
|NPU|dies8–15无进程，AICore0；映射NPU4–7的chip0/1|仅采样时空闲，约2.8–3.2GiB保留HBM，不是预约|
|driver/CANN host|25.5.1 / toolkit8.5.0 build V100R001C25SPC001B232|不能替代镜像内SDK版本|
|旧V4镜像|ID `fe705b00b250b7b40e4103b668ed2434c9bfec257611f4a9674315223f138af3`；RepoDigest `quay.m.daocloud.io/ascend/vllm-ascend@sha256:ee01558f5928b969586a798036ef76ad24f0c312d297523cd993765a19736595`|DeepSeekV4-flash-0731-a3，不是目标V4.1发布镜像|
|v0.30.0-a3|ID `77aea90962507771cfaf5304c926ee3f3539907eb59d37edb560177e7e7b4033`，RepoDigests空|本地镜像ID可固定；无registry digest记录；不能按tag猜内部版本|
|发布A3镜像|完整image ls没有 `quay.nju.edu.cn/ascend/vllm-ascend:deepseek-v4.1-flash-a3`|未确认相同内容以别名存在；未自动拉取|
|源码|五个DeepInfer自有副本HEAD均 `a679bb86ce36e883a98a97733492b686e5b9a08e`，均dirty|完整status已保存，不reset；不是vLLM发布源码身份|
|custom OPP|host标准vendors glob未发现条目|不证明容器内部没有；发布OPP、BI OPP及其hash均未fresh核验|
|官方1017 HF视图|`/root/yuhao/DeepSeek-V4.1-Flash-1017-HF`；96085索引条目，48/48引用可解析，config/tokenizer/index小文件SHA已采|官方混合FP4/FP8，不是发布W4A8_DYNAMIC|
|官方归档|`/root/syf/data_yf/DeepSeek-V4.1-Flash-1017-original_yf`，inventory84/84文件存在且大小匹配，总510311045870 bytes|原归档使用_yf命名，原索引标准名称不直接解析；HF视图解决名称映射|
|官方元数据副本|`/data2/syf/DeepSeek-V4.1-Flash-1017-original_yf`|索引引用48片不在此目录，不可当完整模型|
|旧W8资产|0731-w8a8索引107851条/74片；w8a8-mtp索引103176条/70片，引用均存在|均为V4 W8A8，不能替代目标V4.1 W4A8|

官方inventory保存per-file Revision/SHA256；下载status历史称all_weights_verified=true。本轮仅重算小元数据SHA及stat全部inventory文件，**未读取或重算数百GB权重payload**，因此历史verified不升级为fresh hash验收。tokenizer.json大小6367257，SHA `c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b`；config SHA `8be45ce0476004a3f529fd896115a4a2e800a129ad2d3ec05b16050f52e21879`。

官方索引含Engram12键、vision259键、mtp2401键、字面draft0键；这只是原始checkpoint命名证据，不证明发布Engram int8 DR、QuaRot折叠vision或DSpark配套。未发现/核验发布重组脚本，故未执行。

## 对照 reference-summary.md 的阻塞

1. 10-04发布候选需要W4A8_DYNAMIC、int8重组Engram、QuaRot及同checkpoint draft/vision；现有核验资产全部不满足目标身份，目标ModelScope revision、hash、文件列表/大小及官方源revision均未锁定。
2. 目标发布A3镜像标签未在本地镜像清单出现；fe705旧镜像和v0.30新镜像均不能直接冒充。发布框架commit/dirty、CANN/torch_npu和custom OPP未绑定。
3. 旧镜像包版本仅沿用历史 `ref/DeepInfer/doc/ascend910c-environment.md`：fe705 CANN9.0.1、torch2.10.0+cpu、torch_npu2.10.0.post2。本轮没有新建容器或exec外部容器，**没有fresh包版本核验**；v0.30.0内部版本未知。
4. 88tok/s为另一BI实验栈，不是10-04发布默认；本轮未确认batch_invariant OPP及其二进制hash，不能宣称该栈齐备。
5. 可用磁盘/host内存不等于下载或重组容量门已通过：发布真实字节和临时空间未知。现有root仅4.4G尤其不可使用。

结论：只读盘点完成，**远端必要资产身份不齐，P0通过条件未满足，不能继续P1部署**。没有更改共享资产或清理任何容器/缓存。
