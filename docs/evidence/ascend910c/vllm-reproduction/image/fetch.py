import os, sys, json, subprocess, datetime, urllib.request, hashlib, time, signal
D='sha256:16a57b897a2f475f85b0e90df1644c9870c2418b368b2adf447c5173eae211c3'
base='/root/yuhao/vllm_image_fetch_yh_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
os.mkdir(base)
log=open(base+'/task.log','a',buffering=1)
def report(x):
 print(x,flush=True); log.write(str(x)+'\n')
def cmd(a): return subprocess.check_output(a,text=True).strip()
report('log_directory='+base)
try:
 root=cmd(['docker','info','--format','{{.DockerRootDir}}'])
 report('DockerRootDir='+root)
 def free():
  s=os.statvfs(root); return s.f_bavail*s.f_frsize
 report('initial_free_bytes='+str(free()))
 if free()<50*1024**3: raise RuntimeError('STOP: less than 50GiB free; no pull')
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 chosen=None
 for host in ['quay.nju.edu.cn','quay.io']:
  url='https://'+host+'/v2/ascend/vllm-ascend/manifests/'+D
  try:
   req=urllib.request.Request(url,headers={'Accept':'application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
   with opener.open(req,timeout=45) as r: body=r.read(1048577); status=r.status
   digest='sha256:'+hashlib.sha256(body).hexdigest()
   report(json.dumps({'url':url,'status':status,'sha256':digest}))
   if len(body)>1048576 or digest!=D: raise RuntimeError('manifest identity mismatch')
   open(base+'/'+host+'.manifest.json','wb').write(body)
   chosen=host+'/ascend/vllm-ascend@'+D; break
  except Exception as e: report(host+': '+str(e))
 if not chosen: raise RuntimeError('STOP: no anonymous verified child metadata')
 report('pre_pull_free_bytes='+str(free()))
 if free()<50*1024**3: raise RuntimeError('STOP: less than 50GiB free; no pull')
 with open(base+'/pull.log','w') as out:
  p=subprocess.Popen(['docker','pull',chosen,'--platform','linux/arm64'],stdout=out,stderr=subprocess.STDOUT)
  open(base+'/pull.pid','w').write(str(p.pid)+'\n'); report('owned_pull_pid='+str(p.pid))
  stopped=False
  while p.poll() is None:
   n=free(); report('free_bytes='+str(n))
   if n<16*1024**3:
    report('STOP: below 16GiB; terminating owned pull client only'); p.terminate(); stopped=True; break
   time.sleep(10)
  rc=p.wait(); report('pull_exit='+str(rc))
 if rc!=0 or stopped: raise RuntimeError('pull failed or stopped; see pull.log')
 result=cmd(['docker','image','inspect','--format','{"Id":{{json .Id}},"RepoDigests":{{json .RepoDigests}},"Architecture":{{json .Architecture}},"Size":{{json .Size}}}',chosen])
 open(base+'/image-inspect.json','w').write(result+'\n'); report(result)
 report('SUCCESS')
except Exception as e:
 report('ERROR: '+str(e)); sys.exit(1)
