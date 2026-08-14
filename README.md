# 数字游戏学习研究 · 公众号知识库

本仓库用于整理“数字游戏学习研究”微信公众号公开文章，形成可浏览、可搜索、可供 AI 检索且能回到原文核验的知识库。

> 当前状态：远程私有空仓库已创建，本地“代码＋元数据”首个提交已经建立，等待首次 push 确认。公开合集已发现 474 篇；公众号主页截图显示 486 篇原创内容，差额仍待后台清单或人工核对。正文、摘要片段和图片不进入首发提交。

## 架构

```text
E:\DGBL-WeChat-KB\
├─ private-archive\    原始 HTML、原图、接口快照、日志和不确定项，不进入 Git
└─ public-repo\        清洗后的 Markdown、公开素材、索引、脚本和站点
```

公开仓库以 Markdown 为事实来源：

- `docs/articles/`：本地按年份保存文章；正文许可确认前由 `.gitignore` 阻止提交。
- `docs/catalog-public.md`：只含标题、日期、栏目和微信原文链接的公开目录。
- `data/article-metadata.jsonl`：不含正文与摘要片段的公开安全元数据索引。
- `data/articles.jsonl`：含本地正文检索片段的完整机器索引，正文许可确认前不进入公开包。
- `scripts/`：发现、导入、质量检查、索引和检索脚本。
- `reports/`：批次清单、质量和版权审计。
- `skills/dgbl-kb/`：项目专用 Agent Skill。

## 工作流

1. 从公众号公开合集取得文章清单，保存原始接口快照。
2. 逐篇保存原始 HTML 和图片，并生成规范 Markdown。
3. 对标题、日期、正文、图片和链接进行自动检查及抽样核对。
4. 将第三方素材标为 `pending_review`，通过版权检查后才进入公开素材目录。
5. 构建中文全文搜索站点和本地检索入口。

## 本地命令

```powershell
uv sync --python 3.12 --extra test
uv run python scripts/discover_album.py --help
uv run python scripts/import_articles.py --help
uv run python scripts/archive_images.py --help
uv run python scripts/build_index.py
uv run python scripts/build_public_metadata.py
uv run python scripts/search_kb.py "游戏化学习 动机"
uv run python scripts/qa_kb.py --help
uv run pytest
$env:NO_MKDOCS_2_WARNING='true'; uv run mkdocs build --strict
```

项目不需要公众号 AppID、AppSecret 或 Cookie。合集原始链接中的 `chksm` 是公开访问校验字段，发现阶段必须保留。不得把任何账号凭据放入本仓库。

Camoufox 仅作为可选浏览器回退：`uv sync --extra browser`。正常合集导入不需要下载其浏览器运行时。
