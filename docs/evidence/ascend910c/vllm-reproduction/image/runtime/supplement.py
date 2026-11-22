from pathlib import Path
import subprocess
p=Path(__file__).parent
s=(p/'check.py').read_text()
a=s.index("code=r'''"); b=s.index("\n'''",a)+4
code="""import pathlib,hashlib,json,subprocess
for root in ['/','/root','/opt','/workspace']:
 for p in pathlib.Path(root).glob('*BUILD*'):
  if p.is_file(): print('BUILD_INFO',str(p),p.read_text(errors='replace')[:30000])
for root in ['/vllm-workspace/vllm','/vllm-workspace/vllm-ascend']:
 r=subprocess.run(['git','-c','safe.directory='+root,'-C',root,'status','--porcelain'],capture_output=True,text=True); print('FULL_DIRTY',root,r.stdout)
for p in pathlib.Path('/usr/local/Ascend').glob('*/share/info/asc-devkit/version.info'):
 print('SDK',str(p),p.read_text())
"""
s=s[:a]+'code='+repr(code)+s[b:]
with (p/'supplement.log').open('w') as out:
 subprocess.run(['ssh','910c','python3'],input=s,text=True,stdout=out,stderr=subprocess.STDOUT,check=True)
