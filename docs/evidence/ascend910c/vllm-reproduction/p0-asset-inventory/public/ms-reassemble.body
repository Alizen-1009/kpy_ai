#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Engram 权重重组脚本
#
# 背景：受 ModelScope 单文件 50 GB 上限约束，以下两个文件在发布时被切成 6 片：
#   layers_1_engram_embed.weight.safetensors
#   layers_14_engram_embed.weight.safetensors
# 本脚本把它们按序拼接还原，并逐级校验 sha256。校验不通过会立即中止，
# 不会留下不完整的结果文件。
#
# 用法：
#   cd engram_int8
#   bash reassemble_engram_weights.sh              # 校验并还原（保留分片）
#   bash reassemble_engram_weights.sh --delete-parts   # 还原成功后删除分片
#   bash reassemble_engram_weights.sh --check-only     # 只校验，不还原
# ---------------------------------------------------------------------------
set -uo pipefail

cd "$(dirname "$0")" || exit 2

DELETE_PARTS=0
CHECK_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --delete-parts) DELETE_PARTS=1 ;;
    --check-only)   CHECK_ONLY=1 ;;
    -h|--help)      sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "未知参数: $arg（用 --help 查看用法）" >&2; exit 2 ;;
  esac
done

PARTS=6
# 重组后文件的正确 sha256
declare -A WANT_HASH=(
  [layers_1_engram_embed.weight.safetensors]="51d28f161232e3bf600b92ef4e3c38ceb9164b801bd456503bb1a29da496ea9f"
  [layers_14_engram_embed.weight.safetensors]="bee6e08838c75d40c4b1f5f8d7e4716aba34f90c03c17e77ad406e36188cccaa"
)

have_sha256sum=1
command -v sha256sum >/dev/null 2>&1 || have_sha256sum=0

fail=0
for base in layers_1_engram_embed.weight layers_14_engram_embed.weight; do
  target="$base.safetensors"
  echo "== $target =="

  # 已存在且校验通过 → 跳过
  if [ -f "$target" ] && [ "$have_sha256sum" = 1 ]; then
    got=$(sha256sum "$target" | cut -d' ' -f1)
    if [ "$got" = "${WANT_HASH[$target]}" ]; then
      echo "   已存在且校验通过，跳过"
      continue
    fi
    echo "   已存在但校验不通过，将重新还原"
  fi

  # 收集分片
  parts=(); missing=0
  for i in $(seq -f "%02g" 0 $((PARTS - 1))); do
    p="$base.safetensors.part-$i-of-$(printf '%02d' "$PARTS")"
    [ -f "$p" ] || { echo "   缺少分片: $p" >&2; missing=1; fail=1; break; }
    parts+=("$p")
  done
  [ "$missing" = 1 ] && continue

  # 逐片校验（若 PARTS.sha256 存在）
  if [ "$have_sha256sum" = 1 ] && [ -f PARTS.sha256 ]; then
    bad=0
    for p in "${parts[@]}"; do
      want=$(awk -v f="$p" '$2 == f {print $1}' PARTS.sha256 | head -1)
      [ -z "$want" ] && continue
      got=$(sha256sum "$p" | cut -d' ' -f1)
      if [ "$got" != "$want" ]; then
        echo "   分片校验失败: $p" >&2
        bad=1
      fi
    done
    if [ "$bad" = 1 ]; then
      echo "   有分片损坏，请重新下载该分片后再试。" >&2
      fail=1; continue
    fi
    echo "   分片校验通过（${PARTS} 片）"
  fi

  [ "$CHECK_ONLY" = 1 ] && { echo "   (--check-only，未还原)"; continue; }

  # 拼接
  tmp="$target.tmp-$$"
  if ! cat "${parts[@]}" > "$tmp"; then
    echo "   拼接失败" >&2; rm -f "$tmp"; fail=1; continue
  fi

  # 校验还原结果
  if [ "$have_sha256sum" = 1 ]; then
    got=$(sha256sum "$tmp" | cut -d' ' -f1)
    if [ "$got" != "${WANT_HASH[$target]}" ]; then
      echo "   还原结果校验失败！" >&2
      echo "     期望 ${WANT_HASH[$target]}" >&2
      echo "     实际 $got" >&2
      rm -f "$tmp"
      fail=1; continue
    fi
    echo "   还原完成，sha256 校验通过"
  else
    echo "   还原完成（未找到 sha256sum，未做校验）"
  fi

  mv -f "$tmp" "$target"

  if [ "$DELETE_PARTS" = 1 ]; then
    rm -f "${parts[@]}"
    echo "   已删除分片"
  fi
done

echo
if [ "$fail" = 0 ]; then
  echo "OK：全部文件就绪。"
  [ "$DELETE_PARTS" = 0 ] && [ "$CHECK_ONLY" = 0 ] && echo "提示：分片仍保留，可用 --delete-parts 回收空间。"
  exit 0
else
  echo "FAIL：存在未完成的文件，请按上方提示处理后重试。" >&2
  exit 1
fi
