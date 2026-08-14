# 贡献指南

欢迎提交代码改进、元数据纠错和可复现的审计补充。当前公开版本不接收微信文章正文、
正文摘要、原图或其他权利未确认素材。

## 元数据纠错

请提供：

1. `article_id` 或微信原文链接；
2. 需要修改的字段与建议值；
3. 可公开核验的依据，例如微信原文页面或公众号后台导出的非敏感字段。

Issue 和 pull request 中不要粘贴整篇正文，不要上传 Cookie、Token、后台截图中的个人信息
或未公开日志。无法公开核验的线索请标为 `uncertain`。

## 本地检查

```powershell
uv sync --frozen --python 3.12 --extra test
uv run ruff check .
uv run pytest
uv run python scripts/validate_public_release.py
$env:NO_MKDOCS_2_WARNING='true'; uv run mkdocs build --strict
```

pull request 应保持范围单一，并说明变更原因、数据来源和检查结果。公开派生文件必须能从
有权使用的来源复现；不要将维护者的 `private-archive` 或被 `.gitignore` 排除的文件强制加入 Git。

## 贡献许可

提交代码即表示你有权按 MIT License 提供该贡献；提交公开元数据或项目文档即表示你有权按
CC BY 4.0 提供该贡献。第三方内容必须保留来源和许可证证据，不能确认时不要提交。

安全、隐私或误收受限内容的问题请按 [`SECURITY.md`](SECURITY.md) 私密报告。
