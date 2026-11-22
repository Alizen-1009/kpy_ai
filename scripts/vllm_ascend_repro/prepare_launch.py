#!/usr/bin/env python3
"""Offline P1 preparation gate. Deliberately refuses unsafe recipe generation.

No recipe is executed, including its misleading DRY_RUN branch. This partial
implementation is fail-closed until the blockers in implementation.md are fixed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat

SAFE = dict(DEVS="8 9 10 11 12 13 14 15", TP="8", DP="1", HOST="127.0.0.1",
            SPEC="0", PREFIX="0", DRAFT_GRAPH="0", ENGRAM_DEVICE_INDEX="0",
            GRAPH="0", EAGER="1", MAX_LEN="4096", MAX_SEQS="1", GPU_UTIL="0.85",
            LOADER_MT="0", ALLOW_BUSY="0", I_KNOW="0", DROPCACHE="0", CPU_BIND="0",
            CPUSET="-1", MEMS="-1", MODEL_MOUNT_ALL_RW="0", EXTRA="",
            EXTRA_MODEL_MOUNTS="", KV_ARGS_EXTRA="", PYTHON_PGO="0",
            STATIC_KERNEL="0", NPUGRAPH_EX="0", SKCACHE_GC="0",
            BAT_TOKENS="8192", V41_KV32_REPACK="0", PATCH_MODE="mount")
BLOCKERS = [
    "serve_a2.sh:603-884: dynamic symlink mount discovery has no verified closed mount manifest",
    "serve_a2.sh:1680-1707: admission patch accepts failure and lacks before/after target hashes",
    "serve_a2.sh:1995-2034: generated inner shell and serve_v2.sh need joint environment/quoting review",
    "serve_a2.sh:1529-1656: container creation/exec requires outer exact-CID ownership handoff",
]


def plain_path(value):
    p = Path(value)
    if not p.is_absolute() or ".." in p.parts:
        raise ValueError("path must be absolute without parent traversal")
    for item in [*reversed(p.parents), p]:
        if item.is_symlink():
            raise ValueError(f"symlink path forbidden: {item}")
    return p


def destination(value, source):
    p = plain_path(value)
    if p.exists():
        raise ValueError("destination must be new (even existing empty directories are refused)")
    if not p.parent.is_dir():
        raise ValueError("destination parent must already exist")
    if p == source or source in p.parents or p in source.parents:
        raise ValueError("destination must not overlap reference")
    info = p.parent.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
        raise ValueError("destination parent must be caller-owned and not group/world writable")
    return p


def make_plan(reference, target, image, model, environ=None):
    environ = os.environ if environ is None else environ
    for key, value in SAFE.items():
        if key in environ and environ[key] != value:
            raise ValueError(f"unsafe ambient override: {key}")
    source = plain_path(reference)
    dest = destination(target, source)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9./_:-]*@sha256:[0-9a-f]{64}", image):
        raise ValueError("image must be an explicit immutable repository@sha256 digest")
    model_path = plain_path(model)
    # Only local reference bytes are read; a remote model need not exist locally.
    agent = plain_path(str(source / "AGENTS.md")).read_bytes()
    script = plain_path(str(source / "scripts/serve_a2.sh")).read_bytes()
    return {
        "status": "BLOCKED", "mode": "dry-plan", "launch_supported": False,
        "reference": str(source), "destination": str(dest),
        "reviewed_inputs_sha256": {"AGENTS.md": hashlib.sha256(agent).hexdigest(),
                                   "scripts/serve_a2.sh": hashlib.sha256(script).hexdigest()},
        "proposed_environment_whitelist": dict(SAFE, IMAGE=image, MODEL=str(model_path),
            OUT=str(dest / "run/out"), CACHE=str(dest / "run/cache"),
            TMPDIR=str(dest / "run/tmp")),
        "image": {"reference": image, "platform": "linux/arm64",
                  "child_digest_verification": "required externally; not verified here"},
        "blockers": BLOCKERS,
        "safety_diff": None,
        "safety_diff_status": "not generated: no safe patch claimed",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    for option in ("reference", "destination", "image", "model"):
        parser.add_argument("--" + option, required=True)
    parser.add_argument("--prepare", action="store_true", help="refused while safety blockers remain")
    args = parser.parse_args()
    try:
        plan = make_plan(args.reference, args.destination, args.image, args.model)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"BLOCKED: {exc}\n")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    # BLOCKED must never look like a successful readiness check.
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
