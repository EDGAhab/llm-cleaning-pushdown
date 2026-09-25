# 声明式流水线规格 Schema（v0.1）

插件接收的是**声明式规格**，不是原始 S3 请求。示例见 `pipeline_specs/fineweb_default.json`。

## 顶层字段

| 字段 | 说明 |
|---|---|
| `name` | 规格名 |
| `description` | 人类可读描述 |
| `seed` | 全局随机种子，所有方案输出必须 deterministic |
| `input.columns` | 输入列（如 `["id","text"]`） |
| `input.format` | `whole_gzip` \| `chunked_gzip` \| `zstd_parquet` |
| `steps` | 步骤数组，按顺序执行 |
| `output.columns` | 输出列；`output.sorted_by` 排序键（用于跨方案比对） |

## 步骤类型

| type | 类别 | params |
|---|---|---|
| `rule_filter` | 本地 | `min_words`, `symbols[]`, `max_symbol_ratio`, `max_uppercase_ratio` |
| `language_id` | 本地 | `keep[]`, `min_confidence` |
| `pii_redact` | 本地 | `patterns[]` (`email`/`phone_us`/`ssn_us`), `replacement` |
| `minhash_sign` | 本地 | `num_perm`, `shingle_k`, `seed` |
| `lsh_dedup` | 全局 | （第 5-7 周，方案 D） |
| `exact_dedup` | 全局 | `key`；**永远在计算端执行**，所有方案一致 |

每个步骤可带 `placement: "compute"` 强制计算端执行；`note` 为人类备注。

## 能力声明

插件用 `declare_capabilities()` 对每种步骤返回 `full` / `partial` / `none`。
`none` 的步骤自动回退到计算端，并在可下推性矩阵中标出。
