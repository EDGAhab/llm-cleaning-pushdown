# 检查点 2 评估报告（2026-09-24）

> 对应 handoff §8 检查点 2：第 4 周实现方案 E（同区域 CPU 集群）；若 C 在所有配置下都输给 E，论文重心转向 PII 合规场景和"下推的边界"，如实报告，不硬凑正面结果。

## 试跑配置

- 数据：FineWeb 真实样本，20k 文档子集（1 chunk，`--limit-refs 1`，`data/manifest.json`）
- 规格：`pipeline_specs/fineweb_default.json`（标准流水线）；`pipeline_specs/fineweb_warc.json`（+ `html_extract` 首阶段，高收缩比探针）
- 方案：A（全拉取）/ E（同区域 CPU 集群）/ C（全下推 q10/q25/q50/q100）
- 带宽：100Mbps（跨云）/ 10000Mbps（同区域）
- 本轮修复：CPU 计量（`run_scheme_A` 补 `RUSAGE_CHILDREN`；worker 改 `RUSAGE_SELF`）、报告基线 bug（同带宽基线）
- 报告：`experiments/week4_be/report.md`（自动生成）+ `cost_onepager.md`
- 矩阵：8 个 run 全部成功，无服务重启，一次跑完（约 1h21m），断点续跑逻辑未触发

## 正确性门

- [x] PASS：chunked_gzip 组 6 个 run（A/E/C×4）输出 hash 完全一致；warc_html 组 2 个 run hash 一致。
  - Hash（chunked）: `95bf62fed191643de0b49c7dd9a656a08c03e379673baf26c854978485d538c1`（与 week3 的 20k hash 相同，跨周可比）
  - Hash（warc）: 2 runs 一致（与 chunked 不同，预期内：spec 不同）

## C vs E 对比（检查点 2 核心判定）

唯一带宽匹配的比较（chunked @10000Mbps，均为满 CPU）：

| 方案 | time_to_ready | cost_usd（占位定价） |
|---|---|---|
| C q100 @10Gbps | 246.8s | $0.0051 |
| E @10Gbps | 251.7s | $0.0027 |

- time：C 险胜 1.9%（4.9s）。单次测量、无重复 run，该幅度在单机噪声范围内，**不能算稳健优势**。
- cost：E 便宜约 47%（$0.0027 vs $0.0051；定价为占位常量，但方向是结构性的：同区域 egress < 跨云 egress）。
- 严格按字面标准"C 在所有配置下都输给 E"：**未干净触发**（C 在 time 上赢了 1.9%）；但按科学诚实标准：**C 对 E 没有展示任何稳健优势**。

补充：C q10 总 CPU（246.7+1.2=247.9 cpu-s）反而略高于 A（232.6 cpu-s）：SIGSTOP/SIGCONT 节流只拉长 wall time，不省 CPU。

## 高收缩比探针（WARC→text）

| 方案 | time | bytes | bytes 比 |
|---|---|---|---|
| A warc @100Mbps | 288.4s | 0.027 GB | — |
| C warc q25 @100Mbps | 1043.0s | 0.025 GB | **0.93x** |

- time(C)/time(A) = 3.62x（S1 信号成立）。
- bytes(C)/bytes(A) = 0.93：**高收缩比假设未被验证**。warc_html 测试数据的原始 HTML 仅比提取文本大 7%（0.027 vs 0.025 GB），根本不具备高收缩比特征。探针测的不是"WARC→text"，而是"几乎已经是文本的数据再抽一次"。S2（bytes ≤0.5x 且 time ≤1.2x）依然无信号。
- 要真正检验字节红利，需要原始 HTML 远大于文本的 WARC 数据（本轮数据不具备该性质）。

## S1 配额扫描（chunked @100Mbps，基线 A=301.9s）

| quota | C time_to_ready | ratio vs A |
|---|---|---|
| 10% | 1878.9s | **6.22x** |
| 25% | 820.3s | **2.72x** |
| 50% | 477.3s | **1.58x** |
| 100%（@10Gbps） | 246.8s | 0.82x（带宽不同，不可比） |

单调递减，与 week3（5.47x/2.49x/1.75x）方向一致、幅度更大。低配额下推显著变慢，效应远超阈值。

## 结论

- [x] **INTERESTING（弱信号）**：自动报告判 5 个信号——S1×4（q10/q25/q50 chunked + q25 warc）、S3（格式翻转胜者）。
  - S3 的"翻转"（chunked 胜者=C）是报告脚本的带宽错配产物：best-C@10Gbps vs A@100Mbps，不是同带宽比较，**不作为科学结论**。
- 检查点 2 核心问题"C 能否在任何配置下稳健地赢过 E"：**答案是否定的**。唯一可比配置上 C 的 time 优势为 1.9%（噪声级），cost 上 E 大胜；低配额下 C 被 A 拉开 1.6–6.2 倍。
- **建议**：按 handoff §8 启动转向讨论——论文重心转向 PII 合规场景与"下推的边界"（S1 给出了清晰的"下推何时有害"边界；warc 探针说明字节红利需要真实高收缩比数据；C vs E 打平说明同区域 CPU 集群是更强的 baseline）。转向的触发条件按字面未 100% 满足（1.9% 的 time 险胜），但把 1.9% 单次测量当"胜利"将是不诚实的。

## 诚实性备注

1. **20k 子集、单次测量、无重复**：所有比值（包括 C vs E 的 1.9%）都是单次 run，无误差棒。
2. **单机模拟**：存储/计算同机，传输时间为带宽模型；E 与 C@10Gbps 的比较在本机自洽，但绝对时间不可外推云上。
3. **PII 计数污染未修复**：`pii_redactions`（3195/3153）仍含 FineWeb 原文自然匹配，非纯合成注入；预清除未实现（checkpoint1 的遗留项）。
4. **CPU 计量已修复**：A 的 `compute_cpu_s`=232.55（含子进程），C 有 `storage_cpu_s`；但 C q10 总 CPU 反而高于 A。
5. **cost_usd 为占位定价**：week8 才收集真实云定价；E 便宜的方向是结构性的（同区域 egress），幅度不可作结论。
6. **S3 翻转是带宽错配 artifact**：报告脚本用 best-C（@10Gbps）对比 A（@100Mbps）；同带宽下 chunked 的胜者应为 E（或打平的 C q100）。
7. **warc 探针数据不具备高收缩比**：0.027→0.025 GB；"WARC→text 字节红利"假设本轮未被真正检验。
8. **本次无服务重启**：矩阵 8 个 run 一次跑完（01:11:18），断点续跑逻辑未触发。
