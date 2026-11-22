import pathlib,json,collections
P=pathlib.Path(__file__).resolve().parent
files={x['Path']:x for x in json.loads((P.parent/'model-files.json').read_text())}; w=json.loads((P/'quant_model_weights.safetensors.index.json').read_text())['weight_map'];q=json.loads((P/'quant_model_description.json').read_text()); downloads=json.loads((P/'downloads.json').read_text())
refs=set(w.values());missing=sorted(refs-files.keys());resolved={}
for name in missing:
 parts=[name+'.part-%02d-of-06'%i for i in range(6)];assert all(p in files for p in parts)
 resolved[name]={'parts':parts,'bytes':sum(files[p]['Size'] for p in parts)}
for line in (P/'engram_int8/PARTS.sha256').read_text().splitlines():
 if not line or line.startswith('#'):continue
 h,n=line.split();n='engram_int8/'+n
 if n in files:assert files[n]['Sha256']==h
 else:resolved[n]['sha256']=h
counts=collections.Counter();sizes=collections.Counter()
def group(n):
 if n.startswith('quant_model_weights-'):return 'backbone'
 if n.startswith('mtpq-'):return 'draft'
 if n.startswith('vision-'):return 'vision'
 if n=='engram_extra.safetensors':return 'engram_extra'
 if n.startswith('engram_int8/') and ('.part-' in n or n.endswith('.safetensors')):return 'engram_table_scale'
 if n.startswith('optional/'):return 'quarot'
 return 'metadata_release'
for n in w.values():counts[group(n)]+=1
for n,x in files.items():sizes[group(n)]+=x['Size']
total=sum(x['Size'] for x in files.values());extra=sum(x['bytes'] for x in resolved.values());meta=sum(x['Size'] for x in downloads)
a={'index_keys':len(w),'index_unique_refs':len(refs),'direct_refs':len(refs)-len(missing),'reassembly_refs':resolved,'index_groups':counts,'file_bytes_groups':sizes,'total_download_bytes':total,'metadata_download_bytes':meta,'peak_keep_parts_bytes':total+extra,'quant_tags':dict(collections.Counter(v for v in q.values() if isinstance(v,str)))}
(P/'analysis.json').write_text(json.dumps(a,indent=2)+'\n')
s='# 固定 revision 小元数据核验\n\nrevision `50029772e7757c3d9cec50481661091b369af901`。匿名直连（禁代理，无token/cookie/登录），未下载大权重或layer，未占NPU。远端只读，无创建目录。\n\n## 已验证下载\n\n全部 URL、UTC、服务器声明hash和实际hash见 `downloads.json`；以下13项全部大小与SHA256匹配，总 '+str(meta)+' B，单文件最大17954681 B，低于32MiB/128MiB限制。\n\n|文件|字节|已匹配SHA256|\n|---|---:|---|\n'
for x in downloads:s+=f"|{x['Path']}|{x['Size']}|`{x['Sha256']}`|\n"
s+='\n## index与布局\n\n**不能声称所有引用原样存在于120文件清单**：190728键、81个唯一引用；79个直接存在，2个Engram weight逻辑文件需要各6片重组。12片及2个scale的PARTS.sha256全部与120清单一致；重组逻辑文件预期hash与脚本一致。无其他未解析引用。权重本体尚未下载/hash，布局仅元数据验证。index.metadata.total_size=0不可用于容量。\n\n'
s+='```json\n'+json.dumps(a,ensure_ascii=False,indent=2)+'\n```\n'
s+='\n## 对旧配方的具体差异\n\n- index 187226 → 190728：+3502，超出±32。当前构成 backbone185734、draft4718、vision266、engram_extra6、Engram4。无旧版逐键index原件，不能将+3502冒充已验证逐键增删；精确逐键diff仍待旧index。\n- W4A8_DYNAMIC 184320 → 188928（+4608）；W8A8_DYNAMIC 744±1 → 799（+55）；FLOAT2162±40 →2169（+7）。描述tag总数与index不相等，不能互作张量计数。\n- draft manifest输入1226（旧中间态1224，+2），输出4718，4片；中间态base_bytes31104279944，量化payload10624294280，实际文件含header字节见上表。main_proj/vocab未量化，aggressive=false；不能沿用26.5GiB中间态为下载预算。\n- vision仍266键；quarot由quant描述rotation_map引用optional/quarot.safetensors，不在主index中；文件存在清单。BF16/旋转同源性与矩阵shape仅发布声明，未读取权重header实证。Engram层1/14各weight+scale，extra6键独立文件；无权重payload验证不能证明FP32/group32运行时布局。\n\n## 精确逻辑字节预算与门限\n\n'
s+=f'- 完整120文件一次存储：{total} B；本地13项小元数据 {meta} B，远端尚无新下载。\n- 逐文件写同目录`.part`、hash/size通过后原地rename：下载峰值仍为{total} B，不加最大分片、不另设全量cache；中断保留.part计入同一文件预算，不得另起重复partial。\n- 保留12片并重组两表：额外{extra} B，峰值/最终保留{total+extra} B；重组临时文件原地rename不再增加第三份。\n'
s+='- 这是精确payload字节，不是文件系统实际占用保证；另需目录/块分配、日志、安全余量。120文件+2重组结果至少122文件inode（顺序.part rename不双占inode；目录另算）。不批准删除parts。\n- fresh远端可用：数据卷875945725952 B，扣722409157145 B剩153536568807 B；/data2可用778186674176 B，扣后剩55777517031 B。数据卷inode剩372518233，/data2剩230596875。非预留容量，下载前再检查。\n- DockerRootDir=/home/docker，所在/home总390472556544 B、可用60114132992 B；只知道layer压缩10357254631 B，展开峰值未知，不能批准镜像拉取。root可用4619055104 B，禁止落大文件。\n- 远端同固定config匿名HTTP200、3008 B、SHA匹配；旧任务/root/yuhao/deepinfer_910c_yh存在，拟新目录/root/yuhao/vllm_ascend_repro_yh不存在。完整时间、df -B1、df -i见remote-check.json。未扫描其他目录。\n\n本轮小元数据门完成；大文件下载须主代理明确批准，未执行。旧逐键差异、权重内容及实际运行精度不属于已验证结论。\n'
(P/'RESULT.md').write_text(s)
