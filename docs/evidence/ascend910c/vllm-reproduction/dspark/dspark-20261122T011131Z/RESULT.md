# DSpark actual run: generation FAILED; no speed claim

Run dspark-20261122T011131Z. CID afa344faf865692f8149dd76fdd186aa84201d93aaaee677d98dc3f009a87f9d. Fixed image, locked HEAD 13 selected payload files, independent read-only payload and deployment_dspark_yh. MAX_LEN8192, K5, GRAPH1, draft graph and map fixes enabled; no eager/SPEC0 fallback or weight/precision/shared source edits.

No-device AST parsing completed; import hit device-dependent Triton get_arch (previous run dspark-20261122T011041Z), not a payload syntax failure. Original service ownership and idle metrics saved, full logs/inspect archived, only authorized old CID stopped. Fresh idle guard passed. Device task import then passed; new independently bound prerequisite report does NOT certify DSpark runtime. Launcher gates remained intact.

Actual runtime reached unique /v1/models. container.log:46 shows SpeculativeConfig(method='dspark',num_spec_tokens=5); :410 records 122 draft params loaded. :537-560 show actual draft graph capture, three draft attention layers and five query/input tokens. This is actual loading/capture, not merely environment configuration, but NOT successful generation/replay proof.

First Chinese smoke request returned HTTP500. Worker traceback container.log:620-657: sample_tokens -> propose_draft_token_ids -> _propose -> build_draft_attn_metadata -> build_dspark_swa_indices, attention/dsa_v1.py:623:

    _v41_bt_parent = getattr(self, "block_table", block_table)
    NameError: name 'self' is not defined

Concrete repair candidate for main agent: this is a module-level function without self. Its diagnostic block references self twice (line623 and error-message field near633). Remove invalid self-dependent diagnostic accesses or pass explicit diagnostic context through a reviewed isolated payload variant; preserve tensor computation and shape guard. Do not edit shared reference or frozen payload in place. AST/import tests cannot detect this runtime name lookup. Add focused function-path regression before another weight launch.

No code/multiturn checks or 1+8 speed requests executed after first-request engine failure. No TPS/TTFT/acceptance/step-time values or baseline speedup can be claimed. HTTP client traceback and full worker traceback retained (HTTP error response body was not captured).

Failure task CID only was stopped. stopped-inspect.json confirms Running=false, Pid=0, OOMKilled=false. Old GRAPH1 service also remains stopped; no fallback auto-restart. Address localhost18550 is not a retained usable DSpark endpoint. Full env/argv/mounts in inspect.json and launcher-run/inspect.json, preflight commands/logs, original logs/inspect/metrics, model identity and full failure logs retained locally.
