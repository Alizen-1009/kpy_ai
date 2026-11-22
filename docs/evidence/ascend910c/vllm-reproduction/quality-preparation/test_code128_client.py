"""Offline tests only: no model request, Docker daemon or generated code execution."""
import json
import unittest
from unittest.mock import MagicMock, patch
import code128_client as c


def inspection(image):
    return {'Image': image, 'Config': {'User': '65534:65534'}, 'Mounts': [],
            'HostConfig': dict(Privileged=False, NetworkMode='none', ReadonlyRootfs=True,
                              PidMode='', IpcMode='private', Runtime='runc', Devices=[],
                              DeviceRequests=None, DeviceCgroupRules=None, CapAdd=None,
                              CapDrop=['ALL'], SecurityOpt=['no-new-privileges'],
                              Memory=256*1024**2, MemorySwap=256*1024**2,
                              NanoCpus=10**9, PidsLimit=64,
                              Tmpfs={'/tmp': 'rw,noexec,nosuid,nodev,size=32m'})}


class ClientTests(unittest.TestCase):
    def test_isolation_gate_positive(self):
        c.validate_sandbox(inspection('image'), 'image')

    def test_isolation_gate_rejects_each_escape(self):
        changes = {'Privileged': True, 'NetworkMode': 'host', 'ReadonlyRootfs': False,
                   'PidMode': 'host', 'IpcMode': 'host', 'Runtime': 'ascend',
                   'Devices': [{'PathOnHost': '/dev/davinci0'}],
                   'DeviceRequests': [{}], 'DeviceCgroupRules': ['a *:* rwm'],
                   'CapAdd': ['SYS_ADMIN'], 'CapDrop': [], 'SecurityOpt': [],
                   'Memory': 0, 'MemorySwap': -1, 'NanoCpus': 0, 'PidsLimit': -1,
                   'Tmpfs': {}}
        for field, value in changes.items():
            with self.subTest(field=field):
                info = inspection('image')
                info['HostConfig'][field] = value
                with self.assertRaises(ValueError):
                    c.validate_sandbox(info, 'image')
        for field, value in [('Image', 'other'), ('Config', {'User': 'root'}),
                             ('Mounts', [{'Type': 'bind', 'Destination': '/tmp'}])]:
            with self.subTest(field=field):
                info = inspection('image')
                info[field] = value
                with self.assertRaises(ValueError):
                    c.validate_sandbox(info, 'image')

    def test_gate_failure_never_starts_and_cleans(self):
        cid, image = 'a'*64, 'sha256:'+'b'*64
        bad = inspection(image)
        bad['HostConfig']['Privileged'] = True
        with patch.object(c, 'bounded', side_effect=[
                json.dumps([{'Id': image, 'Config': {}}]).encode(), cid.encode(), b'']) as run, \
             patch.object(c, 'owned', return_value=bad):
            with self.assertRaisesRegex(ValueError, 'isolation'):
                c.sandbox(image, 'lru_cache', 'not executed', [])
            self.assertFalse(any(call.args[0][1] == 'start' for call in run.call_args_list))
            self.assertEqual(run.call_args_list[-1].args[0], ['docker', 'rm', '-f', cid])
    def test_missing_usage(self):
        self.assertEqual(c.wire_fields({'choices':[{}]}),
                         {'usage':None, 'finish_reason':None})

    def test_summary_range(self):
        counts = [17,16,16,16,15,17,16,15]
        for n in range(129):
            remaining = n
            rows = []
            for total in counts:
                passed = min(remaining, total)
                remaining -= passed
                rows.append({'score':dict(passed=passed, total=total)})
            self.assertEqual(c.summary(rows)['passed'], n)
        with self.assertRaises(ValueError):
            c.summary([])

    def test_original_counts(self):
        w = c.workloads()
        self.assertEqual([len(w.fixed_unit_cases(t.task_id)) for t in w.CODE_TASKS],
                         [17,16,16,16,15,17,16,15])

    def test_cleanup_refuses_wrong_id(self):
        cid = 'a'*64
        with patch.object(c, 'bounded', return_value=json.dumps([
                {'Id':'b'*64, 'Config':{'Labels':{c.LABEL:'token'}}}]).encode()) as run:
            with self.assertRaises(ValueError):
                c.cleanup(cid, 'token')
            self.assertEqual(run.call_count, 1)
        with patch.object(c, 'bounded') as run:
            with self.assertRaises(ValueError):
                c.cleanup('short-id', 'token')
            run.assert_not_called()

    def test_cleanup_refuses_wrong_owner(self):
        cid = 'a'*64
        with patch.object(c, 'bounded', return_value=json.dumps([
                {'Id':cid, 'Config':{'Labels':{c.LABEL:'other'}}}]).encode()) as run:
            with self.assertRaises(ValueError):
                c.cleanup(cid, 'token')
            self.assertEqual(run.call_count, 1)

    def test_timeout_and_output_limit(self):
        for ready, chunk, error in [(False, b'', TimeoutError),
                                     (True, b'x'*11, ValueError)]:
            with self.subTest(error=error), \
                 patch.object(c.subprocess, 'Popen') as popen, \
                 patch.object(c.selectors, 'DefaultSelector') as selector, \
                 patch.object(c.os, 'read', return_value=chunk):
                proc = popen.return_value
                proc.poll.return_value = None
                selector.return_value.__enter__.return_value.select.return_value = ready
                with self.assertRaises(error):
                    c.bounded(['mock'], limit=10)
                proc.kill.assert_called_once()
                proc.wait.assert_called_once()

    def test_start_failure_still_cleans_full_id(self):
        cid, image = 'a'*64, 'sha256:'+'b'*64
        calls = []
        def run(argv, *args, **kwargs):
            calls.append(argv)
            if argv[1:3] == ['image', 'inspect']:
                return json.dumps([{'Id':image, 'Config':{}}]).encode()
            if argv[1] == 'create':
                return cid.encode()
            if argv[1] == 'start':
                raise TimeoutError('mock')
            return b''
        with patch.object(c, 'bounded', side_effect=run), patch.object(c, 'owned', return_value=inspection(image)) as owned:
            with self.assertRaises(TimeoutError):
                c.sandbox(image, 'lru_cache', 'not executed', [])
            self.assertEqual(calls[-1], ['docker','rm','-f',cid])
            self.assertEqual(owned.call_count, 2)
            create = calls[1]
            for flag in ['--network=none','--read-only','--cap-drop=ALL',
                         '--security-opt=no-new-privileges','--memory=256m',
                         '--cpus=1','--pids-limit=64','--pull=never']:
                self.assertIn(flag, create)
            self.assertNotIn('--device', create)
            self.assertNotIn('--volume', create)


if __name__ == '__main__':
    unittest.main()
