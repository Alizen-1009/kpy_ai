date -u; uname -m
df -h / /root/yuhao /root/syf/data_yf /data2/syf /home/docker
free -h
numactl --hardware
npu-smi info
printf '\nDRIVER/CANN\n'
cat /usr/local/Ascend/driver/version.info /usr/local/Ascend/ascend-toolkit/latest/version.cfg 2>/dev/null
printf '\nIMAGES\n'
docker image ls --digests --no-trunc
for image in fe705b00b250 vllm-ascend:v0.30.0-a3; do docker image inspect "$image" --format '{{.Id}} {{json .RepoTags}} {{json .RepoDigests}} {{.Size}}' ; done
printf '\nBOUNDED ROOTS\n'
for p in /root/yuhao /root/syf/data_yf /data2/syf; do ls -la "$p"; done
printf '\nCANN DIRECTORIES\n'
ls -ld /usr/local/Ascend/* /usr/local/Ascend/ascend-toolkit/* /usr/local/Ascend/ascend-toolkit/latest/opp/vendors/* 2>/dev/null
