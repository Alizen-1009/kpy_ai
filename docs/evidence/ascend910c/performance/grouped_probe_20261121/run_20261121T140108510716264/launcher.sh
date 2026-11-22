#!/usr/bin/env bash
set -euo pipefail
w=/root/yuhao/deepinfer_910c_yh
p=$w/grouped_probe_20261121_yh
entry=${GROUPED_ENTRY:-probe_grouped_device.py}
[[ "$entry" == probe_grouped_device.py || "$entry" == probe_grouped_rounding.py ]] || exit 2
r=$p/run_$(date +%Y%m%dT%H%M%S%N)
mkdir "$r"
cp "$p/$entry" "$r/$entry"
cp "${BASH_SOURCE[0]}" "$r/launcher.sh"
npu-smi info > "$r/before.txt"
python3 - "$w" "$r" <<'PY'
import json,re,sys
from pathlib import Path
w,r=map(Path,sys.argv[1:]); p=json.loads((w/'scripts_yh/test_device_policy_yh.json').read_text());d=8
assert d in p['host_logical_die_allowlist'] and d not in p['host_logical_die_forbidden']
s=(r/'before.txt').read_text();process=s[s.index('| NPU     Chip'):]
assert not re.search(r'\|\s*4\s+0\s*\|\s*\d+\s*\|',process),'busy'
m=re.search(r'\|\s+0\s+8\s+\|[^\n]*?(\d+)\s*/\s*65536',s)
assert m and int(m[1])<4096
PY
cleanup(){ if [[ -s "$r/cid" ]]; then docker rm -f "$(<"$r/cid")" > "$r/cleanup.txt" 2>&1 || true; fi; }
trap cleanup EXIT
status=0
timeout --signal=TERM --kill-after=10 240 docker run --rm --pull=never --cidfile "$r/cid" --name "yuhao-grouped-$(basename "$r")" --network none --read-only --tmpfs /tmp:rw,size=256m --memory 8g --cpus 2 --pids-limit 256 --shm-size 64m --security-opt no-new-privileges --device /dev/davinci8 --device /dev/davinci_manager --device /dev/devmm_svm --device /dev/hisi_hdc -e "GROUPED_ENTRY=$entry" -e ASCEND_RT_VISIBLE_DEVICES=0 -e TORCH_DEVICE_BACKEND_AUTOLOAD=0 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -e ASCEND_PROCESS_LOG_PATH=/tmp/ascend_logs -e ASCEND_WORK_PATH=/tmp/ascend_work -v /usr/local/Ascend/driver:/usr/local/Ascend/driver:ro -v "$w:$w" --entrypoint /bin/bash sha256:41dab489874e4983324d9d960a6c57f8bd45ebb5172a3b7672bd64461f9d96b7 -c '
set -e
w=/root/yuhao/deepinfer_910c_yh
source "$w/cann92_sdk_yh/cann/set_env.sh"
prefix=$w/envs_yh/deepinfer-py312_yh
export LD_LIBRARY_PATH="$prefix/lib:/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver:${LD_LIBRARY_PATH:-}"
exec "$prefix/bin/python" "$w/grouped_probe_20261121_yh/$GROUPED_ENTRY"
' > "$r/device.log" 2>&1 || status=$?
cleanup
npu-smi info > "$r/after.txt"
printf '%s\n' "$status" > "$r/exit.txt"
if [[ -s "$r/cid" ]]; then docker inspect "$(<"$r/cid")" > "$r/inspect.txt" 2>&1 || true; fi
printf '%s\n' "$r"
