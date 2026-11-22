"""Anonymous bounded metadata GETs only; no model/image payload downloads."""
import concurrent.futures, datetime, hashlib, json, pathlib, urllib.request, urllib.error
ROOT=pathlib.Path(__file__).resolve().parent
urls={
'ms-model':'https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend',
'ms-revisions':'https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend/revisions',
'ms-files':'https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend/repo/files?Revision=master&Recursive=true',
'github-repo':'https://api.github.com/repos/chiro2001/deepseek-v4.1-flash-ascend910B',
'github-readme':'https://raw.githubusercontent.com/chiro2001/deepseek-v4.1-flash-ascend910B/main/README.md',
'nju-manifest':'https://quay.nju.edu.cn/v2/ascend/vllm-ascend/manifests/deepseek-v4.1-flash-a3',
'quay-manifest':'https://quay.io/v2/ascend/vllm-ascend/manifests/deepseek-v4.1-flash-a3',
'quay-tag':'https://quay.io/api/v1/repository/ascend/vllm-ascend/tag/?specificTag=deepseek-v4.1-flash-a3',
}
def probe(item):
 name,url=item
 result={'url':url,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'public-asset-audit/1.0','Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.v2+json, application/json, text/plain'})
  try: r=urllib.request.urlopen(req,timeout=35)
  except urllib.error.HTTPError as e: r=e
  with r:
   body=r.read(1048577)
   result.update(status=r.code,final_url=r.url,headers={k:v for k,v in r.headers.items() if k.lower() in ['content-type','docker-content-digest','www-authenticate','location','date']},truncated=len(body)>1048576)
   body=body[:1048576]
   (ROOT/(name+'.body')).write_bytes(body)
   result['body_sha256']=hashlib.sha256(body).hexdigest()
 except Exception as e: result['transport_error']=str(e)
 return name,result
if __name__=='__main__':
 results=dict(concurrent.futures.ThreadPoolExecutor(max_workers=8).map(probe,urls.items()))
 (ROOT/'http-results.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results,indent=2))
