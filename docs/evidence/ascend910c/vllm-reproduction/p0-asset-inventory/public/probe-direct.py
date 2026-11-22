import urllib.request, concurrent.futures,json
import probe
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
urls={k:v for k,v in probe.urls.items() if k.startswith('ms-') or k=='nju-manifest'}
results=dict(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(probe.probe,[(k+'-direct',v) for k,v in urls.items()]))
(probe.ROOT/'http-direct-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
