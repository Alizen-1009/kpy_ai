#!/usr/bin/env bash
# Stage5 small FFN diagnostic; no full model, same idle/RO/cleanup policy.
set -euo pipefail
work="${DEEPINFER_910C_WORK:-/root/yuhao/deepinfer_910c_yh}"
die="${1:-8}"
mode="${FP4_BENCHMARK_MODE:-profile}"
case "$mode" in
 profile) entry=benchmark_w4a8_real_ffn.py ;;
 ab|ffn) if [[ "$mode" == ab ]]; then entry=benchmark_fp4_ab_replay.py; else entry=benchmark_fp4_ffn_ab.py; fi
 [[ "${FP4_APPROVED_CANDIDATE_SHA256:-}" =~ ^[0-9a-f]{64}$ ]] || exit 2 ;;
 *) exit 2 ;;
esac
source_dir="${OFFICIAL_SOURCE_DIR:?Set task-owned stage4 source directory}"
view=/root/yuhao/DeepSeek-V4.1-Flash-1017-HF
archive=/root/syf/data_yf/DeepSeek-V4.1-Flash-1017-original_yf
snapshot="${MOE_REPLAY_SNAPSHOT:?Set captured rank0 replay tensor path}"
[[ "$snapshot" == "$work/reports_yh/"* && -f "$snapshot" ]] || exit 2
[[ "$source_dir" == "$work/src_yh/"* && -f "$source_dir/scripts/ascend910c/profile_official_fp4_replay.py" ]] || exit 2
[[ "$die" =~ ^(8|9|10|11|12|13|14|15)$ && "$(uname -m)" == aarch64 && -c "/dev/davinci$die" ]] || exit 2
[[ -d "$view" && -d "$archive" ]] || exit 2
image=sha256:41dab489874e4983324d9d960a6c57f8bd45ebb5172a3b7672bd64461f9d96b7
stamp="$(date +%Y%m%dT%H%M%S%N)"
report="$work/reports_yh/stage5_moe_batch_die${die}_${stamp}_yh"
mkdir "$report"
npu-smi info > "$report/before_yh.txt"
python3 - "$work" "$report" "$die" <<'PY'
import json,re,sys
from pathlib import Path
w,r=map(Path,sys.argv[1:3]);d=int(sys.argv[3]);p=json.loads((w/'scripts_yh/test_device_policy_yh.json').read_text())
assert d in p['host_logical_die_allowlist'] and d not in p['host_logical_die_forbidden']
s=(r/'before_yh.txt').read_text();process=s[s.index('| NPU     Chip'):]
assert not re.search(r'\|\s*'+str(d//2)+r'\s+'+str(d%2)+r'\s*\|\s*\d+\s*\|',process),'Selected die is busy'
m=re.search(r'\|\s+'+str(d%2)+r'\s+'+str(d)+r'\s+\|[^\n]*?(\d+)\s*/\s*65536',s)
assert m and int(m[1])<4096,'Selected die above idle HBM baseline'
print('Fresh idle guard passed',d,m[1])
PY
cidfile="$report/container_yh.cid"
cleanup() {
 if [[ -s "$cidfile" ]]; then
  local cid; cid="$(python3 -c 'from pathlib import Path;import sys;print(Path(sys.argv[1]).read_text().strip())' "$cidfile")"
  if [[ "$cid" =~ ^[0-9a-f]{64}$ ]]; then docker rm -f "$cid" >/dev/null 2>&1 || true; fi
 fi
}
trap cleanup EXIT
status=0
timeout --signal=TERM --kill-after=10 900 docker run --rm --pull=never \
 --cidfile "$cidfile" --name "yuhao-stage5-moe-batch-die${die}-${stamp}-yh" \
 --network none --read-only --tmpfs /tmp:rw,size=256m --memory 8g --cpus 2 --pids-limit 256 --shm-size 64m --security-opt no-new-privileges \
 --device "/dev/davinci$die" --device /dev/davinci_manager --device /dev/devmm_svm --device /dev/hisi_hdc \
 -e "FP4_ENTRY=$entry" -e "FP4_APPROVED_CANDIDATE_SHA256=${FP4_APPROVED_CANDIDATE_SHA256:-}" \
 -e "MOE_REPLAY_HC_ONLY=${MOE_REPLAY_HC_ONLY:-0}" -e ASCEND_RT_VISIBLE_DEVICES=0 -e DEEPINFER_ACCELERATOR=ascend -e TORCH_DEVICE_BACKEND_AUTOLOAD=0 \
 -e PYTHONDONTWRITEBYTECODE=1 -e OMP_NUM_THREADS=1 -e MKL_NUM_THREADS=1 -e OPENBLAS_NUM_THREADS=1 \
 -e "W=$work" -e "D=$die" -e "R=$report" -e "S=$source_dir" -e "HF=$view" -e "SNAP=$snapshot" \
 -e "HOME=$work/home_yh" -e "TMPDIR=$work/tmp_yh" -e "ASCEND_WORK_PATH=$work/tmp_yh" -e "ASCEND_PROCESS_LOG_PATH=$work/logs_yh" \
 -v /usr/local/Ascend/driver:/usr/local/Ascend/driver:ro -v "$work:$work" \
 -v "$view:$view:ro" -v "$archive:$archive:ro" -w "$work" \
 --entrypoint /bin/bash "$image" -c '
 set -e;prefix="$W/envs_yh/deepinfer-py312_yh"; export PATH="$prefix/bin:$PATH"
 source "$W/cann92_sdk_yh/cann/set_env.sh"
 export PYTHONPATH="$S:${PYTHONPATH:-}"
 export LD_LIBRARY_PATH="$prefix/lib:/usr/local/Ascend/driver/lib64:/usr/local/Ascend/driver/lib64/common:/usr/local/Ascend/driver/lib64/driver:${LD_LIBRARY_PATH:-}"
 exec "$prefix/bin/python" "$S/scripts/ascend910c/$FP4_ENTRY" --host-die "$D" \
 --snapshot "$SNAP" --root "$HF" \
 --audited-headers "$S/doc/evidence/ascend910c/official_checkpoint_headers_yh.json" --report "$R/npu_yh.json"
 ' > "$report/run_yh.log" 2>&1 || status=$?
cleanup
npu-smi info > "$report/after_yh.txt"
python3 - "$report" "$status" <<'PY'
import json,subprocess,sys
from pathlib import Path
r=Path(sys.argv[1]);c=r/'container_yh.cid';cid=c.read_text().strip() if c.exists() else None
p=subprocess.run(['docker','inspect',cid],capture_output=True,text=True) if cid else None
state=json.loads(p.stdout)[0]['State'] if p and p.returncode==0 else None
d=dict(docker_exit_code=int(sys.argv[2]),container_still_running=bool(state and state['Running']),
       test_started=bool(cid),report_dir=str(r),checkpoint_mounts_read_only=True)
(r/'execution_yh.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))
f=r/'npu_yh.json'; print(f.read_text() if f.exists() else (r/'run_yh.log').read_text(errors='replace')[-6000:])
if d['container_still_running']:raise SystemExit('Owned container cleanup failed')
PY
if [[ "$status" == 0 && -f "$report/fp4_baseline.json" ]]; then
 python3 "$source_dir/scripts/ascend910c/summarize_fp4_profile.py" "$report" > "$report/profile_summary_stdout.txt"
fi
cp "$source_dir/scripts/ascend910c/$entry" "$report/profile_script.py"
cp "${BASH_SOURCE[0]}" "$report/launcher.sh"
printf 'EVIDENCE=%s\n' "$report"
exit "$status"
