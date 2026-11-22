import json,pathlib,subprocess,time
p=pathlib.Path(__file__).resolve().parent
r=json.loads((p/'launch.json').read_text())['remote']
probe="import pathlib,json; p=pathlib.Path("+repr(r)+"); print(json.dumps({n:(p/n).read_text() if (p/n).exists() else None for n in ['process.json','exit.json']}))"
for i in range(720):
 result=subprocess.run(['ssh','-o','ConnectTimeout=20','910c','python3 -c '+__import__('shlex').quote(probe)],capture_output=True,text=True,timeout=45)
 if result.returncode:
  (p/'monitor-error.txt').write_text(result.stderr); raise SystemExit('SSH monitor failed; downloader not restarted')
 data=json.loads(result.stdout)
 (p/'process.json').write_text(data['process.json'] or '{}')
 if data['exit.json']:
  (p/'exit.json').write_text(data['exit.json'])
  subprocess.run(['scp','910c:'+r+'/download.jsonl','910c:'+r+'/supervisor.log',str(p)+'/'],check=True)
  print(data['exit.json'],flush=True); break
 if i%10==0: print('running '+str(i)+' '+data['process.json'],flush=True)
 time.sleep(60)
else: raise SystemExit('12 hour bounded wait elapsed; not declared complete')
