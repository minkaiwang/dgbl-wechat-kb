# 数据集说明

## 版本快照

| 项目 | v0.1.0 |
|---|---|
| 数据对象 | “数字游戏学习研究”微信公众号公开帖子元数据 |
| 记录数 | 474 |
| 合集位置 | 1–474，连续 |
| 发布时间 | 2024-07-11 至 2026-08-12 |
| 数据许可 | CC BY 4.0 |
| 正文与图片 | 不包含 |

本数据集以公开合集为当前收录边界。公众号主页显示 486 篇原创内容，尚有 12 篇差额需要后台
清单解释，因此 v0.1.0 不宣称覆盖账号全部原创文章。

## 下载格式

- `dgbl-wechat-metadata-v0.1.0.jsonl`：UTF-8，每行一个 JSON 对象；适合流式处理。
- `dgbl-wechat-metadata-v0.1.0.csv`：UTF-8 with BOM；适合 Excel 直接打开。
- `dgbl-wechat-metadata-v0.1.0.schema.json`：单条 JSONL 记录的 JSON Schema 2020-12。
- `dgbl-wechat-metadata-v0.1.0.zip`：包含 JSONL、CSV、Schema、Manifest、许可和包内说明。
- `SHA256SUMS.txt`：以上四个数据资产的 SHA256 摘要。

所有文件可从 [GitHub Releases](https://github.com/minkaiwang/dgbl-wechat-kb/releases) 下载。
Python 读取 CSV 时建议显式使用 `encoding="utf-8-sig"`，以自动处理 Excel 兼容的 BOM。

## 字段字典

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | integer | 单条记录的结构版本，当前为 1 |
| `article_id` | string | 由微信消息 ID 与图文序号构成的稳定 ID |
| `position` | integer | 在公开合集清单中的连续位置 |
| `issue_no` | integer / null | 从标题解析的期号；特别篇等可为空 |
| `title` | string | 微信原文标题 |
| `display_title` | string / null | 去除栏目与期号前缀后的展示标题 |
| `series` | string / null | 从标题前缀解析的原始栏目标签 |
| `author` | string / null | 微信文章页面显示的作者字段 |
| `published_at` | string | ISO 8601 格式、带时区的发布时间 |
| `source_url` | string | 微信原文 URL，用于来源核验 |
| `content_rights` | string | 对应文章正文的权利审查状态 |
| `asset_rights` | string | 对应图片和第三方素材的权利审查状态 |

机器可读约束见
[`article-metadata.schema.json`](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/data/article-metadata.schema.json)。`author` 是微信
页面提供的字段，不等同于对全文著作权归属的确认。

## 完整性与异常口径

- 474 个合集位置连续，稳定 ID 与 `source_url` 均无重复。
- 标题中的最大期号为 482；编号 3、94、435 尚待核对。
- 356–364 位于相邻合集位置之间，且发布时间仅相隔约 21.86 小时，暂记为高度疑似一次跳号。
- 编号 246 对应两篇稳定 ID、URL 和正文均不同的帖子，不属于数据重复。
- 3 篇特别篇或特殊篇没有数字期号，`issue_no` 为 `null`。

完整核对过程见
[`completeness-reconciliation.md`](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/reports/completeness-reconciliation.md)。

## 使用边界

公开元数据可用于目录检索、描述性统计、发布节奏分析、候选内容回溯和知识图谱入口。它不含
正文文本，因此不能单独支持全文主题建模、语义嵌入或文章内容再分发。使用者应通过
`source_url` 回到原文核验，并遵守微信原文及第三方材料的原有权利条件。

## 署名建议

> 数字游戏学习研究（2026）。数字游戏学习研究公众号公开元数据集（v0.1.0）。
> https://github.com/minkaiwang/dgbl-wechat-kb

机器可读引用信息见仓库根目录
[`CITATION.cff`](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/CITATION.cff)。
