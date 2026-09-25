# 阶段报告：第 1-2 周（本地环境实搭 + 工具包骨架代码）

> 日期：2026-09-24。对应 handoff §8 第 1-2 周。

## 做了什么

1. **环境实测并定案**：Docker 不可用、MinIO 已归档、SeaweedFS 起不来、moto 内存后端不适合 GB 级。
   定案 `LocalShardedPlugin`：4 本地分片目录 = 存储节点；worker 子进程 = 下推执行器；
   `cpulimit`（已 apt 安装）做 CPU 配额（10%/25%/50%）；传输时间用显式带宽模型。
   实测结论与限制写入 `ENV_SETUP.md`（含论文局限性 4 条）。
2. **工具包骨架代码实现并冒烟通过**：
   - `plugins/base.py` 插件接口；`plugins/cleaning.py` 确定性清洗步骤
     （rule_filter / language_id / pii_redact / minhash_sign / exact_dedup）。
   - `plugins/minio_duckdb/` 参考实现（A 全拉取 / C 全下推，worker 子进程）。
   - `plugins/airmettle_stub/` 接口 stub + `INTEGRATION.md`（1-2 周可接入的指南，未实现）。
   - `scripts/00_prepare_data.py`（FineWeb 样本 + 合成 PII 注入 + 三种格式）。
   - `scripts/10_run_scheme.py`（A/C 试跑，记录字节/时间/CPU/成本/输出哈希）。
   - `scripts/20_report.py`（对比表 + 正确性门 + 检查点 1 判定 + 一页成本报告）。
   - `scripts/30_pushdown_matrix.py`（可下推性矩阵）、`scripts/31_interference.py`（H4 前台干扰）。
   - `costs/pricing.yaml`（2026-09-24 占位定价，第 8 周换真实云定价）。
3. **调试中修的真问题**（记录供复现）：
   - datasketch 2.x `MinHash.digest()` 返回 ndarray → 用 `.tobytes().hex()`。
   - `systemd-run --user` 在本机无 bus → 改用 `cpulimit`。
   - worker stdout 被 cpulimit 的 "Process N detected" 污染 → 只解析 `{` 开头的行。
   - MinHash hex（1024 字符/文档）进传输输出会淹没下推收益 → worker 主输出只传 `{id, text}`，签名走 sidecar（供方案 D）。
   - exact dedup 必须与输入顺序无关 → 按 text 哈希分组、保留最小 id。

## 结果

- 3000 合成文档冒烟：A/C 输出 sha256 完全一致（正确性门 PASS）；C（quota 25%）传输 0.8x、耗时 4.4x（S1 方向信号，真实数据复测）。
- FineWeb 1.5GB 真实样本下载中（curl 直下 parquet 分片，绕开 datasets 的代理 bug）。

## 下一步

- 数据就绪后跑 `docs/week3_plan.md` 的 12 配置矩阵 + 干扰测试 → `reports/checkpoint1.md`。

## 需要用户决定的事

- 暂无。云上正式实验（第 5-7 周）的预算届时单独报批，今晚不碰。
