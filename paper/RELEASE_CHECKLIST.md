# RELEASE_CHECKLIST: 公开发布步骤（等用户手动执行）

> 状态：仓库已做发布前清理，**尚未**建 GitHub 仓库、**尚未** push。
> 发布键只能用户按：不要让 agent 自动建仓库或 push。

## 发布前检查（已完成，2026-09-25）

- [x] 敏感信息全仓库扫描：`api_key/token/secret/password/private_key/bearer/credential` 等关键字 **0 命中**（排除 .venv/__pycache__）。
- [x] `data/`、`experiments/`、`scripts/` 无真实 key、邮箱、硬编码路径。仅有的邮箱是合成 PII 模板 `synthetic.user.N@example.invalid`（example.invalid 为保留域名，安全）。
- [x] "dynamic credential surrogate" 相关文件：仓库中不存在，无需处理。
- [x] `ENV_SETUP.md` 中的本地路径 `/home/hatch` 已改为通用占位描述。
- [x] `LICENSE` 已替换为完整 Apache License 2.0 全文（含版权行 Copyright 2026 Feilian Huang）。
- [x] `README.md` 已重写为英文公开版：一句话介绍、A/C/E 三个 scheme、复现步骤、结果文件位置、论文引用（arXiv 占位 TBD）。
- [x] `.gitignore` 新增：排除 `.venv/`、`__pycache__/`、原始大语料 `data/`（3.5G）、实验中间大文件 `experiments/subsets|storage_nodes`。保留 `data_pii/`（72M 合成语料）、`experiments/pii_matrix*` 小结果 JSON、paper、scripts、plugins。
- [x] `scripts/run_pii_matrix.sh` 可复现性：脚本本身是 resume-safe（已存在的输出自动跳过）；正通过 n=3 重复实验（`scripts/run_pii_extras.sh` + `scripts/25_repeat_ci.py`）实测验证，无需单独再跑一遍 11-run。

## 用户执行的 3 条发布命令

在 `~/workspace/llm-cleaning-pushdown/` 目录下依次执行：

```bash
# 1. 初始化并提交（首次）
cd ~/workspace/llm-cleaning-pushdown
git init -b main
git add -A
git commit -m "Public release: pushdown-is-not-free PII redaction measurement + toolkit"

# 2. 建公开仓库并 push（需要 gh 已登录；二选一）
gh repo create llm-cleaning-pushdown --public --source=. --push

# 3.（备选）如果不用 gh：先在网页建空公开仓库，再执行
# git remote add origin git@github.com:<你的用户名>/llm-cleaning-pushdown.git
# git push -u origin main
```

## push 之后

- 把仓库 URL 填回 `paper/paper.md` 的 `[TODO] repository URL`。
- 更新 README 中的 arXiv 占位（提交 arXiv 后填入真实编号）。
