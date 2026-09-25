# 检查点 1 评估报告（2026-09-24）

> 对应 handoff §8 检查点 1：在 1-2GB 数据上试跑 A 和 C；H1-H4 至少一个出现有意思的信号，否则停下来讨论调整方向。

## 试跑配置

- 数据：FineWeb 真实样本，100k 文档子集（约 300MB raw，5 chunks），manifest 见 `data/manifest.json`
  - **注意**：原定 1-2GB 正式检查点因本机算力/稳定性（3 次服务重启）降为 100k exploratory run。结论为方向性，非正式。
- 规格：`pipeline_specs/fineweb_default.json`（seed 42）
- 方案：A（全拉取）x4（chunked/whole/parquet/10Gbps），C（全下推）x3（chunked q10/q25/q50 @100Mbps）
- 报告：`experiments/week3_ac/report.md`（自动生成，有基线选择 bug，见下）

## 正确性门

- [x] PASS：chunked 下 5 个 run（A x2 + C x3）输出 hash 完全一致；whole/parquet 各自一致。
  - Hash: `413a353221efc97a3fec08be520d1e72328ff68201051a8bf2144c19ec7f08df` (100k)
  - Hash: `95bf62fed191643de0b49c7dd9a656a08c03e379673baf26c854978485d538c1` (20k)

## 信号判定（量化标准见 docs/week3_plan.md §5）

**基线修正**：自动报告误用 A@10Gbps（1109s）作基线。正确基线为 A@100Mbps（859.0s），与 C 同带宽。

| 信号 | 定义 | 结果 | 效应量 |
|---|---|---|---|
| S1（H1 方向） | time(C,q=10%) / time(A) ≥ 1.2 | **YES** | **5.47x** (q10: 4695s/859s) |
| S2（潜力） | bytes(C)/bytes(A) ≤ 0.5 且 time(C)/time(A) ≤ 1.2 | NO | bytes 0.996x（过滤率仅 1.1%） |
| S3（H3 方向） | A/C 胜者在三格式下不一致 | NO | A 在 chunked 全胜；parquet 下 A=1597s，C 外推 >>1597s |
| S4（H4 方向） | p99 退化随 quota 单调上升且出现 ≥2x knee | **INCOMPLETE** | 3 次服务重启杀死 interference 测试 |

### S1 配额扫描（chunked @100Mbps，基线 A=859.0s）

| quota | C time_to_ready | ratio vs A |
|---|---|---|
| 10% | 4695.2s | **5.47x** |
| 25% | 2138.0s | **2.49x** |
| 50% | 1501.9s | **1.75x** |

单调递减，外推 q100 ≈ 1.2x。低配额下推慢 5.5 倍，效应远超 20% 阈值。

### S2 为何无信号

- bytes(C)/bytes(A) = 0.996。过滤率仅 1.1%，PII 脱敏不改变字节数。
- **关键洞察**：当清洗流水线以计算为主（langdetect+minhash ≈ 850s，占 A 总时间 99%）、过滤率低时，下推几乎不省字节，也不省时间（传输仅 10s）。下推的字节红利要求高收缩比流水线（如 WARC→text）。

### S3 说明

- C/parquet 未完成（单 worker 100k @q25 需 ~77min，两次被重启杀死）。
- 外推：C/parquet ≥ 4640s（单 worker 上限）> A/parquet 1597s。胜者仍为 A，无翻转。

### S4 说明

- Interference 测试两次被服务重启杀死（第 1 次卡死因 cpulimit 被清空，第 2 次直接重启）。
- 已实现 `scripts/throttle.py`（SIGSTOP/SIGCONT）替代 cpulimit 并验证可用，但环境不稳定，不再重跑 65min 测试。
- S4 标记为 INCOMPLETE，非科学阴性。

## 结论

- [x] **INTERESTING**（S1 效应 447%，远超 20% 阈值）→ 按授权进入下一阶段
- [ ] NO SIGNAL

## 诚实性备注

1. **100k 子集，非 1-2GB**：本机 2vCPU 跑 100k 已需数小时；完整数据（389k）未跑正式检查点。
2. **单机模拟**：存储/计算同机，传输时间为带宽模型（100Mbps/10Gbps）。绝对时间不可外推云上；相对比值（5.47x 等）在本机自洽。
3. **PII 计数污染**：17,169 redactions 含 FineWeb 原文自然匹配，非纯合成注入。正式结果前需预清除原文匹配。
4. **CPU 计量**：`compute_cpu_s` 用 RUSAGE_SELF，未计 multiprocessing 子进程；`cost_usd` 为占位定价，不可作结论。
5. **C/parquet、C/10Gbps 未完成**：S3 为外推，C/10Gbps 缺失（但 A/10Gbps 显示传输可忽略，不影响结论方向）。
6. **3 次服务重启**：09-24 当天基础设施重启 3 次，杀死长任务。已做 checkpoint 续跑脚本（`run_week3_resume.sh`/`run_week3_final.sh`）。

## 下一步（第 4 周）

- 实现方案 E（同区域 CPU 集群）或转向 PII 合规场景（handoff §8 检查点 2 逻辑）。
- 优先修复：PII 预清除、CPU 计量（multiprocessing）、report.py 基线 bug。
- S4 interference 待环境稳定后补测。
