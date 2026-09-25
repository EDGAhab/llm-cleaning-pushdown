# 阶段报告：第一步三样交付物（handoff §10）

> 日期：2026-09-24。状态：2/3 已完成，文献对比表与截稿日期由两个并行子任务收尾中。

## 做了什么

1. **HANDOFF.md**：handoff 原文逐字存档（含用户追加指示）。
2. **本地环境搭建清单（ENV_SETUP.md）**：实测结论，非臆测。
   - Docker：本机未安装、不可用；MinIO 社区版已归档（dl.min.io 410 Gone）；SeaweedFS 起不来。
   - 采用 `LocalShardedPlugin`：4 个本地分片目录扮演存储节点，worker 子进程做下推，`cpulimit`（已 apt 安装）做 CPU 配额，传输时间用显式带宽模型（10Gbps/1Gbps/100Mbps）。
   - `/tmp` 是 512MB tmpfs：venv 与数据一律放 workspace（85GB 可用）。
3. **工具包骨架**：插件接口（`plugins/base.py`）、声明式流水线规格（`pipeline_specs/fineweb_default.json` + `docs/pipeline_spec_schema.md`）、可下推性矩阵（`scripts/30_pushdown_matrix.py` → `docs/pushdownability_matrix.md`）、AirMettle 插件 stub + 1-2 周接入指南（`plugins/airmettle_stub/INTEGRATION.md`，未实现、不用其内部资料）、Apache 2.0 LICENSE。
4. **第 3 周试跑脚本计划（docs/week3_plan.md）**：12 配置矩阵 + 干扰测试 + 检查点 1 量化判定标准（S1-S4，效应 ≥20% 才算信号）。

## 结果

- 端到端冒烟测试通过：3000 合成文档上 A/C 输出 sha256 完全一致（正确性门 PASS）。
- 冒烟测试已看到方向性信号：C（quota 25%）传输字节 0.8x 但耗时 4.4x（S1 方向），真实数据上复测。
- 文献对比表、HotStorage/DaMoN/CIDR 截稿日期：子任务进行中，完成后补入 `docs/literature_review.md` / `docs/venues.md`。

## 下一步

- 第 1-2 周剩余：FineWeb 1.5GB 样本下载中（后台），随后跑 week3 矩阵 → 检查点 1。

## 需要用户决定的事

- 暂无（本阶段零费用、零对外联系）。
