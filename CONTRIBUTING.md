# 贡献指南

欢迎提交代码改进、元数据纠错、正文转换修复和可复现的审计补充。请保持来源、权利和修改记录
可追溯。

## 提交内容纠错

请提供：

1. `article_id` 或微信原文链接；
2. 需要修改的字段或正文位置及建议值；
3. 可公开核验的依据；
4. 修改是否影响授权、脱敏、图片占位符或索引。

Issue 中不要粘贴整篇正文，不要上传 Cookie、Token、后台个人信息、原始图片、私有日志或其他
未确认许可素材。无法公开核验的线索请标为 `uncertain`。

## 本地检查

```powershell
uv sync --frozen --python 3.12 --extra test
uv run ruff check .
uv run pytest
uv run python scripts/validate_public_release.py
$env:NO_MKDOCS_2_WARNING='true'; uv run mkdocs build --strict
```

修改文章后还应运行 `scripts/build_index.py`、`scripts/build_public_metadata.py` 和严格知识库审计，
确保 Markdown、索引、元数据和报告同步。不要将维护者的 `private-archive` 或被 `.gitignore`
排除的图片强制加入 Git。

## 贡献许可

- 代码贡献按 MIT License 提供；
- 元数据和项目文档贡献按 CC BY 4.0 提供；
- 对现有文章原创文字的修正应能在 CC BY-NC 4.0 范围内合法提供；
- 第三方文字、图片和数据必须保留来源与许可证据，无法确认时不要提交。

安全、隐私或误收受限内容的问题请按 [`SECURITY.md`](SECURITY.md) 私密报告。
