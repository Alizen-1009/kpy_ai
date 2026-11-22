"""Regression tests for the explicitly BLOCKED offline preparation gate."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prepare_launch", ROOT / "scripts/vllm_ascend_repro/prepare_launch.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PreparationGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.base.chmod(0o700)
        self.source = ROOT / "ref/deepseek-v4.1-flash-ascend910B"
        self.target = self.base / "new-run"

    def plan(self, **kw):
        args = dict(reference=str(self.source), target=str(self.target),
                    image="example.invalid/model@sha256:" + "a" * 64,
                    model="/root/syf/data_yf/yuhao_vllm_ascend_repro_yh/model", environ={})
        args.update(kw)
        return module.make_plan(**args)

    def test_blocked_without_writes(self):
        before = set(self.base.iterdir())
        plan = self.plan()
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertFalse(plan["launch_supported"])
        self.assertIsNone(plan["safety_diff"])
        self.assertEqual(before, set(self.base.iterdir()))

    def test_existing_empty_target_rejected(self):
        self.target.mkdir()
        with self.assertRaises(ValueError):
            self.plan()

    def test_symlink_ancestor_rejected(self):
        link = self.base / "link"
        link.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.plan(target=str(link / "new"))

    def test_shared_parent_rejected(self):
        self.base.chmod(0o777)
        with self.assertRaises(ValueError):
            self.plan()

    def test_unsafe_overrides_rejected(self):
        for key in ("ALLOW_BUSY", "I_KNOW", "DROPCACHE", "CPU_BIND", "EXTRA", "MODEL_MOUNT_ALL_RW"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.plan(environ={key: "unsafe"})

    def test_mutable_image_rejected(self):
        with self.assertRaises(ValueError):
            self.plan(image="example/model:latest")


if __name__ == "__main__":
    unittest.main()
