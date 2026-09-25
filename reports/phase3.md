# 阶段报告：Phase 3 — 真实数据准备 + A/C 试跑矩阵（已完成，2026-09-24）

日期：2026-09-24（PDT 上午，约 10:30 完成）

## 试跑结果总览

- **矩阵完成**：A x4（chunked/whole/parquet/10Gbps）+ C x3（chunked q10/q25/q50 @100Mbps），共 7 个有效 run。
- **正确性**：全部 PASS（同 format 输出 hash 一致）。
- **检查点 1 判定**：**INTERESTING**（S1 效应 447%），详见 `reports/checkpoint1.md`。
- **未完成**：C/parquet（外推 S3=NO）、C/10Gbps（非关键）、interference/S4（3 次服务重启杀死，标记 INCOMPLETE）。

## 已完成

1. **FineWeb 真实数据准备**（`scripts/00_prepare_data.py`）
   - 从 HuggingFace 公开仓库直接下载 FineWeb parquet shard（免费，无需登录）：
     `data/CC-MAIN-2013-20/000_00001.parquet`（2,146,853,893 bytes，1,083,399 行）。
   - 绕开本机 `datasets` streaming 的代理 bug（`httpx.InvalidURL`）。
   - 生成三格式（`data/manifest.json`）：
     - whole gzip JSONL：480.0 MB
     - chunked gzip（20 x 20k docs）：~480 MB
     - zstd Parquet：523.7 MB
   - 共 388,995 文档（~1.2GB raw），注入 3,922 条明确合成 PII（~1%）。
   - 试跑矩阵使用前 5 chunks（100k docs，~300MB raw）子集，保证本机 2 vCPU
     一夜可跑完；全量数据已备好，用户机器可跑全量。

2. **工具包性能优化**
   - `plugins/minio_duckdb/plugin.py`：4 个下推 worker 并行（ThreadPoolExecutor）。
   - `scripts/10_run_scheme.py`：scheme A 计算阶段 multiprocessing（2 进程）。
   - 新增 `--limit-refs`（子集试跑）、`--local-parquet`（用已下载分片）。

3. **正确性门（真实数据，1 chunk）**
   - A 与 C（q25）的 `output_sha256` 完全一致：
     `95bf62fed191643de0b49c7dd9a656a08c03e379673baf26c854978485d538c1`
   - filter_rate = 1.05%，docs_out = 19,790 / 20,000。

4. **试跑矩阵完成**（历经 3 次服务重启，续跑脚本 `run_week3_resume.sh`/`run_week3_final.sh`）
   - 7 个有效 run + 自动报告 `experiments/week3_ac/report.md`。
   - 关键数字（100k docs，基线 A@100Mbps=859s）：
     - C/q10: 4695s (**5.47x**)，C/q25: 2138s (**2.49x**)，C/q50: 1502s (**1.75x**)
     - bytes(C)/bytes(A) = 0.996（过滤率仅 1.1%，下推不省字节）
   - 基础设施问题：cpulimit 被重启清空，已实现 `scripts/throttle.py`（SIGSTOP/SIGCONT）替代并验证可用。

## 基础设施教训

- 当天 3 次服务重启杀死长任务（每次损失数小时）。教训：长矩阵必须 checkpoint 化（已做续跑脚本），关键中间结果及时落盘。
- `scripts/20_report.py` 有基线选择 bug（多 A run 同 format 时取错基线），checkpoint1.md 已用手工修正数字。

## 诚实性备注

- 本机无 Docker/MinIO，结论来自 LocalShardedPlugin 单机模拟；
  传输时间为带宽模型，绝对数值不可直接外推云上。
- 定价为占位常量（`costs/pricing.yaml`）。
