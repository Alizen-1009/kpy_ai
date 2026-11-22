import json, os, hashlib, urllib.request, urllib.parse
from pathlib import Path
root=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
def emit(**kw): print(json.dumps(kw),flush=True)
assert not Path('/proc/2210671').exists(), 'PID still present'
emit(event='pid_absent',pid=2210671)
rows=json.loads(input())
remaining=0
for r in rows:
 p=root/'model'/r['Path']; part=Path(str(p)+'.part')
 if not p.exists(): remaining+=r['Size']-(part.stat().st_size if part.exists() else 0)
v=os.statvfs(root); free=v.f_bavail*v.f_frsize
emit(event='budget',free=free,remaining=remaining,extra=196613849824,reserve=68719476736,required=remaining+196613849824+68719476736)
class Redirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  u=urllib.parse.urlsplit(newurl)
  emit(event='redirect',status=code,hostname=u.hostname)
  if u.scheme!='https' or u.hostname!='cdn-lfs-cn-1.modelscope.cn': raise ValueError('redirect forbidden')
  return urllib.request.Request(newurl,headers={'Range':req.get_header('Range')})
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),Redirect())
for r in rows:
 if not any('weights-%05d-'%i in r['Path'] for i in range(33,37)): continue
 p=root/'model'/r['Path']; part=Path(str(p)+'.part')
 sizes={suffix:(Path(str(p)+suffix).stat().st_size if Path(str(p)+suffix).exists() else None) for suffix in ('','.part','.part.lock')}
 emit(event='sizes',path=r['Path'],expected=r['Size'],sha256=r['Sha256'],sizes=sizes)
 n=sizes['.part'] or 0
 if n==r['Size']:
  h=hashlib.sha256()
  with part.open('rb') as f:
   for c in iter(lambda:f.read(1048576),b''):h.update(c)
  emit(event='full_part_hash',path=r['Path'],sha256=h.hexdigest(),match=h.hexdigest()==r['Sha256'].lower())
 start=max(0,n-1048576); end=max(0,n-1)
 url='https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend/repo?'+urllib.parse.urlencode({'Revision':'50029772e7757c3d9cec50481661091b369af901','FilePath':r['Path']})
 try:
  with op.open(urllib.request.Request(url,headers={'Range':f'bytes={start}-{end}'}),timeout=30) as resp:
   cr=resp.headers.get('Content-Range'); status=resp.getcode()
   emit(event='range_headers',path=r['Path'],status=status,content_range=cr,hostname=urllib.parse.urlsplit(resp.geturl()).hostname,start=start,end=end)
   if status!=206 or cr!=f'bytes {start}-{end}/{r["Size"]}': continue
   data=resp.read(end-start+1)
   with part.open('rb') as f:f.seek(start); local=f.read(len(data))
   emit(event='range_body',path=r['Path'],bytes=len(data),expected=end-start+1,tail_match=(data==local if n else None))
 except Exception as e:emit(event='probe_error',path=r['Path'],error_type=type(e).__name__)
