# GitHub 仓库与公开发布方案

## 账号预检

- 仓库所有者：`minkaiwang`
- 账号主页：<https://github.com/minkaiwang>
- 本机 GitHub CLI：已登录 `minkaiwang`，Git 协议为 HTTPS。
- 仓库：`minkaiwang/dgbl-wechat-kb`，默认分支为 `main`。
- 发布决策：用户已于 2026-08-14 明确授权把“代码 + 474 条安全元数据”版本推进为 Public。
- 持续排除：文章正文、摘要片段、图片与私有归档；GitHub Pages 和全文发布不在本批次范围内。

## 建仓字段

| 字段 | 建议值 |
|---|---|
| Owner | `minkaiwang` |
| Repository name | `dgbl-wechat-kb` |
| Description | `数字游戏学习研究公众号文章知识库：可追溯元数据、中文检索、质量审计与可复现导入流程。` |
| Visibility | `Public`；仅公开通过门禁的代码与安全元数据 |
| Initialize repository | 已从本地受审计工作树初始化 |
| Default branch | `main` |
| Website | 暂留空；通过发布闸门后再填写 GitHub Pages 地址 |

预期远程地址：`https://github.com/minkaiwang/dgbl-wechat-kb.git`

建议 Topics：

`wechat`、`knowledge-base`、`digital-game-based-learning`、`gamification`、`education`、`mkdocs`、`chinese-nlp`、`open-research`

## 分阶段发布

### 第一阶段：代码与元数据

可以先发布以下内容：

- 导入、索引、检索与质量审计脚本；
- 单元测试、项目说明、方法与审计报告；
- `data/article-metadata.jsonl` 中的标题、日期、栏目、稳定 ID、微信原文链接等事实性元数据；
- 根目录 MIT License。MIT 只覆盖代码。

暂不发布：

- `docs/articles/` 的 474 篇正文；
- `data/articles.jsonl` 中含正文片段的 `preview`；
- `docs/llms.txt` 中的正文摘要片段；
- 原始 HTML、原图、接口快照、抓取日志与未审查素材。

### 第二阶段：全文知识库

满足以下条件后再提交全文：

1. 公众号权利人确认正文许可；
2. 客座作者或多人创作内容完成授权核对；
3. 图片逐项明确为可再分发、替换、删除或仅保留原文链接；
4. 主页 486 篇与合集 474 篇的口径完成对账；
5. 测试、Ruff、严格站点构建和浏览器抽样复核通过。

正文许可建议：若作者构成可确认且希望允许非商业传播，可选 `CC BY-NC 4.0`；若希望最大化复用，可选 `CC BY 4.0`；暂不能确认授权的文章保持原有权利状态，不放入公开全文包。图片许可必须单独处理。

## 当前确认状态

1. 私有仓库初始化和首次 `main` 推送已完成。
2. v0.1.0 范围固定为代码、测试、审计材料和 474 条公开安全元数据。
3. 代码采用 MIT；公开元数据和项目文档采用 CC BY 4.0。
4. 正文、摘要片段与图片继续排除，文章正文许可仍待逐项确认。
5. 用户已明确授权在 CI、完整历史和隐私门禁通过后将仓库改为 Public。

GitHub Pages、GitHub Release 和任何全文发布均作为后续独立动作处理。
