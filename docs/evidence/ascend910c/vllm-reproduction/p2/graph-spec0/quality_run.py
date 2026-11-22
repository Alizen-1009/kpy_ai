import pathlib,subprocess,json,os,shutil
B=pathlib.Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh'); E=B/'quality-run/graph-spec0'; O=B/'quality-run/p2-20261121T210612Z'; os.chdir(E)
rid=(E/'run-id.txt').read_text(); py=str(O/'venv/bin/python'); official=O/'official1017'; images=official/'inference/examples/images'; assert images.is_dir() and (official/'encoding').is_dir()
for n in ['reference','gsm8k','official1017']:
 if not (E/n).exists(): (E/n).symlink_to(O/n)
for n in ['gsm_wire_client.py','vision_wire.py']: shutil.copy2(O/n,E/n)
shutil.copy2(B/'quality-run/context8192/code128_client.py',E/'code128_client.py')
env=dict(os.environ,ENC_DIR=str(official/'encoding'),GSM_WIRE_DIR=str(E/'gsm200-wire'))
for n in ['acc_eval.py','vision_accuracy_check.py']:
 p=subprocess.run([py,str(E/'reference/tests'/n),'--help'],env=env,capture_output=True,text=True); (E/(n+'.help')).write_text(p.stdout+p.stderr); assert p.returncode==0
stages=[('gsm200',[py,'gsm_wire_client.py','--task','gsm8k','--limit','200','--base-url','http://127.0.0.1:18550','--model',rid,'--gsm8k-data-dir',str(O/'gsm8k'),'--enc-dir',str(official/'encoding'),'--conc','1','--mode','chat','--max-tokens','1024','--out','gsm200.json']),('code128',['python3','code128_client.py','--model',rid,'--image','sha256:1f2c08195c5b119aa9a107861fa2efa5d2b93b161f1ae91cb5358923a78cbcef','--out','code128','--execute','--timeout','1800']),('vision23',[py,'vision_wire.py','--server','http://127.0.0.1:18550','--model',rid,'--official-dir',str(official),'--images-dir',str(images),'--min-hit-rate','1.0','--max-tokens','32','--temperature','0','--out','vision23.json'])]
for name,a in stages:
 (E/(name+'-argv.json')).write_text(json.dumps(a)); p=subprocess.run(a,env=env,capture_output=True,text=True); (E/(name+'.log')).write_text(p.stdout+p.stderr); (E/(name+'-exit.txt')).write_text(str(p.returncode))
 if p.returncode: print(name,p.returncode,flush=True); break
(E/'QUALITY_FINISHED').write_text('Inspect scores and wires; not an automatic PASS')
cid=(E/'container.cid').read_text().strip(); p=subprocess.run(['docker','logs',cid],capture_output=True,text=True); (E/'container.log').write_text(p.stdout+p.stderr)
