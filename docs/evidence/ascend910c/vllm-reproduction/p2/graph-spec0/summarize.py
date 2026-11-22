import pathlib,json,base64,collections
E=pathlib.Path(__file__).parent
out={}
for group in ['gsm200-wire','vision-wire']:
 rows=[]
 for p in (E/group).glob('*.json'):
  r=json.loads(p.read_text()); raw=base64.b64decode(r['response_body_base64']).decode(); objs=[]
  try: objs=[json.loads(raw)]
  except Exception:
   for line in raw.splitlines():
    if line.startswith('data: ') and line[6:]!='[DONE]':
     try: objs.append(json.loads(line[6:]))
     except Exception: pass
  finishes=[c['finish_reason'] for o in objs for c in o.get('choices',[]) if c.get('finish_reason')]
  req=json.loads(base64.b64decode(r['request_body_base64'])) if r['request_body_base64'] else {}
  rows.append({'file':p.name,'finish':finishes,'usage':[o['usage'] for o in objs if o.get('usage')],'max_tokens':req.get('max_tokens'),'temperature':req.get('temperature'),'error':r['error']})
 out[group]={'finishes':dict(collections.Counter(f for r in rows for f in r['finish'])),'rows':rows}
(E/'wire-summary.json').write_text(json.dumps(out,indent=2)); print({k:v['finishes'] for k,v in out.items()})
