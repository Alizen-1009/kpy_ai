import json, hashlib, subprocess, shlex
from pathlib import Path
E=Path(__file__).resolve().parent
R=E.parents[4]
staging=json.loads((E.parent/'launch/staging.stdout').read_text())
local=[]
for f in staging['files']:
 rel=f['path'].split('/deployment_yh/')[1]
 p=R/rel
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 local.append(dict(path=rel,local=h,staged=f['sha256']))
 if not rel.endswith('download_assets.py'): assert h==f['sha256'],rel
(E/'local-hashes.json').write_text(json.dumps(local,indent=2))
code=(E/'remote.py').read_text().replace('STAGING_JSON',repr(staging)).replace('FROZEN_JSON',repr(json.loads((E.parent/'image/runtime/frozen-payload.json').read_text())))
with (E/'execution.stdout').open('w') as out:
 p=subprocess.run(['ssh','-o','ConnectTimeout=20','910c','python3 -u'],input=code,text=True,stdout=out,stderr=subprocess.STDOUT)
print('remote exit',p.returncode)
