import urllib.request, concurrent.futures,json
from probe import probe,ROOT
urllib.request.install_opener(urllib.request.build_opener(urllib.request.ProxyHandler({})))
base='https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend/repo'
rev='50029772e7757c3d9cec50481661091b369af901'
urls={'ms-git-refs':'https://modelscope.cn/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend.git/info/refs?service=git-upload-pack','ms-pinned-files':base+'/files?Revision='+rev+'&Recursive=true','ms-reassemble':base+'?Revision='+rev+'&FilePath=engram_int8/reassemble_engram_weights.sh','ms-readme':base+'?Revision='+rev+'&FilePath=README.md'}
results=dict(concurrent.futures.ThreadPoolExecutor(max_workers=4).map(probe,urls.items()))
(ROOT/'http-pinned-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
