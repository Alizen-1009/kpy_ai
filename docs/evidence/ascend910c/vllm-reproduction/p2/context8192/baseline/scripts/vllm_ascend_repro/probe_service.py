#!/usr/bin/env python3
"""Loopback-only P1/P3 runtime smoke evidence, never a P2 quality assessment."""
import argparse
import codecs
import http.client
import json
import math
import re
import time
from pathlib import Path

PROMPTS = [
    [{"role": "user", "content": "小林有17颗珠子，送出5颗又收到9颗，现在有多少颗？简短回答。"}],
    [{"role": "user", "content": "请记住我的纸船名字叫青栗。"},
     {"role": "assistant", "content": "好的，我记住了。"},
     {"role": "user", "content": "我的纸船叫什么名字？"}],
    [{"role": "user", "content": "用Python写一个函数，返回整数列表中所有偶数的和。只给代码。"}],
]


def endpoint(value):
    match = re.fullmatch(r"http://127\.0\.0\.1:([0-9]{1,5})/?", value)
    if not match or not 1 <= int(match[1]) <= 65535:
        raise ValueError("base-url must be http://127.0.0.1:PORT")
    return int(match[1])


def events(response, clock=time.perf_counter):
    """Incremental UTF-8 and CR/LF SSE framing; yield verbatim event frames."""
    decoder = codecs.getincrementaldecoder("utf-8")()
    pending = ""
    frame = ""
    data = []
    size = 0
    while True:
        chunk = response.read1(4096)
        size += len(chunk)
        if size > 8 * 1024 * 1024:
            raise ValueError("SSE exceeds evidence size limit")
        pending += decoder.decode(chunk, final=not chunk)
        while pending:
            match = re.search(r"\r\n|\r|\n", pending)
            if not match or (chunk and match[0] == "\r" and match.end() == len(pending)):
                break
            line = pending[:match.start()]
            frame += pending[:match.end()]
            pending = pending[match.end():]
            if not line:
                yield frame, "\n".join(data) if data else None, clock()
                frame, data = "", []
            elif line == "data" or line.startswith("data:"):
                value = line[5:] if line.startswith("data:") else ""
                data.append(value[1:] if value.startswith(" ") else value)
        if not chunk:
            if pending or frame:
                raise ValueError("unterminated SSE event")
            break


def consume(response, start, raw, clock=time.perf_counter):
    text, times, finish, usage = "", [], None, None
    done = False
    for frame, data, arrived in events(response, clock):
        raw.write(json.dumps({"seconds": arrived - start, "raw_event": frame}, ensure_ascii=False) + "\n")
        raw.flush()
        if data is None:
            continue
        if done:
            raise ValueError("data after DONE")
        if data == "[DONE]":
            done = True
            continue
        item = json.loads(data)
        if "error" in item:
            raise ValueError("server SSE error")
        if item.get("usage") is not None:
            usage = item["usage"]
        for choice in item.get("choices", []):
            if choice.get("index", 0) != 0:
                raise ValueError("unexpected choice index")
            content = choice.get("delta", {}).get("content")
            if content:
                if not isinstance(content, str):
                    raise ValueError("non-text content")
                text += content
                times.append(arrived - start)
            if choice.get("finish_reason") is not None:
                finish = choice["finish_reason"]
    elapsed = clock() - start
    if not done or not text.strip() or finish is None:
        raise ValueError("missing DONE, nonempty text, or finish_reason")
    tokens = usage.get("completion_tokens") if isinstance(usage, dict) else None
    if tokens is not None and (type(tokens) is not int or tokens < 0):
        raise ValueError("invalid completion_tokens")
    return {"text": text, "finish_reason": finish, "usage": usage,
            "ttft_seconds": times[0], "end_to_end_seconds": elapsed,
            "content_chunk_intervals_seconds": [b-a for a, b in zip(times, times[1:])],
            "interval_definition": "content chunk arrival intervals, NOT token ITL",
            "end_to_end_output_tps": tokens / elapsed if tokens is not None and elapsed > 0 else None,
            "decode_tps": None, "decode_tps_definition": "not computed: exact token timing unavailable"}


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(args, connection_factory=http.client.HTTPConnection):
    port = endpoint(args.base_url)
    if not args.expected_model.strip() or not args.run_id.strip():
        raise ValueError("expected-model and unique run-id required")
    if not 1 <= args.count <= 3 or args.max_tokens < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        raise ValueError("invalid limits")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    save(out / "config.json", vars(args))
    summary = {"run_id": args.run_id, "scope": "P1/P3 runtime smoke only; not P2 quality", "status": "failed", "requests": []}
    connection = None
    try:
        # HTTPConnection connects directly: no proxy environment, redirects, or retries.
        connection = connection_factory("127.0.0.1", port, timeout=args.timeout)
        connection.request("GET", "/v1/models")
        response = connection.getresponse()
        summary["models_http_status"] = response.status
        if response.status != 200:
            raise ValueError("models HTTP failure")
        body = response.read(1024 * 1024 + 1)
        if len(body) > 1024 * 1024:
            raise ValueError("models response too large")
        models = json.loads(body)
        save(out / "models.json", models)
        if [m.get("id") for m in models["data"]] != [args.expected_model]:
            raise ValueError("expected exactly one matching served model")
        connection.close()
        for index, messages in enumerate(PROMPTS[:args.count]):
            request = {"model": args.expected_model, "messages": messages, "stream": True,
                       "stream_options": {"include_usage": True}, "temperature": 0, "max_tokens": args.max_tokens}
            if args.seed is not None:
                request["seed"] = args.seed
            save(out / f"request-{index}.json", request)
            record = {"index": index}
            summary["requests"].append(record)
            connection = connection_factory("127.0.0.1", port, timeout=args.timeout)
            start = time.perf_counter()
            connection.request("POST", "/v1/chat/completions", json.dumps(request).encode(),
                               {"Content-Type": "application/json", "Accept": "text/event-stream"})
            response = connection.getresponse()
            record["http_status"] = response.status
            if response.status != 200 or response.getheader("Content-Type", "").split(";")[0].strip().lower() != "text/event-stream":
                raise ValueError("chat HTTP status or content type failure")
            with (out / f"sse-{index}.jsonl").open("w", encoding="utf-8") as raw:
                record.update(consume(response, start, raw))
            save(out / f"response-{index}.json", record)
            connection.close()
        summary["status"] = "runtime_smoke_completed"
    except Exception as exc:
        summary["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        if connection is not None:
            connection.close()
        save(out / "summary.json", summary)
    return 0 if summary["status"] == "runtime_smoke_completed" else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("base-url", "expected-model", "run-id", "out"):
        parser.add_argument("--" + name, required=True)
    parser.add_argument("--count", type=int, default=3, choices=range(1, 4))
    parser.add_argument("--max-tokens", type=int, default=64)
    parser.add_argument("--timeout", type=float, default=60, help="socket operation timeout seconds")
    parser.add_argument("--seed", type=int, help="omit unless server supports fixed seed")
    args = parser.parse_args()
    try:
        return run(args)
    except ValueError as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
