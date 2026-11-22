import datetime,hashlib,json,os,re,stat,time
from pathlib import Path
root=Path('/root/syf/data_yf/yuhao_vllm_ascend_repro_yh')
manifest=root/'tools/model-files.json'
raw=manifest.read_bytes(); rows=json.loads(raw)
assert len(rows)==120 and len({r['Path'] for r in rows})==120
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=root/'logs'/('completed-hash-audit_'+stamp+'.json')
report={'started_utc':stamp,'manifest_sha256':hashlib.sha256(raw).hexdigest(),'manifest_count':120,'all_120_verified':False,'pid':os.getpid(),'records':[],'status':'running'}
def save():
    tmp=out.with_suffix('.json.tmp'); tmp.write_text(json.dumps(report,indent=2)); tmp.replace(out)
def metadata(s):
    return {'size':s.st_size,'mtime_ns':s.st_mtime_ns,'inode':s.st_ino,'device':s.st_dev,'ctime_ns':s.st_ctime_ns}
print(json.dumps({'event':'start','report':str(out),'manifest_sha256':report['manifest_sha256']}),flush=True)
save()
for row in rows:
    name=row['Path']; rec={'path':name,'expected_bytes':row['Size'],'expected_sha256':row['Sha256']}
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    if '.part' in Path(name).suffixes or name.endswith('.lock') or re.search(r'quant_model_weights-000(?:33|34|35|36)',name):
        rec['status']='excluded'
    else:
        p=root/'model'/name
        try:
            before=p.lstat(); rec['before']=metadata(before)
            if not stat.S_ISREG(before.st_mode): rec['status']='not_regular'
            elif before.st_size!=row['Size']: rec['status']='not_complete_size'
            else:
                h=hashlib.sha256(); count=0
                with p.open('rb') as f:
                    opened=os.fstat(f.fileno())
                    while True:
                        block=f.read(8*1024*1024)
                        if not block: break
                        count+=len(block); h.update(block)
                    finished=os.fstat(f.fileno())
                after=p.lstat(); rec.update(bytes=count,sha256=h.hexdigest(),after=metadata(after))
                stable=all(metadata(s)==metadata(before) for s in (opened,finished,after))
                rec['status']='verified' if stable and count==row['Size'] and h.hexdigest()==row['Sha256'].lower() else ('changed_during_read' if not stable else 'HASH_MISMATCH')
        except FileNotFoundError: rec['status']='missing'
        except Exception as e: rec.update(status='error',error=str(e))
    report['records'].append(rec); save(); print(json.dumps(rec),flush=True)
    if rec['status']=='HASH_MISMATCH':
        report['status']='stopped_hash_mismatch'; save(); raise SystemExit(2)
report['status']='completed_scoped_audit'; report['finished_unix']=time.time()
report['verified_count']=sum(r['status']=='verified' for r in report['records'])
report['verified_bytes']=sum(r.get('bytes',0) for r in report['records'] if r['status']=='verified')
save(); print(json.dumps({'event':'done','report':str(out),'verified_count':report['verified_count'],'verified_bytes':report['verified_bytes'],'all_120_verified':False}),flush=True)
