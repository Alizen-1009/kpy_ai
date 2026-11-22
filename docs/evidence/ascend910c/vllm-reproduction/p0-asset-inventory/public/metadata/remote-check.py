import urllib.request,hashlib,json,datetime,subprocess,os
out={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
url='https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend/repo?Revision=50029772e7757c3d9cec50481661091b369af901&FilePath=config.json'
try:
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=45) as r:
  b=r.read(3009);out['get']={'url':url,'status':r.status,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'match':len(b)==3008 and hashlib.sha256(b).hexdigest()=='f796648afd448324b203d8990d5bcf3132322822a08340ae00be65ec8213f91b'}
except Exception as e:out['get']={'error':type(e).__name__}
r=subprocess.run(['docker','info','--format','{{.DockerRootDir}}'],capture_output=True,text=True);out['docker_root']=r.stdout.strip();out['docker_rc']=r.returncode
paths=['/','/root/syf/data_yf','/data2/syf']+([r.stdout.strip()] if r.returncode==0 else [])
out['df_bytes']=subprocess.run(['df','-B1',*paths],capture_output=True,text=True).stdout
out['df_inodes']=subprocess.run(['df','-i','/root/syf/data_yf','/data2/syf'],capture_output=True,text=True).stdout
out['workspace_exists']={p:os.path.isdir(p) for p in ['/root/yuhao/deepinfer_910c_yh','/root/yuhao/vllm_ascend_repro_yh']}
print(json.dumps(out,indent=2))
