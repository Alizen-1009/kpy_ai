# 固定 revision 小元数据核验

revision `50029772e7757c3d9cec50481661091b369af901`。匿名直连（禁代理，无token/cookie/登录），未下载大权重或layer，未占NPU。远端只读，无创建目录。

## 已验证下载

全部 URL、UTC、服务器声明hash和实际hash见 `downloads.json`；以下13项全部大小与SHA256匹配，总 35822421 B，单文件最大17954681 B，低于32MiB/128MiB限制。

|文件|字节|已匹配SHA256|
|---|---:|---|
|README.md|41653|`90a96fa5b04ced014384126448f54b30b83b8f2d2192f7bc39e8d958d013c35f`|
|config.json|3008|`f796648afd448324b203d8990d5bcf3132322822a08340ae00be65ec8213f91b`|
|configuration.json|29|`8fa209ef18ac53dea0c47cf8d6f4e92c907565a4971bee413c1772e314a251fa`|
|engram_int8/PARTS.sha256|2421|`baba958502a4a6dc96f2e2e391eab4bff9baed1ec9ccc796fa4fc1e2b54ced78`|
|engram_int8/reassemble_engram_weights.sh|4002|`41d1d467de45a8c34a36828101ffb026ccc543ff8a01d01afcd468a06408eb1d`|
|mtpq_manifest.json|3698|`d99cfe02c0c8ce501138a70df07fc075c21ce86fdfa2430a949c1ab94e860232`|
|quant_model_description.json|11396950|`5677e007c0de3826f97993f2cc6bc5313480b3e690606c2b37f824f23a84d928`|
|quant_model_weights.safetensors.index.json|17954681|`b087a7123ab85eaade441a8dfe2c2e62a55f88f4bf76f6bb4e03e485c163aa3d`|
|release/msmodelslim/recipes/deepseek_v4_1_flash_w4a8.yaml|2582|`d3d9bdc6f2f249407dbbdb9faea8414a7d448a153c38f9ea1c36e3451deb7345`|
|release/reports/quant-repro-accuracy.md|19646|`7989b8751802647727ece29412823b1e5e3e8912bfb44d3aa936ae07f09b9b79`|
|release/reports/quant-repro-validation.md|25693|`be478f4544e763ee0494fff1b81b91f31f72f276a9b3d1cf4d2d2cbd3def2096`|
|tokenizer.json|6367257|`c90dfa01249db1be4245780a052ede752e1361c612ac6d08e2bdada7d599476b`|
|tokenizer_config.json|801|`6ac8c8dc065ed118161d02dd532749ae3f52c243deac27872134fae2f50d8547`|

## index与布局

**不能声称所有引用原样存在于120文件清单**：190728键、81个唯一引用；79个直接存在，2个Engram weight逻辑文件需要各6片重组。12片及2个scale的PARTS.sha256全部与120清单一致；重组逻辑文件预期hash与脚本一致。无其他未解析引用。权重本体尚未下载/hash，布局仅元数据验证。index.metadata.total_size=0不可用于容量。

```json
{
  "index_keys": 190728,
  "index_unique_refs": 82,
  "direct_refs": 80,
  "reassembly_refs": {
    "engram_int8/layers_14_engram_embed.weight.safetensors": {
      "parts": [
        "engram_int8/layers_14_engram_embed.weight.safetensors.part-00-of-06",
        "engram_int8/layers_14_engram_embed.weight.safetensors.part-01-of-06",
        "engram_int8/layers_14_engram_embed.weight.safetensors.part-02-of-06",
        "engram_int8/layers_14_engram_embed.weight.safetensors.part-03-of-06",
        "engram_int8/layers_14_engram_embed.weight.safetensors.part-04-of-06",
        "engram_int8/layers_14_engram_embed.weight.safetensors.part-05-of-06"
      ],
      "bytes": 98308270704,
      "sha256": "bee6e08838c75d40c4b1f5f8d7e4716aba34f90c03c17e77ad406e36188cccaa"
    },
    "engram_int8/layers_1_engram_embed.weight.safetensors": {
      "parts": [
        "engram_int8/layers_1_engram_embed.weight.safetensors.part-00-of-06",
        "engram_int8/layers_1_engram_embed.weight.safetensors.part-01-of-06",
        "engram_int8/layers_1_engram_embed.weight.safetensors.part-02-of-06",
        "engram_int8/layers_1_engram_embed.weight.safetensors.part-03-of-06",
        "engram_int8/layers_1_engram_embed.weight.safetensors.part-04-of-06",
        "engram_int8/layers_1_engram_embed.weight.safetensors.part-05-of-06"
      ],
      "bytes": 98305579120,
      "sha256": "51d28f161232e3bf600b92ef4e3c38ceb9164b801bd456503bb1a29da496ea9f"
    }
  },
  "index_groups": {
    "backbone": 185734,
    "vision": 266,
    "engram_table_scale": 4,
    "engram_extra": 6,
    "draft": 4718
  },
  "file_bytes_groups": {
    "metadata_release": 36095335,
    "engram_extra": 629310402,
    "engram_table_scale": 221190581248,
    "draft": 10624796368,
    "quarot": 104857696,
    "backbone": 292239101648,
    "vision": 970564624
  },
  "total_download_bytes": 525795307321,
  "metadata_download_bytes": 35822421,
  "peak_keep_parts_bytes": 722409157145,
  "quant_tags": {
    "FLOAT": 2169,
    "W8A8_DYNAMIC": 799,
    "W4A8_DYNAMIC": 188928,
    "1.0.0": 1
  }
}
```

## 对旧配方的具体差异

- index 187226 → 190728：+3502，超出±32。当前构成 backbone185734、draft4718、vision266、engram_extra6、Engram4。无旧版逐键index原件，不能将+3502冒充已验证逐键增删；精确逐键diff仍待旧index。
- W4A8_DYNAMIC 184320 → 188928（+4608）；W8A8_DYNAMIC 744±1 → 799（+55）；FLOAT2162±40 →2169（+7）。描述tag总数与index不相等，不能互作张量计数。
- draft manifest输入1226（旧中间态1224，+2），输出4718，4片；中间态base_bytes31104279944，量化payload10624294280，实际文件含header字节见上表。main_proj/vocab未量化，aggressive=false；不能沿用26.5GiB中间态为下载预算。
- vision仍266键；quarot由quant描述rotation_map引用optional/quarot.safetensors，不在主index中；文件存在清单。BF16/旋转同源性与矩阵shape仅发布声明，未读取权重header实证。Engram层1/14各weight+scale，extra6键独立文件；无权重payload验证不能证明FP32/group32运行时布局。

## 精确逻辑字节预算与门限

- 完整120文件一次存储：525795307321 B；本地13项小元数据 35822421 B，远端尚无新下载。
- 逐文件写同目录`.part`、hash/size通过后原地rename：下载峰值仍为525795307321 B，不加最大分片、不另设全量cache；中断保留.part计入同一文件预算，不得另起重复partial。
- 保留12片并重组两表：额外196613849824 B，峰值/最终保留722409157145 B；重组临时文件原地rename不再增加第三份。
- 这是精确payload字节，不是文件系统实际占用保证；另需目录/块分配、日志、安全余量。120文件+2重组结果至少122文件inode（顺序.part rename不双占inode；目录另算）。不批准删除parts。
- fresh远端可用：数据卷875945725952 B，扣722409157145 B剩153536568807 B；/data2可用778186674176 B，扣后剩55777517031 B。数据卷inode剩372518233，/data2剩230596875。非预留容量，下载前再检查。
- DockerRootDir=/home/docker，所在/home总390472556544 B、可用60114132992 B；只知道layer压缩10357254631 B，展开峰值未知，不能批准镜像拉取。root可用4619055104 B，禁止落大文件。
- 远端同固定config匿名HTTP200、3008 B、SHA匹配；旧任务/root/yuhao/deepinfer_910c_yh存在，拟新目录/root/yuhao/vllm_ascend_repro_yh不存在。完整时间、df -B1、df -i见remote-check.json。未扫描其他目录。

本轮小元数据门完成；大文件下载须主代理明确批准，未执行。旧逐键差异、权重内容及实际运行精度不属于已验证结论。
