import argparse
import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.vllm_ascend_repro import launch


def idle():
    evidence = launch.MAP.parent.parent / 'p0-asset-inventory/remote/inventory.stdout'
    text = evidence.read_text()
    start = text.index('| 0     Ascend910')
    end = text.index('| No running processes found in NPU 7',start)
    return text[start:text.index('\n',end)]


class LauncherTests(unittest.TestCase):
    def test_plan_has_no_commands(self):
        with patch.object(launch,'run',side_effect=AssertionError('external call')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launch.main([]),0)

    def test_missing_parameters_closed(self):
        with patch.object(launch,'run',side_effect=AssertionError('external call')), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(launch.main(['--execute']),1)

    def test_idle_all_cards(self):
        launch.check_npu(idle())

    def test_missing_or_busy_cards(self):
        for text in ('No running processes found',idle().replace('0000:83:00.0  | 0','0000:83:00.0  | 1'),idle().replace('No running processes found in NPU 6','unknown'),idle()+'\n| 5 0 123 python |',idle()+'\n| No running processes found in NPU 7 |'):
            with self.assertRaises(ValueError):
                launch.check_npu(text)

    def test_execute_mocked(self):
        for failure in (None,'inspect','planned','env'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as d:
                root = Path(d).resolve()
                model,payload = root/'model',root/'payload'
                model.mkdir(); payload.mkdir()
                def dump(path,data):
                    path.write_text(json.dumps(data)); return str(path)
                dump(model/launch.assets.MARKER,launch.assets.OWNER)
                (model/'weight').write_bytes(b'w')
                rows = [{'Path':'weight','Size':1,'Sha256':launch.digest(model/'weight')}]
                manifest = root/'manifest.json'; dump(manifest,rows)
                groups = []
                reports = []
                for target in ('one','two'):
                    (model/target).write_bytes(b'x')
                    groups.append((target,'a'*64,[{'Size':1}]))
                    reports.append(dict(path=target,sha256='a'*64,bytes=1,status='planned' if failure == 'planned' else 'complete'))
                reassembly = root/'assembly.json'; dump(reassembly,reports)
                verified = dump(root/'verified.json',dict(schema_version=1,model=str(model),manifest_sha256=launch.digest(manifest),reassembly_sha256=launch.digest(reassembly),files={'weight':rows[0]['Sha256']}))
                image_id = 'sha256:'+'a'*64
                runtime = dump(root/'runtime.json',dict(schema_version=1,image_id=image_id,runtime_map_sha256=launch.digest(launch.MAP),mapping=launch.MAPPING,cann_login_verified=True,payload_api_verified=True,image_environment_verified=True,reviewed_image_env={'PATH':'/bin'}))
                (payload/'entry').write_bytes(b'test'); (payload/'entry').chmod(0o444)
                mapping = dict(environment_whitelist={},mounts=[dict(selected=True,source_relative_to_ref='entry',destination='/opt/entry',sha256=launch.digest(payload/'entry'))])
                args = argparse.Namespace(run_dir=str(root/'task'),model=str(model),payload_dir=str(payload),image_id=image_id,run_id='test',port=8000,manifest=str(manifest),verified_report=verified,reassembly_report=str(reassembly),runtime_report=runtime)
                calls = []; create = []
                cid = 'b'*64
                def fake(argv):
                    calls.append(argv)
                    if argv[:3] == ['docker','image','inspect']:
                        return json.dumps([{'Id':image_id,'Config':{'Env':['PATH=/bad' if failure == 'env' else 'PATH=/bin']}}])
                    if argv[:2] == ['docker','create']:
                        create.extend(argv); return cid
                    if argv[:2] == ['docker','inspect']:
                        mounts = []
                        for i,x in enumerate(create):
                            if x == '--mount':
                                fields = create[i+1].split(',')
                                mounts.append(dict(Source=fields[1][4:],Destination=fields[2][4:],RW='readonly' not in fields))
                        return json.dumps([dict(HostConfig=dict(NetworkMode='host',IpcMode='private',SecurityOpt=['no-new-privileges'],Memory=768*1024**3,NanoCpus=64*10**9,PidsLimit=8192,ShmSize=16*1024**3),Mounts=mounts,Config=dict(Env=['PATH=/bin']+[create[i+1] for i,x in enumerate(create) if x == '--env'],Entrypoint=['bash'],Cmd=create[-2:]))])
                    if argv[0] == 'npu-smi': return idle()
                    return ''
                original_exists = Path.exists
                def exists(path):
                    return True if str(path) == '/usr/local/Ascend/driver' else original_exists(path)
                with patch.object(launch,'run',side_effect=fake), patch.object(launch.assembly,'plan',return_value=groups), patch.object(launch.gate,'validate_inspect',return_value=['reject'] if failure == 'inspect' else []), patch.object(Path,'exists',exists), contextlib.redirect_stdout(io.StringIO()):
                    if failure:
                        with self.assertRaises(ValueError): launch.execute(args,mapping)
                        self.assertNotIn(['docker','start',cid],calls)
                    else:
                        self.assertEqual(launch.execute(args,mapping),cid)
                        self.assertIn(['docker','start',cid],calls)
                    self.assertFalse(any(c[:2] == ['docker','rm'] for c in calls))

    def test_paths(self):
        for p in ('relative','/tmp/../etc','/tmp//a','/tmp/a,b'):
            with self.assertRaises(ValueError):
                launch.canonical(p)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            (root/'link').symlink_to(root)
            with self.assertRaises(ValueError):
                launch.canonical(str(root/'link'/'child'))


if __name__ == '__main__':
    unittest.main()
