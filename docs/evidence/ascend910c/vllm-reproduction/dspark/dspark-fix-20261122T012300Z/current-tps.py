import urllib.request,json,time,statistics
BASE='http://127.0.0.1:18550'
MODEL='dspark-fix-20261122T012300Z'
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open(BASE+'/v1/models',timeout=10) as r:
    assert MODEL in [m['id'] for m in json.load(r)['data']]
with opener.open(BASE+'/metrics',timeout=10) as r:
    metrics=r.read().decode()
for line in metrics.splitlines():
    if not line.startswith('#') and ('vllm:num_requests_running{' in line or 'vllm:num_requests_waiting{' in line):
        assert float(line.rsplit(' ',1)[1])==0, 'service not idle'
rows=[]
for i in range(9):
    body={'model':MODEL,'messages':[{'role':'user','content':'请详细介绍矩阵乘法的原理、计算步骤以及在神经网络中的应用，给出具体例子。'}], 'temperature':0,'max_tokens':256,'min_tokens':256,'ignore_eos':True,'stream':True,'stream_options':{'include_usage':True}}
    req=urllib.request.Request(BASE+'/v1/chat/completions',json.dumps(body).encode(),{'Content-Type':'application/json'})
    start=time.perf_counter(); first=None; usage=None; finish=None; events=[]
    with opener.open(req,timeout=600) as r:
        for line in r:
            now=time.perf_counter()
            if not line.startswith(b'data: '): continue
            raw=line[6:].strip()
            events.append({'t':now-start,'data':raw.decode()})
            if raw==b'[DONE]': break
            d=json.loads(raw)
            if d.get('usage'): usage=d['usage']
            for c in d.get('choices',[]):
                if c.get('delta',{}).get('content') and first is None: first=now
                if c.get('finish_reason'): finish=c['finish_reason']
    elapsed=time.perf_counter()-start
    assert usage and usage['completion_tokens']==256,(usage,finish)
    row={'warmup':i==0,'elapsed_s':elapsed,'ttft_s':None if first is None else first-start,'usage':usage,'finish_reason':finish,'output_tps_e2e':usage['completion_tokens']/elapsed,'events':events}
    rows.append(row)
    print(json.dumps({'type':'request','index':i,**row},ensure_ascii=False),flush=True)
print(json.dumps({'type':'summary','model':MODEL,'config':'TP8/EP8 GRAPH1 DSPARK5 PREFIX0','definition':'completion_tokens / full SSE request duration (includes TTFT)','measured_requests':8,'median_output_tps_e2e':statistics.median(r['output_tps_e2e'] for r in rows[1:]),'min_output_tps_e2e':min(r['output_tps_e2e'] for r in rows[1:]),'max_output_tps_e2e':max(r['output_tps_e2e'] for r in rows[1:]),'median_ttft_s':statistics.median(r['ttft_s'] for r in rows[1:]),'note':'short prompt, not aligned 2048/256 benchmark; chunk times are not token ITL'}),flush=True)
