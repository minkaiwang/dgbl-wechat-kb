# 构建与审计方法

知识库采用“私有原始层—规范化正文层—授权公开层—检索与发布层”的分层流程。

1. **发现与留证**：从公开合集取得文章清单，保存稳定 ID、位置、标题、发布时间和原文 URL；
   原始响应只保存在私有归档。
2. **原始保存**：先保存 HTML，再转换 Markdown，避免处理失败后无法追溯来源。
3. **正文规范化**：保留标题、段落、表格、超链接和必要格式；每篇文章写入 YAML frontmatter。
4. **图片隔离**：原图不进入公开仓库；每个图片出现位置转换为可计数的文字占位符。
5. **授权闸门**：`data/content-license.json` 固化许可人、范围和版本。当前仅位置 1–475 的
   原创文字获 CC BY-NC 4.0 授权，未来文章默认待确认。
6. **隐私检查**：公开前扫描邮箱、个人用户路径、凭据模式、危险内联标记和私有归档标记；
   需要删除的论文通讯作者邮箱以不暴露原值的审计记录留痕。
7. **索引生成**：由 Markdown 重建 `data/articles.jsonl`、全文目录、轻量元数据和
   `docs/llms.txt`，避免人工维护多个相互漂移的副本。
8. **一致性审计**：核对 475 个位置、稳定 ID、原文 URL、导入状态、许可字段、正文 QA、
   去重图片数和图片出现位置数。
9. **确定性发布**：从同一输入生成全文与元数据 JSONL/CSV/Schema/ZIP，并输出 SHA256；
   同版本重复构建应得到相同字节。
10. **完整历史扫描**：正式发布前检查当前树和全部 Git blob，阻止私有路径、凭据、个人邮箱、
    超限文件和未授权原图进入远端历史。

## 新增文章流程

新文章进入私有清单后先导入并完成 QA，正文权利默认保持 `pending_owner_review`。只有维护者
明确将新增位置纳入授权清单后，才运行 `scripts/apply_text_license.py --write`、重建索引并
生成新版本 Release。图片许可始终与正文许可分开处理。

## 可复现命令

```powershell
uv run python scripts/apply_text_license.py
uv run python scripts/build_index.py
uv run python scripts/build_public_metadata.py
uv run python scripts/qa_kb.py --inventory <private-articles.jsonl> --public-root . --strict
uv run python scripts/validate_public_release.py --history
uv run python scripts/build_release_assets.py --output dist --version 0.2.0
```

第一条命令默认只检查、不写入；确需应用已确认授权时才添加 `--write`。
