# 第 3 周试跑脚本计划（A 全拉取 vs C 全下推）

> 对应 handoff §4/§8。数据 1-2GB，本地执行，零费用。

## 0. 前置

- `.venv` 已装好（见 ENV_SETUP.md）。
- `scripts/30_pushdown_matrix.py` 自检通过（local_sharded：4 个本地步骤 full，2 个全局步骤 none；airmettle_stub 未实现）。

## 1. 数据准备（`scripts/00_prepare_data.py`）

- 从 HuggingFace 流式取 FineWeb（`HuggingFaceFW/fineweb`，train，streaming），攒 ~1.5GB raw JSONL。
- 1% 文档注入**合成** PII（`synthetic.user.NNNN@example.invalid` / `555-01XX` / `900-XX-XXXX`），供 `pii_redact` 验证。
- 输出三种格式：
  - `data/fmt_whole_gzip/sample.jsonl.gz`（整块 gzip）
  - `data/fmt_chunked_gzip/chunks/chunk_*.jsonl.gz`（每 20k 文档独立 gzip，记录边界切分）
  - `data/fmt_zstd_parquet/sample.parquet`（zstd 压缩）
- 写 `data/manifest.json`（大小、文档数、sha256）。

## 2. 试跑矩阵（`scripts/10_run_scheme.py`）

| # | scheme | format | cpu_quota | bandwidth | 目的 |
|---|---|---|---|---|---|
| 1 | A | whole_gzip | - | 100Mbps | 基线（跨云） |
| 2 | A | chunked_gzip | - | 100Mbps | 基线 |
| 3 | A | zstd_parquet | - | 100Mbps | 基线 |
| 4 | C | whole_gzip | 10% | 100Mbps | H1：低配额是否拖慢 |
| 5 | C | chunked_gzip | 10% | 100Mbps | H1 |
| 6 | C | chunked_gzip | 25% | 100Mbps | 档位 |
| 7 | C | chunked_gzip | 50% | 100Mbps | 档位 |
| 8 | C | zstd_parquet | 25% | 100Mbps | H3：格式是否改变胜负 |
| 9 | C | chunked_gzip | 25% | 1000Mbps | 跨区域 |
| 10 | A | chunked_gzip | - | 1000Mbps | 跨区域基线 |
| 11 | C | chunked_gzip | 25% | 10000Mbps | 同区域（下推应无优势） |
| 12 | A | chunked_gzip | - | 10000Mbps | 同区域基线 |

每个配置跑 1 次（调试性质；时间允许则对 #5/#6 跑 3 次取中位数）。

## 3. 干扰测试（`scripts/31_interference.py`，H4）

- 前台随机读 + 后台下推（quota 10%/25%/50%），记录 p50/p99 与基线对比。

## 4. 报告（`scripts/20_report.py`）

- 正确性门：同 format 下所有 run 的 `output_sha256` 必须一致，否则 FAIL。
- 输出 `experiments/week3_ac/report.md` + `cost_onepager.md`。

## 5. 检查点 1 判定标准（量化）

- **S1（H1 方向）**：`time(C,quota=10%) / time(A) >= 1.2` → 低配额拖慢下推。
- **S2（潜力）**：`bytes(C)/bytes(A) <= 0.5` 且 `time(C)/time(A) <= 1.2` → 有下推价值。
- **S3（H3 方向）**：A/C 的 `time_to_ready` 胜者在三种 format 下不一致。
- **S4（H4 方向）**：`p99_degradation_x` 随 quota 呈单调上升且在某档出现 ≥2x 跃变（knee）。
- **结论**：任一满足（效应 ≥20%）→ INTERESTING，继续；全不满足 → NO SIGNAL，如实报告，与用户讨论转向（PII 合规场景 / 下推边界），**不硬凑**。

## 6. 产物

- `experiments/week3_ac/*.json`（原始结果）
- `experiments/week3_ac/report.md`（对比 + 判定）
- `reports/checkpoint1.md`（给用户的检查点报告）
