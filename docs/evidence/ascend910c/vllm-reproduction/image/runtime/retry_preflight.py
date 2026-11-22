import pathlib,json,uuid
p=pathlib.Path(__file__).parent
s=(p/'p1_preflight.py').read_text()
a=s.index("probe=r'''")
prefix="import pathlib,json,subprocess,uuid\nout=pathlib.Path("+repr(str(p))+")\nrunid=uuid.uuid4().hex\nspecs=[]\n"
mp=json.loads((p.parents[1]/'launch/runtime-map.json').read_text()); records=json.loads((p/'frozen-payload.json').read_text())
for r in records:
 m=next(m for m in mp['mounts'] if m['source_relative_to_repo']==r['source'])
 prefix+='specs.extend('+repr(['--mount','type=bind,src='+r['destination']+',dst='+m['destination']+',readonly'])+')\n'
s=prefix+s[a:]
s=s.replace("'--entrypoint','/bin/bash'","'--env','TMPDIR=/dev/shm','--entrypoint','/bin/bash'")
s=s.replace("'--env','TMPDIR=/dev/shm'", "'--env','TMPDIR=/dev/shm','--env','TRITON_CACHE_DIR=/dev/shm/triton','--env','NUMBA_CACHE_DIR=/dev/shm/numba','--env','XDG_CACHE_HOME=/dev/shm/cache'")
s=s.replace('/dev/shm','/tmp')
s=s.replace("'--env','TMPDIR=/tmp'", "'--tmpfs','/tmp:rw,exec,nosuid,size=512m','--env','TMPDIR=/tmp'")
s=s.replace("l[:800]", "' | '.join(lines[max(0,i-1):i+10])[:3000]")
s=s.replace("p1-preflight.log","p1-preflight-tmpfs.log")
exec(compile(s,__file__,'exec'))
