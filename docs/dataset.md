# 数据集说明

## 版本快照

| 项目 | v0.2.0 |
|---|---|
| 数据对象 | “数字游戏学习研究”微信公众号公开文章全文与元数据 |
| 文章数 | 475 |
| 合集位置 | 1–475，连续 |
| 发布时间 | 2024-07-11 至 2026-08-14 |
| 原创文字许可 | CC BY-NC 4.0，署名“靓点迷人” |
| 元数据许可 | CC BY 4.0 |
| 图片 | 不包含原图，仅保留文字占位符 |

本版本以已发现的公开合集为收录边界，不宣称覆盖公众号后台的全部原创内容。

## Release 文件

### 全文知识库

- `dgbl-wechat-fulltext-v0.2.0.zip`：475 篇 Markdown、全文 JSONL、Schema、目录、索引、
  Manifest 与正文许可；
- `dgbl-wechat-fulltext-v0.2.0.jsonl`：UTF-8，每行一篇文章，正文位于
  `body_markdown`；
- `dgbl-wechat-fulltext-v0.2.0.schema.json`：单条全文记录的 JSON Schema 2020-12。

### 轻量元数据

- `dgbl-wechat-metadata-v0.2.0.zip`：元数据 JSONL、CSV、Schema、Manifest 与许可；
- `dgbl-wechat-metadata-v0.2.0.jsonl`：不含正文，每行一条元数据；
- `dgbl-wechat-metadata-v0.2.0.csv`：UTF-8 with BOM，适合 Excel；
- `dgbl-wechat-metadata-v0.2.0.schema.json`：单条元数据记录的 JSON Schema。

`SHA256SUMS.txt` 列出以上 7 个数据资产的 SHA256。全部文件从
[GitHub Releases](https://github.com/minkaiwang/dgbl-wechat-kb/releases) 下载。

## 轻量元数据字段

| 字段 | 类型 | 含义 |
|---|---|---|
| `schema_version` | integer | 轻量元数据结构版本，当前为 2 |
| `article_id` | string | 由微信消息 ID 与图文序号构成的稳定 ID |
| `position` | integer | 公开合集中的连续位置 |
| `issue_no` | integer / null | 从标题解析的期号，特别篇等可为空 |
| `title` | string | 微信原始标题 |
| `display_title` | string / null | 去除栏目和期号前缀后的展示标题 |
| `series` | string / null | 从标题前缀解析的原始栏目 |
| `author` | string | 文章作者网名，当前为“靓点迷人” |
| `licensor` | string | 正文许可署名，当前为“靓点迷人” |
| `published_at` | string | 带时区的 ISO 8601 发布时间 |
| `source_url` | string | 微信原文 URL |
| `content_rights` | string | 当前 475 篇均为 `CC-BY-NC-4.0` |
| `content_license_url` | string | CC BY-NC 4.0 许可链接 |
| `asset_rights` | string | 图片与第三方素材状态，当前为 `pending_review` |

## 全文记录扩展字段

全文 JSONL 包含上述核心字段，并增加：

| 字段 | 类型 | 含义 |
|---|---|---|
| `tags` | array[string] | 从栏目和内容处理中保留的标签 |
| `markdown_path` | string | ZIP 或仓库中的 Markdown 路径 |
| `text_chars` | integer | 导入时记录的正文字符数 |
| `image_count` | integer | 单篇文章内去重后的图像源数量 |
| `image_occurrence_count` | integer | 正文中图像实际出现位置数量 |
| `image_policy` | string | 固定为 `placeholder` |
| `body_markdown` | string | 不含 YAML frontmatter 的 Markdown 正文 |

`image_count` 与 `image_occurrence_count` 不应直接相等：同一图像 URL 在一篇文章多次出现时，
前者只计一次，后者按每个占位符计数。

## 读取示例

```python
import json
from pathlib import Path

records = [
    json.loads(line)
    for line in Path("dgbl-wechat-fulltext-v0.2.0.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
]

first = records[0]
print(first["title"])
print(first["body_markdown"][:200])
```

使用正文开展 RAG、主题建模或其他分析时，应把 `article_id` 和 `source_url` 一同保留在结果
中，方便回到来源核验。自动摘要、翻译或改写须标明修改，并遵守非商业条件。

## 完整性与异常口径

- 475 个合集位置连续，稳定 ID 与 `source_url` 均无重复；
- 标题中的最大期号为 483；编号 3、94、435 尚待核对；
- 356–364 位于相邻合集位置之间，发布时间仅相隔约 21.86 小时，暂记为高度疑似一次跳号；
- 编号 246 对应两篇稳定 ID、URL 和正文均不同的帖子，不属于数据重复；
- 3 篇特别篇或特殊篇没有数字期号，`issue_no` 为 `null`。

完整核对过程见
[完整性报告](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/reports/completeness-reconciliation.md)。

## 许可与引用

文章原创文字的详细许可范围见
[`TEXT-LICENSE.md`](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/TEXT-LICENSE.md)，
图片和第三方素材的排除口径见
[`RIGHTS.md`](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/RIGHTS.md)。

推荐引用：

> 靓点迷人（2026）。数字游戏学习研究 · 公众号全文知识库（v0.2.0）。
> https://github.com/minkaiwang/dgbl-wechat-kb

机器可读引用信息见
[`CITATION.cff`](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/CITATION.cff)。
