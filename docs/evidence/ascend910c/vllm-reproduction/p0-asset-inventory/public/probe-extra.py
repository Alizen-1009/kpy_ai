import concurrent.futures,json
from probe import probe, ROOT
base='https://modelscope.cn/api/v1/models/chiro2001/DeepSeek-V4.1-Flash-w4a8-Ascend'
urls={
'ms-com-model':base.replace('modelscope.cn','modelscope.com'),
'ms-com-files':base.replace('modelscope.cn','modelscope.com')+'/repo/files?Revision=master&Recursive=true',
'github-fixed-readme':'https://raw.githubusercontent.com/chiro2001/deepseek-v4.1-flash-ascend910B/ab88ff84efa7970875f3f8cc38dfcb06c491b154/README.md',
'github-fixed-repro':'https://raw.githubusercontent.com/chiro2001/deepseek-v4.1-flash-ascend910B/ab88ff84efa7970875f3f8cc38dfcb06c491b154/REPRO.md',
'quay-arm64':'https://quay.io/v2/ascend/vllm-ascend/manifests/sha256:16a57b897a2f475f85b0e90df1644c9870c2418b368b2adf447c5173eae211c3',
}
results=dict(concurrent.futures.ThreadPoolExecutor(max_workers=5).map(probe,urls.items()))
(ROOT/'http-extra-results.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
