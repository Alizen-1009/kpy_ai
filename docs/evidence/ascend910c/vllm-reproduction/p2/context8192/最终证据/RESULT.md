# P2 context8192 — FAILED orchestration; Code PASS

前台有界等待既有 PID2251262 至终态，没有重复评测、重启或另行停止任何容器。

- 模型：p2-8192-20261121T224721Z；CID：8bf3ddd996ee580b7d94629ad7aeaa6c6d2b4158580a50e25c734ad4fe57313c。
- readiness/models 身份通过；smoke 返回 OK，finish_reason=stop，usage prompt/completion/total=8/2/10。
- Code8：8/8 tasks，128/128 assertions，所有响应 finish_reason=stop。逐项原始 response、评分 JSON、sandbox 记录保留在 code128/；usage 汇总在 wire-summary.json。
- Vision23：没有分数，不是 0/23。既有编排遗漏内置 suite 必需的 --images-dir，CLI 参数校验退出码2；见 vision23.log、vision23-argv.json、FAILURE.txt。未进入视觉推理，无实际 Vision wire/usage。
- 原编排自身异常处理自动停止其拥有的 CID（quality.py 可审计）；当前进程已结束，容器 Running=false / Status=exited / ExitCode=0，FinishedAt=2026-11-21T22:58:37.371242168Z。18550 无监听。服务不是 running/idle，而是已停止；见 status.txt 与 final-inspect.json。
- GSM 两个 length 诊断未执行：用户要求成功后执行，但编排失败且服务被原编排停止；没有擅自重启。没有本实例 GSM200 分数，也没有拼接不同 run 声称完整200。

失败明确定位为编排 CLI 参数遗漏，不是模型视觉正确率失败或 Code 超时。继续视觉测试须另行授权恢复服务并修正调用参数，本次未做。不操作 graph/spec/长针/性能，不停止其他任务。
