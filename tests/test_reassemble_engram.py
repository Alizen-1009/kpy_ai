import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.vllm_ascend_repro import reassemble_engram as m


class AssemblyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        (self.root / m.MARKER).write_text(json.dumps(m.OWNER))
        self.groups = []
        for layer in (1, 14):
            rows, contents = [], b''
            for i in range(6):
                data = f'{layer}:{i}'.encode()
                name = f'l{layer}-{i}'
                (self.root / name).write_bytes(data)
                rows.append(dict(Path=name, Size=len(data), Sha256=hashlib.sha256(data).hexdigest()))
                contents += data
            self.groups.append((f'target{layer}', hashlib.sha256(contents).hexdigest(), rows))
        space = type('Space', (), {'f_bavail': 10**15, 'f_frsize': 1})()
        self.space = patch.object(m.os, 'statvfs', return_value=space)
        self.space.start()
        self.addCleanup(self.space.stop)

    def test_plan(self):
        groups = m.plan()
        self.assertEqual([sum(r['Size'] for r in g[2]) for g in groups], [98305579120, 98308270704])
        self.assertEqual([g[1] for g in groups], list(m.FINAL))
        with self.assertRaises(ValueError):
            m.plan(revision='wrong')

    def test_dry_run(self):
        with patch.object(m, 'scan', side_effect=AssertionError):
            self.assertEqual(m.run(self.root, self.groups)[0]['status'], 'planned')
        self.assertFalse((self.root / 'target1').exists())

    def test_success_and_skip(self):
        report = m.run(self.root, self.groups, True)
        self.assertEqual(report[0]['status'], 'complete')
        self.assertEqual(m.run(self.root, self.groups, True)[0]['status'], 'verified_existing')
        self.assertTrue((self.root / 'l1-0').exists())

    def test_bad_hash(self):
        (self.root / 'l1-0').write_bytes(b'bad')
        with self.assertRaises(ValueError):
            m.run(self.root, self.groups, True)
        self.assertFalse((self.root / 'target1.part').exists())

    def test_order(self):
        self.groups[0][2].reverse()
        with self.assertRaises(ValueError):
            m.run(self.root, self.groups, True)
        self.assertTrue((self.root / 'target1.part').exists())

    def test_existing(self):
        for name in ('target1', 'target1.part'):
            with self.subTest(name=name):
                path = self.root / name
                path.write_bytes(b'old')
                with self.assertRaises((ValueError, FileExistsError)):
                    m.run(self.root, self.groups, True)
                self.assertEqual(path.read_bytes(), b'old')
                path.unlink()

    def test_space(self):
        m.os.statvfs.return_value.f_bavail = m.RESERVE
        with self.assertRaises(ValueError):
            m.run(self.root, self.groups, True)

    def test_symlink(self):
        (self.root / 'l1-0').unlink()
        (self.root / 'l1-0').symlink_to(self.root / 'l1-1')
        with self.assertRaises(ValueError):
            m.run(self.root, self.groups, True)

    def test_symlink_ancestor_and_escape(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            m.run(alias, self.groups, True)
        bad = [('../outside', self.groups[0][1], self.groups[0][2])]
        with self.assertRaises(ValueError):
            m.run(self.root, bad, True)

    def test_input_changed_during_copy(self):
        original = m.scan
        def changed(path, output=None, combined=None):
            if output is not None:
                path.write_bytes(b'changed')
            return original(path, output, combined)
        with patch.object(m, 'scan', side_effect=changed):
            with self.assertRaises(ValueError):
                m.run(self.root, self.groups, True)
        self.assertTrue((self.root / 'target1.part').exists())
        self.assertFalse((self.root / 'target1').exists())

    def test_owner(self):
        (self.root / m.MARKER).write_text('{}')
        with self.assertRaises(ValueError):
            m.run(self.root, self.groups, True)

    def test_interrupt(self):
        original = m.scan
        def interrupted(path, output=None, combined=None):
            if output is not None:
                output.write(b'partial')
                raise KeyboardInterrupt
            return original(path)
        with patch.object(m, 'scan', side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt):
                m.run(self.root, self.groups, True)
        self.assertEqual((self.root / 'target1.part').read_bytes(), b'partial')
        self.assertFalse((self.root / 'target1').exists())
        self.assertTrue((self.root / 'l1-0').exists())


if __name__ == '__main__':
    unittest.main()
