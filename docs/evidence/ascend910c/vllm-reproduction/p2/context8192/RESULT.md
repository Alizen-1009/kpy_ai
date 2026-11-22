# P2 context8192 — IN PROGRESS, not PASS

Old run was idle in two successive metrics snapshots, full inspect/logs preserved, ownership labels checked and only full CID 1fdb00879533bb97ba7ef9f7bf7f64639a03e8b01bdfbdfe198b8a03fcf98a65 stopped. Fresh npu-smi and listener evidence retained. Old deployment_v2_yh remains unchanged.

New deployment_v3_yh copies v2. Config change only MAX_LEN 4096 -> 8192; runtime map hash rebound in independent runtime report. Original verified assets/payload reused. Actual launcher succeeded and created/started run p2-8192-20261121T224721Z, full CID 8bf3ddd996ee580b7d94629ad7aeaa6c6d2b4158580a50e25c734ad4fe57313c on loopback18550. Last observation: loading 78 checkpoint shards, not yet ready.

Remote evidence: /root/syf/data_yf/yuhao_vllm_ascend_repro_yh/quality-run/context8192.

Background serial orchestrator PID2251262 is currently waiting for readiness, then requires unique /v1/models identity and real smoke before Code8 (original4096 budget, timeout1800) then Vision23. No implicit inference retry. If an orchestration exception occurs, it saves FAILURE.txt and stops only the verified owned full CID. Successful service stays running.

Task-local Code client adds --timeout (default180, allowed1..3600), unchanged tasks/scorer/model budget, plus persistent exact sandbox inspect/removal records. py_compile passed, CLI tests accepted1800 and rejected0/3601; timeout-tests.json retained. Sandboxes retain network=none/no devices and exact-CID ownership cleanup.

NOT YET COMPLETE: readiness/smoke outcome, Code128 score/finish/usage, Vision23 score/finish/usage, original two GSM length diagnostic1024 (and2048 once if still length), final result retrieval. Orchestrator intentionally does not claim GSM completion; main agent must perform the two-item diagnostic separately after serial stages. No same-instance GSM200 claim is supported.
