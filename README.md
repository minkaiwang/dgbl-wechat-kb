# 数字游戏学习研究 · 公众号知识库

[![CI](https://github.com/minkaiwang/dgbl-wechat-kb/actions/workflows/ci.yml/badge.svg)](https://github.com/minkaiwang/dgbl-wechat-kb/actions/workflows/ci.yml)

这是“数字游戏学习研究”微信公众号的可追溯元数据知识库。公开仓库收录导入与审计代码、
474 条公开安全元数据、文章目录和质量报告；每条记录均可回到微信原文核验。

## 当前状态

- 公开合集：已发现并导入 **474** 个连续位置，文章 ID 与原文 URL 均无重复。
- 公众号主页截图：显示 **486** 篇原创内容；与公开合集相差 12 篇，仍待后台清单对账。
- 未决编号：3、94、435；356–364 高度疑似一次性编号跳号；编号 246 有两篇不同文章。
- 公开范围：代码、元数据、目录、测试和审计材料。
- 私有范围：474 篇正文、本地全文索引、摘要片段、原始 HTML、原图与抓取快照。

完整性口径见 [`reports/completeness-reconciliation.md`](reports/completeness-reconciliation.md)。

## 公开边界

| 内容 | GitHub 状态 | 说明 |
|---|---|---|
| `data/article-metadata.jsonl` | 公开 | 标题、日期、栏目、稳定 ID、作者字段与微信原文链接 |
| `docs/catalog-public.md` | 公开 | 不含正文的可浏览目录 |
| `data/import-status.jsonl` | 公开 | 导入与自动质量审计状态 |
| `scripts/`、`tests/` | 公开 | 发现、导入、索引、检索、审计和发布门禁 |
| `docs/articles/` | 不提交 | 474 篇本地 Markdown 正文 |
| `data/articles.jsonl`、`docs/llms.txt` | 不提交 | 含正文片段的本地检索索引 |
| 原始 HTML、图片、接口快照和日志 | 不提交 | 仅保存在维护者的 E 盘私有归档 |

`.gitignore` 与 `scripts/validate_public_release.py` 对受限路径实施双重门禁。公开仓库不需要
公众号 AppID、AppSecret、Cookie 或浏览器登录状态。

## 公开仓库快速验证

```powershell
git clone https://github.com/minkaiwang/dgbl-wechat-kb.git
cd dgbl-wechat-kb
uv sync --frozen --python 3.12 --extra test
uv run ruff check .
uv run pytest
uv run python scripts/validate_public_release.py
$env:NO_MKDOCS_2_WARNING='true'; uv run mkdocs build --strict
```

GitHub Actions 在每次 push 和 pull request 上运行同一组检查。公开 clone 可以验证已提交的
安全元数据；重新抓取、生成正文或构建全文索引需要维护者的私有原始清单。

## 目录结构

```text
data/       公开元数据、导入状态与中文分词词典
docs/       元数据站点和公开文章目录
reports/    完整性、质量、权利与发布审计
scripts/    发现、导入、构建、搜索和发布门禁
tests/      单元测试
skills/     项目专用 Codex Agent Skill
```

## 许可

- 软件代码：根目录 [`LICENSE`](LICENSE) 中的 MIT License。
- 公开元数据、目录、报告和项目文档：[`DATA-LICENSE.md`](DATA-LICENSE.md) 中的 CC BY 4.0。
- 微信文章正文、摘要片段、图片和第三方材料：不在上述开放许可范围内，且不进入公开 Git 历史。

引用项目时可使用 [`CITATION.cff`](CITATION.cff)。贡献规则见
[`CONTRIBUTING.md`](CONTRIBUTING.md)，内容权利边界见 [`RIGHTS.md`](RIGHTS.md)。
