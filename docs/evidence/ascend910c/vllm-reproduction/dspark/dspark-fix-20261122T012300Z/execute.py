import pathlib,json,shutil,hashlib,subprocess,socket,time,urllib.request,traceback
B=pathlib.Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh'); R='dspark-fix-20261122T012300Z'; E=B/'quality-run'/R; D=B/'deployment_dspark_fix_yh'; P=B/'payload'/R
old='dspark-20261122T011131Z'; cid=None
run=lambda a: subprocess.check_output(a,text=True)
def save(n,x): (E/n).write_text(x)
try:
    assert not json.loads(run(['docker','inspect','afa344faf865692f8149dd76fdd186aa84201d93aaaee677d98dc3f009a87f9d']))[0]['State']['Running']
    s=socket.socket(); s.bind(('127.0.0.1',18550)); s.close()
    assert not D.exists() and not P.exists()
    shutil.copytree(B/'deployment_dspark_yh',D); shutil.copytree(B/'payload'/old,P)
    target=P/'patches/files/draft/dsa_v1.py'; target.chmod(0o600); shutil.copyfile(E/'patched.py',target); target.chmod(0o444)
    mp=D/'docs/evidence/ascend910c/vllm-reproduction/launch/runtime-map.json'; m=json.loads(mp.read_text()); selected=[x for x in m['mounts'] if x['selected']]; assert len(selected)==13
    for x in selected:
        h=hashlib.sha256((P/x['source_relative_to_ref']).read_bytes()).hexdigest()
        if x['source_relative_to_ref']=='patches/files/draft/dsa_v1.py': x['sha256']=h
        else: assert x['sha256']==h
    mp.write_text(json.dumps(m,indent=2)); save('runtime-map.json',mp.read_text())
    report=json.loads((B/'quality-run'/old/'runtime-report.json').read_text()); report['runtime_map_sha256']=hashlib.sha256(mp.read_bytes()).hexdigest(); report['local_minimal_bugfix']={'source':'patched.py','diff':'source.patch','cpu_regression':'cpu2.log','scope':'Local diagnostic NameError repair, differs from original release; no tensor math changes. Prior import/API prerequisites inherited, not runtime certification.'}; save('runtime-report.json',json.dumps(report,indent=2))
    import sys
    sys.path.insert(0,str(D/'scripts/vllm_ascend_repro')); import launch
    npu=run(['npu-smi','info']); save('fresh-npu.txt',npu); launch.check_npu(npu)
    a=['python3',str(D/'scripts/vllm_ascend_repro/launch.py'),'--execute','--run-dir',str(B/'runs_yh'/R),'--model',str(B/'model'),'--payload-dir',str(P),'--image-id',report['image_id'],'--run-id',R,'--port','18550','--manifest',str(D/'docs/evidence/ascend910c/vllm-reproduction/p0-asset-inventory/public/model-files.json'),'--verified-report',str(B/'logs/recovery-3-20261121T200226Z/verified_report.json'),'--reassembly-report',str(B/'logs/recovery-3-20261121T200226Z/reassembly.json'),'--runtime-report',str(E/'runtime-report.json')]
    save('launcher-argv.json',json.dumps(a)); result=subprocess.run(a,text=True,capture_output=True); save('launch.log',result.stdout+result.stderr)
    cp=B/'runs_yh'/R/'container.cid'
    if cp.exists(): cid=cp.read_text().strip(); save('container.cid',cid)
    assert result.returncode==0,result.stdout+result.stderr
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({})); base='http://127.0.0.1:18550'
    for i in range(240):
        logs=run(['docker','logs',cid]); save('container.log',logs)
        assert 'Engine core encountered an issue' not in logs and 'EngineCore failed to start' not in logs, 'engine startup failure'
        try:
            with opener.open(base+'/v1/models',timeout=5) as r: models=r.read().decode()
            assert R in models; save('models.json',models); break
        except (OSError,urllib.error.URLError): time.sleep(10)
    else: raise RuntimeError('ready timeout')
    smoke=[('chinese',[{'role':'user','content':'请用中文解释为什么天空通常是蓝色的。'}]),('code',[{'role':'user','content':'Write a Python function that returns the sum of squares of a list of integers.'}]),('multiturn',[{'role':'user','content':'记住数字17。'},{'role':'assistant','content':'好的，我记住了数字17。'},{'role':'user','content':'刚才的数字加8是多少？'}])]
    for name,messages in smoke:
        req=urllib.request.Request(base+'/v1/chat/completions',json.dumps(dict(model=R,messages=messages,temperature=0,max_tokens=128)).encode(),{'Content-Type':'application/json'})
        with opener.open(req,timeout=600) as r: text=r.read().decode()
        save('smoke-'+name+'.json',text); assert json.loads(text)['choices'][0]['message']['content']
    with opener.open(base+'/metrics') as r: save('metrics-before.txt',r.read().decode())
    script=(B/'quality-run'/old/'current-tps.py').read_text().replace(old,R); save('current-tps.py',script)
    with open(E/'current-tps.jsonl','w') as f: subprocess.run(['python3',str(E/'current-tps.py')],stdout=f,stderr=subprocess.STDOUT,check=True,timeout=6000)
    with opener.open(base+'/metrics') as r: save('metrics-after.txt',r.read().decode())
    save('SUCCESS.txt','Live service retained '+cid)
except Exception:
    save('FAILURE.txt',traceback.format_exc())
    if cid:
        save('failure-inspect.json',run(['docker','inspect',cid])); subprocess.run(['docker','stop',cid],check=True); save('stopped-inspect.json',run(['docker','inspect',cid]))
finally:
    if cid:
        p=subprocess.run(['docker','logs',cid],text=True,capture_output=True); save('container.log',p.stdout+p.stderr); save('inspect.json',run(['docker','inspect',cid]))
print((E/'FAILURE.txt').read_text() if (E/'FAILURE.txt').exists() else (E/'SUCCESS.txt').read_text(),flush=True)
