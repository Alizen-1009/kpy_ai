"""Read-only stopped-container capture; never starts containers or imports ML code."""
import hashlib, json, pathlib, subprocess, tarfile, io
ROOT = pathlib.Path(__file__).resolve().parent
CID = '67993945c3595dc9bc76bbddc429c2c4d7d49be7cadd5b3d4b1bdbd7795e3525'
IMAGE = 'sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef'
def remote(*args):
    return subprocess.check_output(['ssh','-o','BatchMode=yes','910c',*args])
x = json.loads(remote('docker','inspect',CID))[0]
assert x['Id'] == CID and x['Image'] == IMAGE
assert x['State']['Status'] == 'exited' and not x['State']['Running']
old = json.loads((ROOT.parents[2]/'p1/p1-20261121T203514Z-4f842308/create-inspect.json').read_text())
assert old['Id'] == CID and old['Image'] == IMAGE
(ROOT/'inspect.json').write_text(json.dumps(x,indent=2))
manifest=[]
for rel in ['spec_decode/dflash_proposer.py','spec_decode/utils.py','ops/triton/spec_decode/utils.py']:
    src='/vllm-workspace/vllm-ascend/vllm_ascend/'+rel
    assert not any(src == m['Destination'] or src.startswith(m['Destination'].rstrip('/')+'/') for m in x['Mounts'])
    data=remote('docker','cp',CID+':'+src,'-')
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        members=[m for m in archive.getmembers() if m.isfile()]
        assert len(members)==1
        content=archive.extractfile(members[0]).read()
    dst=ROOT/'sources'/rel; dst.parent.mkdir(parents=True,exist_ok=True); dst.write_bytes(content)
    manifest.append(dict(source=src,file=str(dst.relative_to(ROOT)),sha256=hashlib.sha256(content).hexdigest()))
(ROOT/'sources.json').write_text(json.dumps(dict(image=IMAGE,cid=CID,files=manifest),indent=2)+'\n')
