# 必读文献对比表：大模型数据清洗的存储端下推

> 检索时间：2026-09-24；渠道：公开 web（arXiv、作者主页/机构页、会议官网、ACM/USENIX/VLDB 公开 PDF、Google Patents）。
> 凡未读全文者，已在"信息来源"中标注"未获取全文，基于摘要/二级引用"。本表不作任何法律判断。

## 总表

| # | 文献（标题/作者/venue） | 问题 | 方法 | 实验场景 | 与本文区别 |
|---|---|---|---|---|---|
| 1 | HAPI：Accelerating Transfer Learning with Near-Data Computation on Cloud Object Stores；D. Petrescu, A. Guirguis, Do Le Quoc, J. Picorel, R. Guerraoui, F. Dinu (EPFL/Huawei)；SoCC 2024 | 解耦云存储-计算网络瓶颈拖慢迁移学习训练 | 把 TL 模型在特征提取阶段切分，下推到对象存储侧执行；存储侧 batch-size 自适应提高并发、避免 OOM | 训练时图像特征提取下推；ResNet/VGG/Transformer；最高 11x 应用运行加速（v1），数据传输降 8.3x | HAPI 研究训练时图像预处理下推，本文研究训练前文本清洗（含全局去重拆分、压缩数据并行下推、多轮迭代累积收益） |
| 2 | SOPHON：A Selective Preprocessing Offloading Framework for Reducing Data Traffic in DL Training；M. Wang, G. Waldspurger, S. Sundararaman (UChicago)；HotStorage 2024 | 图像预处理全量下推反而可能增加流量/训练时间 | 选择性下推：两阶段 profiler（TG/TCC/TCS/TNet），只下推预处理后变小的样本 | 训练时图像解码/裁剪下推；OpenImages、ImageNet，500Mbps 网络；OpenImages 流量降 2.2x，ImageNet 降 1.2x | SOPHON 研究训练时图像预处理下推，本文研究训练前文本清洗（含全局去重拆分、压缩数据并行下推、多轮迭代累积收益） |
| 3 | OffloadFS：Leveraging Disaggregated Storage for Computation Offloading；S. Moon 等 7 人；arXiv 2604.13743 (2026-04，投稿 IEEE 审稿中） | NVMeoF 解耦存储节点算力/内存闲置；共享盘文件系统分布式锁过重 | 用户态文件系统 OffloadFS（免分布式锁）；OffloadDB（RocksDB flush/compaction 下推）、OffloadPrep（图像预处理下推） | RocksDB 后台压实（3.36x vs OCFS2）、ML 图像预处理（1.85x） | OffloadFS 的 OffloadPrep 仍是训练时图像预处理下推，本文研究训练前文本清洗（含全局去重拆分、压缩数据并行下推、多轮迭代累积收益） |
| 4 | PushdownDB：Accelerating a DBMS Using S3 Computation；X. Yu 等 7 人；ICDE 2020 | 云上分析查询全量拉取 S3 数据，网络瓶颈 | 用 S3 Select 下推 selection/projection/简单 aggregation；join/top-K/group-by 重实现；成本分析 | TPC-H 查询；平均便宜 30%、快 6.7x | PushdownDB 研究数据库查询下推（SQL 聚合/过滤），本文研究 ML 数据清洗流水线 |
| 5 | FlexPushdownDB：Hybrid Pushdown and Caching in a Cloud DBMS；Y. Yang 等 8 人；VLDB 2021 (PVLDB 14(11)) | caching 与 pushdown 被当作正交技术，各自为政 | separable operators 细粒度混合执行；Weighted-LFU 缓存替换 | Star Schema Benchmark；混合执行比纯 cache/纯 pushdown 快 2.2x；Weighted-LFU 比 LFU 好 37% | FlexPushdownDB 研究数据库查询下推（SQL 聚合/过滤），本文研究 ML 数据清洗流水线 |
| 6 | FlexPushdownDB 扩展版：FlexpushdownDB: Rethinking Computation Pushdown for Cloud OLAP DBMSs；Y. Yang, X. Yu, M. Serafini, A. Aboulnaga, M. Stonebraker；VLDBJ 2024 | （同上，期刊扩展） | 新增 adaptive pushdown（含 pushback 机制，按存储层资源动态决策）；两个新可下推算子 selection bitmap、distributed data shuffle | TPC-H；两个新算子分别带来 3.0x、1.7x 端到端加速 | 扩展版仍研究数据库查询下推（SQL 聚合/过滤/算子），本文研究 ML 数据清洗流水线 |
| 7 | tf.data service：A Case for Disaggregating ML Input Data Processing；A. Audibert, Y. Chen, D. Graur, A. Klimovic, J. Simsa, C. Thekkath (Google/ETH)；SoCC 2023 | 加速器与 host CPU/RAM 固定配比导致一方闲置；训练时数据 stall | 解耦输入数据处理服务：水平扩展 right-size CPU/RAM；跨作业共享预处理结果；coordinated reads 防 straggler | 训练时在线预处理；大规模训练；训练时间/成本大幅降低，coordinated reads 降 2.2x 训练时间 | tf.data service 做训练时在线预处理的解耦扩展（远程 CPU 资源池，非存储节点）；本文是存储端下推的训练前文本清洗 |
| 8 | Pecan：Cost-Efficient ML Data Preprocessing with Automatic Transformation Ordering and Hybrid Placement；D. Graur, O. Mraz, M. Li, S. Pourghannad, C. Thekkath, A. Klimovic (ETH/Google)；USENIX ATC 2024 | 远程 CPU worker 占解耦预处理训练总成本大头；加速器节点 CPU/DRAM 闲置 | AutoPlacement（local+remote 混合放置）+ AutoOrder（自动重排 transformation，松弛交换律保精度） | 训练时在线预处理（ResNet/SimCLR/ASR Transformer/RetinaNet）；预处理成本降 87%，总训练成本 vs Cachew 降 60%、vs collocated 降 55% | Pecan 优化训练时在线预处理（放置+重排），本文研究训练前文本清洗的存储端下推 |
| 9 | FastFlow：Accelerating Deep Learning Model Training with Smart Offloading of Input Data Pipeline；T. Um, B. Oh, B. Seo, M. Kweun, G. Kim, W.-Y. Lee (Samsung Research)；VLDB 2023 (PVLDB 16(5)) | 输入流水线 CPU 瓶颈致 GPU 闲置；naive offload 可能更慢 | 轻量 profiling（DAG 插桩）自动决策何时/下推哪些算子/多少数据到远程 CPU；集成 TensorFlow | 7 个图像+音频训练负载（三星私有 DL 云）；吞吐 1-4.34x vs 无 offload，1-4.52x vs 手动 tf.data.service，0.63-2.06x vs DALI | FastFlow 是训练时在线预处理下推到远程 CPU，本文研究训练前文本清洗下推到存储节点 |
| 10 | DataTrove + FineWeb：FineWeb 数据集（Penedo et al., arXiv 2406.17557, 2024）与 DataTrove 开源库（HF, Apache-2.0） | Common Crawl 原始网页噪声大、重复多，需大规模清洗才能用于 LLM 预训练 | 模块化 pipeline blocks：WARC 读取→文本提取→语言识别→质量过滤（Gopher/C4/启发式）→MinHash/精确子串/句子级去重；支持 local/Slurm/Ray 执行 | 构建 FineWeb（英文 15T+ tokens）、FineWeb-Edu、FineWeb-2（多语言）；DCLM、Cosmopedia 亦采用 | DataTrove/FineWeb 是清洗算法的参考实现，计算全部发生在计算集群（CPU 集群/Slurm），未研究把清洗步骤下推到存储节点；本文研究把这类文本清洗流水线（本地步骤+全局去重拆分）下推到存储端 |
| 11 | Lee et al.：Deduplicating Training Data Makes Language Models Better；K. Lee, D. Ippolito, A. Nystrom, C. Zhang, D. Eck, C. Callison-Burch, N. Carlini；ACL 2022 | LM 数据集近重复多→模型记忆、训练低效、train-test overlap（>4% 验证集） | 两种去重工具：exact（后缀数组）+ 近似（MinHash/LSH）；开源 google-research/deduplicate-text-datasets | C4 等数据集；C4 中一条 61 词句子重复 6 万+次；记忆化输出降 10x；更少训练步数达到同等/更好精度 | Lee 等论证去重价值与算法，不涉及系统/存储下推；本文把"全局去重拆分"这类步骤下推到存储节点并行执行 |
| 12 | Ana Klimovic：Rethinking Data Storage and Preprocessing for ML；ACM SIGARCH 博客（清单注 2021；抓取页面未显示日期） | ML 存储与预处理未得到系统栈应有关注；Google 百万级作业中平均 30% 端到端训练算力花在数据摄取和在线预处理 | 观点文章：梳理离线（清洗/转二进制格式）与在线预处理（读/变换/加载）现状；提出方向：解耦在线预处理弹性扩展、部分变换（过滤）放近存储执行、缓存复用、统一存储层（Lakehouse） | 无实验（观点/position 文章） | 该博客提出"把过滤等变换推到近存储"的方向但未做实现；本文是具体实现（训练前文本清洗下推、全局去重拆分、压缩并行下推） |
| 13 | 美国专利 US12438943B2：System and method for offloading preprocessing of machine learning data to remote storage；发明人 D. Dutta, J. George, M. Bhattacharyya, R. Liao；受让人 Nutanix Inc；申请 2022-11-04，授权 2025-10-07 | （专利，仅复述公开文本） | 公开摘要：在对象存储平台的存储节点放置第一计算资源、客户端计算节点放置第二计算资源；存储节点对非结构化数据做预处理，之后发往计算节点训练 ML 模型；preprocessing orchestrator 决定各步骤（filtering/parsing/interleaving/mapping/prefetching）在存储或计算节点执行；数据分 chunk 跨多存储节点并行预处理；template generator 可生成预处理模板（含 PII 掩码） | （专利说明，无学术实验） | 专利侧重训练输入流水线（训练时）预处理步骤拆分；本文研究训练前文本清洗流水线（含全局去重拆分、压缩数据并行下推、多轮迭代累积收益）。仅作相关工作引用，不做任何法律判断 |

---

## 每篇 2-3 句摘要 + 来源链接

**1. HAPI (SoCC 2024).** 针对迁移学习（先特征提取、后微调）的两阶段结构，把 DNN 在特征提取阶段切分，将部分特征提取下推到云对象存储侧执行，并用存储侧 batch-size 自适应在有限算力下提高并发且不爆内存。实验用 ResNet/VGG/Transformer，最高 11x 应用运行加速（v1 报告；v3 报告最高 2.5x 训练加速），存储→计算数据传输降低 8.3x。
来源：arXiv https://arxiv.org/abs/2210.08650 ；ACM DOI https://doi.org/10.1145/3698038.3698549

**2. SOPHON (HotStorage 2024).** 发现图像预处理（解码、裁剪）全量下推到存储节点反而可能增加流量与训练时间，于是做"选择性下推"：两阶段 profiler 采集 TG/TCC/TCS/TNet 四个指标，只对预处理后变小的样本做存储侧下推。在 500Mbps 网络、存储节点 CPU 可变配置下，OpenImages 数据流量降 2.2x、ImageNet 降 1.2x。
来源：机构 PDF https://ucare.cs.uchicago.edu/pdf/hotstorage24-sophon.pdf ；ACM DOI https://doi.org/10.1145/3655038.3665947 ；作者按论文页脚署名（M. Wang, G. Waldspurger, S. Sundararaman），未发现 arXiv 版本。

**3. OffloadFS (arXiv 2604.13743, 2026-04，投稿 IEEE 审稿中）。** 为 NVMeoF 解耦存储设计的用户态文件系统：允许多节点把 IO 密集型任务下推到存储节点（或 peer 计算节点）近数据执行，免去传统共享盘文件系统的分布式锁管理，上层演示了 OffloadDB（RocksDB flush/compaction 下推）和 OffloadPrep（图像预处理下推）。相对 OCFS2，RocksDB 最高 3.36x、ML 图像预处理最高 1.85x。
来源：arXiv https://arxiv.org/abs/2604.13743

**4. PushdownDB (ICDE 2020).** 研究用 AWS S3 Select 把 DBMS 分析查询的 filter/projection/简单 aggregation 下推到 S3 存储节点执行，复杂算子（join/top-K/group-by）需重实现，并指出 S3 Select 按量计价可能比 EC2 计算更贵。TPC-H 上平均便宜 30%、快 6.7x。
来源：arXiv https://arxiv.org/abs/2002.05837 ；researchr 会议记录 https://researchr.org/publication/YuYWGSAS20

**5. FlexPushdownDB (VLDB 2021).** 指出 caching 与 pushdown 不应被视为正交，提出 separable operators 实现细粒度混合执行（缓存命中的分段本地算、其余下推），以及考虑下推成本的 Weighted-LFU 缓存替换。Star Schema Benchmark 上混合执行比纯缓存/纯下推快 2.2x，Weighted-LFU 比 LFU 好 37%。
来源：PDF https://ashraf.aboulnaga.me/pubs/pvldb21flexpushdowndb.pdf ；DOI https://doi.org/10.14778/3476249.3476265 ；未发现 arXiv 版本。

**6. FlexPushdownDB 扩展版 (VLDBJ 2024).** 期刊扩展：在 VLDB 2021 基础上加入 adaptive pushdown（含 pushback 机制，按存储层资源利用率动态决定是否下推），并论证了两个此前未被下推的算子（selection bitmap、distributed data shuffle）可受益于下推。TPC-H 端到端分别加速 3.0x 与 1.7x。
来源：Springer https://link.springer.com/article/10.1007/s00778-024-00867-8 ；作者手稿 PDF https://marcoserafini.github.io/assets/pdf/FlexPushdownDB-VLDBJ.pdf ；未获取全文，方法细节基于手稿摘要与二级引用。

**7. tf.data service (SoCC 2023).** 把 tf.data 输入预处理从训练 host 解耦为独立服务：可水平扩展以 right-size 每个作业的 CPU/RAM、跨作业共享预处理结果、coordinated reads 避免分布式训练中的 straggler。面向训练时在线预处理，是"远程 CPU 资源池"而非存储节点。
来源：arXiv https://arxiv.org/abs/2210.14826 ；ACM DOI https://doi.org/10.1145/3620678.3624666

**8. Pecan (USENIX ATC 2024).** 在解耦预处理（Cachew）基础上做成本优化：AutoPlacement 在加速器 host 本地与远程 worker 间混合放置，AutoOrder 自动重排 pipeline 中的 transformation（松弛交换律但保持模型精度）以提高 worker 吞吐。预处理成本平均降 87%，总训练成本比 Cachew 降 60%、比 collocated 降 55%。
来源：USENIX 页面 https://www.usenix.org/conference/atc24/presentation/graur ；代码 https://github.com/eth-easl/cachew/tree/pecan ；未发现 arXiv 版本。

**9. FastFlow (VLDB 2023).** 针对"naive 下推可能更慢"的问题，用轻量 profiling（在 pipeline DAG 中插入 profiling 算子，复用训练迭代特性）自动决策何时下推、下推哪些算子、下推多少数据到远程 CPU，并与 TensorFlow 集成、用户无需改代码。在三星私有 DL 云的 7 个图像/音频负载上：吞吐 1-4.34x（vs 无 offload）、1-4.52x（vs 手动 tf.data.service）、0.63-2.06x（vs DALI）。
来源：PVLDB PDF https://www.vldb.org/pvldb/vol16/p1086-um.pdf ；DOI https://doi.org/10.14778/3579075.3579083 ；代码 https://github.com/SamsungLabs/FastFlow ；未发现 arXiv 版本。

**10. DataTrove 与 FineWeb 数据清洗流程。** FineWeb（Penedo et al., arXiv:2406.17557, 2024）是用 DataTrove 库构建的高质量英文网页数据集（15T+ tokens）及 FineWeb-Edu、FineWeb-2（多语言）；DataTrove 是 HF 开源的模块化大规模文本处理库（Apache-2.0，local/Slurm/Ray 可执行），pipeline blocks 覆盖 WARC 读取、文本提取、语言识别、质量过滤（Gopher/C4/启发式规则）、MinHash/精确子串/句子级去重。DCLM、Cosmopedia 等也基于它构建。注意：DataTrove 的计算全部发生在计算集群，没有存储端下推的概念。
来源：FineWeb 论文 https://arxiv.org/abs/2406.17557 ；DataTrove 仓库 https://github.com/huggingface/datatrove ；数据集说明 https://github.com/openeurollm/training-data-catalogue/blob/HEAD/fineweb/1.4.0/README.md

**11. Lee et al. "Deduplicating Training Data Makes Language Models Better" (ACL 2022).** 发现 LM 数据集存在大量近重复与长重复子串（C4 中一条 61 词句子重复 6 万余次），导致模型记忆化输出（>1% 无提示输出逐字复制训练数据）与 train-test overlap（影响 >4% 验证集）。提供 exact（后缀数组）与近似（MinHash/LSH）两套去重工具并开源；去重后记忆化输出降 10x、达到同等精度所需训练步数更少。
来源：ACL Anthology https://aclanthology.org/2022.acl-long.577/ ；arXiv https://arxiv.org/abs/2107.06499

**12. Ana Klimovic "Rethinking Data Storage and Preprocessing for ML" (ACM SIGARCH 博客）。** 观点文章：指出 Google 百万级 ML 作业中平均 30% 端到端训练算力花在数据摄取和在线预处理；梳理离线（特征提取、清洗、转二进制格式）与在线预处理（读/变换/加载）现状，提出研究方向，包括解耦在线预处理弹性扩展、把能减少数据量的变换（过滤、聚合）推到近存储执行、缓存复用、统一存储层与 provenance。无实验。
来源：https://www.sigarch.org/rethinking-data-storage-and-preprocessing-for-ml/ （页面抓取未显示发布日期，清单注 2021）

**13. 美国专利 US12438943B2（Nutanix Inc，仅公开信息，不做法律判断）。** 标题 "System and method for offloading preprocessing of machine learning data to remote storage"，发明人 D. Dutta, J. George, M. Bhattacharyya, R. Liao；申请号 US17/981,077，申请日 2022-11-04，授权日 2025-10-07。公开摘要：在对象存储平台的存储节点放第一计算资源、客户端计算节点放第二计算资源；存储节点对非结构化数据做预处理后再发往计算节点训练 ML 模型；preprocessing orchestrator 决定 filtering/parsing/interleaving/mapping/prefetching 等步骤在存储或计算节点执行；数据分 chunk 跨多存储节点并行预处理；template generator 可生成预处理模板（含 PII 掩码）。
来源：Google Patents https://patents.google.com/patent/US12438943B2/en

---

## 检索说明与局限

- SOPHON 作者按论文 PDF 页脚署名记录（M. Wang, G. Waldspurger, S. Sundararaman）；FlexPushdownDB 扩展版未获取全文，方法细节基于作者手稿摘要与二级引用；Klimovic 博客页面抓取未显示发布日期，按任务清单注 2021。
- 未发现 arXiv 版本的文献：SOPHON、FlexPushdownDB (VLDB 2021)、FlexPushdownDB 扩展版 (VLDBJ 2024)、Pecan、FastFlow（均有公开 PDF 或会议页面替代）。
- 专利部分仅复述 Google Patents 公开摘要与著录信息，未解释权利要求、不判断有效性/侵权。
