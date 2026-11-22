"""Fail-closed Docker inspect acceptance gate; not proof of runtime isolation.

Host networking is permitted: a subsequent listener check must verify API loopback
binding. Saved inspect JSON is only evidence, not authenticated live state.
"""
import argparse
import json
import posixpath
import re
import subprocess
import sys

DEVICES = {f"/dev/davinci{i}" for i in range(8, 16)} | {
    "/dev/davinci_manager", "/dev/devmm_svm", "/dev/hisi_hdc"
}


def _path(value):
    return (isinstance(value, str) and value.startswith("/")
            and not value.startswith("//") and posixpath.normpath(value) == value)


def validate_inspect(record, expected_full_cid, expected_image_id, run_id,
                     allowed_ro_sources, allowed_rw_task_sources):
    """Return errors without I/O. Allowlisted sources are exact canonical paths."""
    errors = []
    if not isinstance(expected_full_cid, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_full_cid):
        errors.append("expected CID must be full 64 lowercase hex")
    if not isinstance(expected_image_id, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", expected_image_id):
        errors.append("expected image must be sha256 ID")
    if not isinstance(run_id, str) or not run_id.strip():
        errors.append("run_id required")
    sets = []
    for sources in (allowed_ro_sources, allowed_rw_task_sources):
        if not isinstance(sources, (list, tuple, set, frozenset)) or any(
                not _path(p) or p in {"/", "/root", "/dev"} for p in sources):
            errors.append("invalid source allowlist")
            sets.append(set())
        else:
            sets.append(set(sources))
    ro, rw = sets
    if ro & rw:
        errors.append("source allowlists overlap")
    if not isinstance(record, dict):
        return errors + ["inspect record must be an object"]
    if record.get("Id") != expected_full_cid:
        errors.append("CID mismatch")
    if record.get("Image") != expected_image_id:
        errors.append("image mismatch")
    config = record.get("Config")
    labels = config.get("Labels") if isinstance(config, dict) else None
    if not isinstance(labels, dict) or labels.get("owner") != "yuhao-vllm-repro" or labels.get("run_id") != run_id:
        errors.append("ownership labels mismatch")
    host = record.get("HostConfig")
    if not isinstance(host, dict):
        return errors + ["HostConfig missing"]
    if host.get("Privileged") is not False:
        errors.append("Privileged must be false")
    for key, allowed in (("PidMode", {"", "private"}),
                         ("IpcMode", {"private", "shareable"})):
        if not isinstance(host.get(key), str) or host[key] not in allowed:
            errors.append(key + " must use an independent namespace")
    for key in ("DeviceCgroupRules", "CapAdd", "DeviceRequests"):
        if key not in host or host[key] not in (None, []):
            errors.append(key + " must be empty")
    devices = host.get("Devices")
    if not isinstance(devices, list) or len(devices) != len(DEVICES) or any(
        not isinstance(d, dict) or not isinstance(d.get("PathOnHost"), str) or d.get("PathOnHost") not in DEVICES
        or d.get("PathInContainer") != d.get("PathOnHost") for d in devices
    ) or {d.get("PathOnHost") for d in devices if isinstance(d, dict)} != DEVICES:
        errors.append("device set must be exactly dies8-15 plus management devices")
    mounts = record.get("Mounts")
    if not isinstance(mounts, list):
        return errors + ["Mounts missing"]
    destinations = []
    for mount in mounts:
        if not isinstance(mount, dict):
            errors.append("invalid mount")
            continue
        src, dst, writable = mount.get("Source"), mount.get("Destination"), mount.get("RW")
        if not _path(src) or not _path(dst):
            errors.append("mount paths must be canonical absolute paths")
            continue
        if mount.get("Type") != "bind":
            errors.append("only allowlisted bind mounts permitted")
        if src in {"/", "/root", "/dev"} or dst in {"/", "/root", "/dev"}:
            errors.append("broad mount prohibited")
        if "docker.sock" in src or "docker.sock" in dst or src in {"/run", "/var", "/var/run"} or dst in {"/run", "/var", "/var/run"}:
            errors.append("Docker socket exposure prohibited")
        if not ((src in ro and writable is False) or (src in rw and writable is True)):
            errors.append("mount source/mode not allowlisted")
        if any(dst == other for other, _ in destinations):
            errors.append("duplicate mount destination")
        destinations.append((dst, writable))
    for dst, _ in destinations:
        if any(dst.startswith(parent + "/") and mode is False for parent, mode in destinations):
            errors.append("submount overrides readonly directory")
    return errors


def _record(data):
    if isinstance(data, list) and len(data) == 1:
        return data[0]
    if isinstance(data, dict):
        return data
    raise ValueError("inspect JSON must contain exactly one record")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect-json", required=True)
    parser.add_argument("--expected-full-cid", required=True)
    parser.add_argument("--expected-image-id", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--allowed-ro-sources", nargs="*", required=True)
    parser.add_argument("--allowed-rw-task-sources", nargs="*", required=True)
    parser.add_argument("--cleanup", action="store_true")
    args = parser.parse_args(argv)
    def check(record):
        errors = validate_inspect(record, args.expected_full_cid, args.expected_image_id,
                                  args.run_id, args.allowed_ro_sources, args.allowed_rw_task_sources)
        if errors:
            raise ValueError("; ".join(errors))
    try:
        with open(args.inspect_json, encoding="utf-8") as stream:
            check(_record(json.load(stream)))
        if args.cleanup:
            cid = args.expected_full_cid
            result = subprocess.run(["docker", "inspect", "--type", "container", cid],
                                    check=True, capture_output=True, text=True)
            check(_record(json.loads(result.stdout)))
            subprocess.run(["docker", "stop", cid], check=True)
            subprocess.run(["docker", "rm", cid], check=True)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("inspect accepted" + ("; exact CID removed" if args.cleanup else "; no actions performed"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
