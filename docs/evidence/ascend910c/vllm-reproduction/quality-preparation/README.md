# P2 评分资产准备（非 P2 通过）

仅在本目录写入；未启动服务、未访问 NPU、未执行模型生成。发布 revision `500297...` + 最小 SPEC0 诊断属于适配复现，不能继承旧实例质量。已读计划、P0 reference-summary 与参考 AGENTS。参考 HEAD 为 ab88ff84efa7970875f3f8cc38dfcb06c491b154；本次按实际文件冻结，完整文件 SHA/来源见 `assets.json`，副本在 `reference/`。没有提交 git。

## 已取得

- GSM：匿名从 OpenAI grade-school-math 公共 GitHub 下载 train/test 与 MIT LICENSE，先在线读取 LICENSE 再下载。共 **4,917,006 bytes**，低于100MiB，无登录/私有数据。URL、大小、SHA见 assets.json。train SHA `17f347dc51477c50d4efb83959dbb7c56297aba886e5544ee2aaed3024813465`，test SHA `3730d312f6e3440559ace48831e51066acaca737f6eabec99bccb9e4b3c39d14`，与严格历史门逐字节一致。URL虽为master，实际字节已冻结且 canonical guard 验证通过。
- `tests/acc_eval.py`：GSM200与100共用评分器，first200/first100 test、train first8原顺序8-shot；chat、temperature0、512输出，串行prefill。`norm_num` 使用 round(float) 整数归一化，存在小数容忍；不得悄悄改评分口径。原始模板需官方 encoding.encode_messages（本包不含），不可擅用通用chat template替代。
- `scoring.py`及`evaluator_sources.json`：冻结源提取函数与Vision案例；SHA分别4369e659…、a5c80ac3…，已实际加载测试。
- Code8：`experiments/delivery_matrix/workloads.py` 完整原题、prompt构造器、固定/seeded128用例及隔离评分器齐全（SHA62db3507…，匹配历史）。题目为LRU、合并区间、拓扑排序、最长不重复子串、kth largest、最小窗口、anagrams、flatten dict。用例数量17/16/16/16/15/17/16/15。参考仓Apache-2.0许可随副本保存。`benchmark.py`当前SHA b39d9c3… **不是历史CODE8_RESULT中33c458…**；不可将当前性能驱动称为历史逐字节复现。执行模型代码必须保留bwrap/sandbox隔离，禁止用exec替代隔离。
- Vision23：评分器与23题CASE已取得，SHA af13bc47…吻合历史。官方 carrots.jpeg/corn.jpeg 来源路径是官方 checkpoint `inference/examples/images/`，并引用 example_harmony.json/example.txt。历史图片SHA为5df896a4…/251fe7ad…；归档收据声称source/images存在，但本地对应source目录实际不存在。图片独立授权/模型包许可尚未核验，**未下载、未宣称图片合法可用**。空白PNG由评分器生成，不替代20张图题（两张图各10题）及3负控。
- 长针：`tools/ced_pd_acceptance.py` SHA d12d746f…匹配严格历史；原针/构造逻辑已齐。历史正文为 hongloumeng.txt，SHA a7fc413bd6e3926482faddf2af9bfb4426e55d8e421481d60100c14160785578，2468721字节。只有作者远端路径，没有已核验公开数字版本来源/许可，不能因原著年代久远便假定这个具体文件可再分发。未获取。地火是另一性能语料，明确不下载也不混作长针正文。

## 实际离线结果

`PYTHONDONTWRITEBYTECODE=1 python3 selftest.py` **PASS**；结果原件 `selftest-result.json`。
- GSM canonical hash校验；合成已知正确100行通过；错误答案、空答、重复ID、错误model共4负控均被拒绝。
- Vision原生 `--self-test` 退出0，覆盖scoring/empty/garbled/error/blank-PNG正负路径。
- 编程8题128例仅完成清点，**隔离执行未跑**；长针评分/端到端未跑。没有伪造任何模型分数，也未新增替代smoke题。

## 建议运行前冻结的门（不是当前发布的严格复现承诺）

| 项 | 建议适配质量目标 | 历史对应及限制 |
|---|---|---|
| GSM200 | ≥197/200，empty/errors=0 | EXPECTED_PERF历史197/198/199；非当前发布同实例 |
| GSM100 | 100/100，empty/errors=0 | A2sim v4 strict_quality_audit；与200重叠，不当独立300题 |
| Code8 | 8/8题且128/128例 | 同v4；保持隔离和原用例 |
| Vision23 | 23/23、empty/garbled/errors=0、mandatory negatives全部通过 | 显式min-hit-rate1.0；默认0.80不够 |
| 147456四针 | 4/4准确，每针真实usage.prompt_tokens≥145982 | 必须另开长上下文准入，不能在短上下文诊断臂强跑；maxlen196608、max_tokens64 |

同一run/model/权重revision/配置分别出结果，恢复SPEC/DSpark后重新测，不拼接历史行或SPEC0/SPEC1成绩。请求必须保存raw、usage、finish_reason、模型身份、prompt/hash及错误；旧GSM客户端丢弃finish_reason/usage，单独其summary不足以完成wire审计。需接入经审核wire sidecar或适配client后才宣称完整P2。不因length输出或HTTP200判通过。

## 将来回环执行模板（尚未执行）

在本目录，先确认唯一服务身份（/v1/models与run ID）、固定端口/模型，且权重/encoder/image许可与hash已经核验。变量由运行环境的真实manifest提供，不要求现在提交任何凭据。每个新run使用全新OUT路径，避免acc_eval断点文件串配方。

```bash
export BASE=http://127.0.0.1:18550
# MODEL=实际served name；ENC=已核验官方encoding；OUT=本run专有输出目录
python3 reference/tests/acc_eval.py --base "$BASE" --model "$MODEL" --enc-dir "$ENC" --gsm8k-data-dir "$PWD/gsm8k" --task gsm8k --limit 200 --mode chat --conc 1 --serialize-prefill 1 --max-tokens 512 --out "$OUT/gsm200.json"
# strict100独立运行用同命令 --limit 100 --out "$OUT/gsm100.json"
python3 reference/tests/vision_accuracy_check.py --server "$BASE" --model "$MODEL" --images-dir "$IMAGES" --official-dir "$OFFICIAL" --min-hit-rate 1.0 --max-tokens 32 --temperature 0 --out "$OUT/vision23.json"
# 仅SPEC恢复并验证后加 --expect-dspark；SPEC0不伪称DSpark通过
python3 reference/tools/ced_pd_acceptance.py --base-url "$BASE" --tokenize-url "$BASE" --model "$MODEL" --corpus "$CORPUS" --mode needle --context-tokens 147456 --max-model-len 196608 --max-tokens 64 --repeat 1 --offset 0 --out "$OUT/needles.json"
```

编程现有benchmark依赖实验metrics控制接口，不能直接向普通发布服务运行并宣称可用；尚需普通回环生成adapter和隔离评分驱动。长针需补充raw capture与真实token门审计。官方encoder必须核验逐文件hash；历史manifest digest7055766f…只是对照不是当前已有资产。图片/正文合法来源、encoder、Code sandbox执行和adapter、wire采集、所有真模型结果仍未完成，故 **P2 BLOCKED / preparation partial**。
