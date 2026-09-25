# 本地环境搭建清单（ENV_SETUP）

> 查询/实测日期：2026-09-24。目标：本机小规模调试（1-2GB），第 3 周试跑 A/C。

## 本机实测结论（2026-09-24）

| 项目 | 结果 |
|---|---|
| Docker | **不可用**（`docker: command not found`，未安装） |
| sudo | 可用（免密），cgroup v2 存在 |
| CPU / 内存 | 2 vCPU / 7.7GB（共享 VM，另有 FileDrawerBench 推理在跑，实测时注意错峰） |
| 磁盘 | 工作目录所在磁盘需 ≥85GB 可用（1-2GB 调试数据足够）；避免把 venv/数据放在内存盘 /tmp |
| `tc` | 可用（`/usr/sbin/tc`），可做 loopback 限速验证 |
| MinIO | **不可用**：社区版已于 2025 年归档，dl.min.io 返回 410 Gone，GitHub release 404 |
| SeaweedFS | 二进制可下载，但 `weed master` 在本机起不来（masterClient 重连失败），放弃 |
| moto[server] | 可 pip 安装（S3 mock），但内存型后端不适合 GB 级数据 → 本周试跑**不用** |
| Python | 3.12，venv 可用 |

**采用方案（已验证思路）**：`LocalShardedPlugin`（`plugins/minio_duckdb/plugin.py`）
- 4 个本地分片目录扮演"存储节点"，下推执行器为子进程 worker。
- CPU 配额：优先 `cpulimit`，其次 `systemd-run --scope -p CPUQuota=`，都不行则如实记录 `cpu_quota_enforced=false`。
- 网络：传输时间用显式带宽模型（`costs/pricing.yaml`：同区域 10Gbps / 跨区域 1Gbps / 跨云 100Mbps），字节数实测。`tc` 可另行做一次 loopback 真实限速校验（可选）。
- S3 API 路径（moto/MinIO 真实版）列为第 5-7 周工作，不阻塞本周。

## 一键搭建

```bash
cd ~/workspace/llm-cleaning-pushdown
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/30_pushdown_matrix.py   # 可下推性矩阵自检
```

## 第 3 周试跑命令（完整流程见 docs/week3_plan.md）

```bash
# 1. 数据准备（约 1.5GB FineWeb 样本，三种格式；需能访问 huggingface.co）
.venv/bin/python scripts/00_prepare_data.py --data-root data

# 2. A/C 试跑（示例：跨云 100Mbps，chunked_gzip）
.venv/bin/python scripts/10_run_scheme.py --scheme A --format chunked_gzip \
    --bandwidth-mbps 100 --out experiments/week3_ac/A_chunked_100.json
.venv/bin/python scripts/10_run_scheme.py --scheme C --format chunked_gzip \
    --cpu-quota 0.25 --bandwidth-mbps 100 --out experiments/week3_ac/C_chunked_100_q25.json

# 3. 干扰测试（H4）
.venv/bin/python scripts/31_interference.py --out experiments/week3_ac/interference.json

# 4. 报告 + 检查点1判定
.venv/bin/python scripts/20_report.py --runs "experiments/week3_ac/*.json" \
    --out experiments/week3_ac/report.md --cost-out experiments/week3_ac/cost_onepager.md
```

## 已知限制（写入论文局限性）

1. 单机模拟：存储/计算同机，"网络"为带宽模型而非真实跨机传输。
2. 2 vCPU 小机器：CPU 配额实验的绝对值仅供看趋势，不可直接外推。
3. moto/MinIO 真实 S3 路径尚未接通；第 5-7 周补。
4. 定价为占位常量（`costs/pricing.yaml`，2026-09-24），第 8 周换真实云定价。
