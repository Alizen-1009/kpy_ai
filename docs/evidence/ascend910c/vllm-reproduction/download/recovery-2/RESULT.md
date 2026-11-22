# Recovery 2: executed, terminated with failure (NOT complete)

Started UTC 2026-11-21 19:25:48, waited to terminal exit code 1 after approximately 2004 seconds. No automatic retry, deletion, quarantine, reassembly, or extra hash audit performed. Historical supervisors and exits untouched.

Remote evidence: `/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/logs/recovery-2-20261121T192543771511Z/`. Full pinned manifest and `--workers 4 --resume --direct --execute` used. Dedicated downloader/supervisor copies and SHA256 recorded in process.json. Supervisor PID 2217726/startticks178053203; downloader PID2217727/startticks178053206; bootid20bd7f0d-55e0-4cf5-b001-eab251f97b15. Both absent after exit; no locks remain.

Downloader verified all 60 existing assets using its unchanged hash protections and completed shards33–51 inclusive (19 additional files). The separate read-only audit reported by parent is acknowledged: logs/completed-hash-audit_20261121T192359Z.json; 60 files/363557117864 bytes, same manifest hash. No third audit started.

First failure: shard53 ValueError, static reason `size/hash mismatch`. Actual retained part is 3114203898 bytes versus expected4294438808: unequivocally incomplete, NOT evidence of a full-sized corrupt hash. Shards52/54/55 then stopped with `download group stopped; partial retained`. Their retained sizes:3494903808/1031798784/678428672. All retained. Available425602162688 bytes. Logs establish short result but not upstream cause.

Local evidence: launch.json, process.json, exit.json, download.jsonl, supervisor.log, final-snapshot.json; launch.py/supervisor.py/wait.py preserve orchestration. No further recovery authorized/executed after this terminal failure.
