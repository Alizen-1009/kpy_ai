"""Offline regression tests: never invokes a real Docker daemon."""
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import container_gate as gate

CID = "a" * 64
IMAGE = "sha256:" + "b" * 64


def record():
    return {
        "Id": CID, "Image": IMAGE,
        "Config": {"Labels": {"owner": "yuhao-vllm-repro", "run_id": "trial"}},
        "HostConfig": {"Privileged": False, "PidMode": "", "IpcMode": "private",
                       "NetworkMode": "host", "CapAdd": None, "DeviceCgroupRules": None,
                       "DeviceRequests": None,
                       "Devices": [{"PathOnHost": p, "PathInContainer": p}
                                   for p in sorted(gate.DEVICES)]},
        "Mounts": [{"Type": "bind", "Source": "/shared/model", "Destination": "/model", "RW": False},
                   {"Type": "bind", "Source": "/tasks/trial", "Destination": "/task", "RW": True}],
    }


def check(value):
    return gate.validate_inspect(value, CID, IMAGE, "trial", ["/shared/model"], ["/tasks/trial"])


class GateTests(unittest.TestCase):
    def test_good_and_pure(self):
        value = record()
        before = copy.deepcopy(value)
        self.assertEqual(check(value), [])
        self.assertEqual(value, before)

    def test_bad_identity(self):
        for key, val in [("Id", "a" * 12), ("Id", "c" * 64), ("Image", "model:latest")]:
            with self.subTest(key=key, val=val):
                value = record()
                value[key] = val
                self.assertTrue(check(value))
        for key in ["owner", "run_id"]:
            value = record()
            value["Config"]["Labels"][key] = "forged"
            self.assertTrue(check(value))

    def test_unsafe_host_settings(self):
        for key, val in [("Privileged", True), ("PidMode", "host"), ("IpcMode", "host"),
                         ("CapAdd", ["SYS_ADMIN"]), ("DeviceCgroupRules", ["c *:* rwm"])]:
            with self.subTest(key=key):
                value = record()
                value["HostConfig"][key] = val
                self.assertTrue(check(value))

    def test_die0_and_remapped_device(self):
        for device in [{"PathOnHost": "/dev/davinci0", "PathInContainer": "/dev/davinci0"},
                       {"PathOnHost": "/dev/davinci8", "PathInContainer": "/dev/davinci0"}]:
            value = record()
            value["HostConfig"]["Devices"][0] = device
            self.assertTrue(check(value))

    def test_mounts(self):
        for source, dest, rw in [("/", "/host", False), ("/root", "/host", False),
                                 ("/dev", "/host", False), ("/var/run/docker.sock", "/sock", False),
                                 ("/shared/model", "/model", True),
                                 ("/tasks/trial", "/model/cache", True)]:
            with self.subTest(source=source, dest=dest):
                value = record()
                value["Mounts"].append({"Type": "bind", "Source": source, "Destination": dest, "RW": rw})
                self.assertTrue(check(value))

    def test_malformed(self):
        for value in [None, [], {}, {"HostConfig": []}]:
            self.assertTrue(check(value))
        self.assertTrue(gate.validate_inspect(record(), "short", IMAGE, "trial", [], []))

    def invoke(self, saved, live=None, cleanup=False):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "inspect.json"
            path.write_text(json.dumps([saved]), encoding="utf-8")
            argv = ["--inspect-json", str(path), "--expected-full-cid", CID,
                    "--expected-image-id", IMAGE, "--run-id", "trial",
                    "--allowed-ro-sources", "/shared/model",
                    "--allowed-rw-task-sources", "/tasks/trial"]
            if cleanup:
                argv.append("--cleanup")
            with patch.object(gate.subprocess, "run") as run, patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO):
                run.return_value.stdout = json.dumps([live if live is not None else saved])
                result = gate.main(argv)
                return result, run.call_args_list

    def test_default_is_offline(self):
        self.assertEqual(self.invoke(record()), (0, []))

    def test_cleanup_exact_cid(self):
        result, calls = self.invoke(record(), cleanup=True)
        self.assertEqual(result, 0)
        self.assertEqual([c.args[0] for c in calls], [
            ["docker", "inspect", "--type", "container", CID],
            ["docker", "stop", CID], ["docker", "rm", CID]])
        self.assertTrue(all("shell" not in c.kwargs for c in calls))

    def test_failed_validation_never_deletes(self):
        bad = record()
        bad["Config"]["Labels"]["run_id"] = "other"
        result, calls = self.invoke(bad, cleanup=True)
        self.assertEqual((result, len(calls)), (1, 0))
        result, calls = self.invoke(record(), live=bad, cleanup=True)
        self.assertEqual((result, len(calls)), (1, 1))
        self.assertEqual(calls[0].args[0][1], "inspect")


if __name__ == "__main__":
    unittest.main()
