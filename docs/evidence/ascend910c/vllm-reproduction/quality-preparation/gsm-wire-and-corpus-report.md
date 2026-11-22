# GSM wire 与替代正文准备（非 P2 通过）

## 实际新增

- `gsm_wire_client.py` 用 runpy 执行冻结的 `reference/tests/acc_eval.py`，仅包裹 urllib 响应，逐请求独立 JSON 保存原始 request/response 字节（base64）、SHA256、状态、读流异常。JSON/SSE 的 usage 和 finish_reason 原样留在 raw 中，不注入评分结果，不改变 prompt、模板、评分函数、stream_options 或 prefill 锁。
- `GSM_WIRE_DIR` 必须是新目录；离线导入无网络行为。将原命令中的 `reference/tests/acc_eval.py` 换成 `gsm_wire_client.py`，其余参数不变，且先指定 `GSM_WIRE_DIR`。尚未执行真实调用。
- 4 项纯内存离线测试实际通过：JSON usage/stop、SSE usage/length、畸形响应不得补造字段、空响应不得补造成功。命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest -v test_gsm_wire_client`。
- 原评分副本 SHA256 仍是 `aad813de1b1af090c4186b0a443b7839339928f90b63e7c3a654d0e028b8e6e2`。wrapper 不改它。
- `make_synthetic_corpus.py` 已实际生成原创合成中文正文 `synthetic-needle-corpus.txt`；来源/许可/精确大小/hash 与门限在 `synthetic-corpus-provenance.json`。不是旧红楼梦语料复现，重复背景难度不同。目标仍为147456，每针真实 prompt_tokens≥145982，maxlen196608、输出64。没有 tokenizer 或长上下文运行。

## 文件 SHA256

- gsm_wire_client.py: b8a083a4f8c91be24ccf540f95e02d5b8d946efeea45a77cc104b3ad8849d70a
- test_gsm_wire_client.py: de8b1b20684cbbfc5a1727c5f750d30a5a1c058b28c86e762ba843d779c0ba0d
- make_synthetic_corpus.py: ff6677db99508467abceb964b747f4c38dc0676805637d8340c8a1e5fa385399
- synthetic-needle-corpus.txt: 0c342582c65d6b61edc74075b433daad5c03e458affa872ed4a1c37154bf67fe

## 未完成与限制

未访问模型服务/NPU。wire wrapper 只保存成功打开的 HTTP response；连接/HTTP打开失败仍由原评分器处理，尚无该类失败的独立 wire 记录。没有额外读取未消费流尾，避免改变原客户端行为。raw capture 不是自动 usage 审计或准入器。未来真实测试须检查终止事件、usage、模型身份及独立run目录。

本次补丁没有完成官方1017 inventory下载/许可核验、Code128 adapter与docker隔离验证。P2 仍 BLOCKED，不能把这4个离线测试当模型质量结果。
