# 官方评测小资产核验

从已授权服务器 `/root/syf/v41_inventory_yf.json` 指定的官方1017归档只读复制18文件，恢复标准相对路径。每个文件均独立核对大小及SHA256；位置、revision、hash见manifest.json。未复制或修改原始模型权重。

归档revision：`9f9818127fdfbb60feba204799d617a874b32a86`。同包LICENSE为DeepSeek MIT许可，已随复制保留。两张图片为该包自带示例；未发现本次选中文件另有排除许可的声明。此记录依据已有官方归档与其许可，不声称独立审计图片底层权利链。

- carrots.jpeg：`5df896a4a07e127281c60fc957f8b3d73f4735b3258a0bf762b4383557f8fa9a`
- corn.jpeg：`251fe7ad58f44db139a6af5ed489e027eca93ae60878b83f3e709c7d6f0112a1`
- encoding.py：`13231c592e958fb39e2af6001dae69d90e7a36b265702b9b390236fb387599e2`

本机默认Python没有pytest，首次测试未运行（test-result.txt）。随后使用隔离依赖命令：

```
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with pytest==8.3.5 python -m pytest -q -p no:cacheprovider docs/evidence/ascend910c/vllm-reproduction/quality-preparation/official1017/encoding/test_encoding.py
```

55 passed，原始输出uv-test-result.txt。这仅验证官方编码器fixture，不证明当前发布W4A8与官方1017权重等价，也不是本次服务质量成绩。
