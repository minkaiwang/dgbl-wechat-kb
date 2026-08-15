# v0.2.0：475 篇公众号文章全文知识库

<p align="center">
  <img src="https://raw.githubusercontent.com/minkaiwang/dgbl-wechat-kb/v0.2.0/docs/assets/readme-overview.svg" width="100%" alt="数字游戏学习研究公众号全文知识库 v0.2.0 概览">
</p>

v0.2.0 将“数字游戏学习研究”从公开元数据集升级为全文知识库。Release 的主体是公众号文章
数据集，不是单独发布 skill。现有公开合集位置 1–475 的 475 篇原创文字由作者网名“靓点迷人”
按 CC BY-NC 4.0 授权。

> 一次下载即可获得可阅读的 Markdown 全文，也可直接使用 JSONL 构建 RAG、语义检索和主题分析。

## 一眼看懂

| 项目 | v0.2.0 |
|---|---:|
| Markdown 全文 | 475 篇 |
| 发布时间范围 | 2024-07-11 至 2026-08-14 |
| 全文 JSONL | 475 条 |
| 图片处理 | 14,334 个文字占位符，公开原图 0 |
| 正文许可 | CC BY-NC 4.0，署名“靓点迷人” |

## 下载

### 全文知识库

| 文件 | 适合用途 | 下载 |
|---|---|---|
| 全文 ZIP | 475 篇 Markdown、JSONL、Schema、目录与许可 | [下载 ZIP](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/dgbl-wechat-fulltext-v0.2.0.zip) |
| 全文 JSONL | RAG、语义检索、主题分析 | [下载 JSONL](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/dgbl-wechat-fulltext-v0.2.0.jsonl) |
| 全文 Schema | 程序化字段校验 | [下载 Schema](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/dgbl-wechat-fulltext-v0.2.0.schema.json) |

### 轻量元数据

| 文件 | 适合用途 | 下载 |
|---|---|---|
| 元数据 ZIP | 一次取得 JSONL、CSV、Schema 与许可 | [下载 ZIP](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/dgbl-wechat-metadata-v0.2.0.zip) |
| 元数据 JSONL | 知识图谱、目录服务与程序处理 | [下载 JSONL](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/dgbl-wechat-metadata-v0.2.0.jsonl) |
| 元数据 CSV | Excel、SPSS/R 前期整理与人工浏览 | [下载 CSV](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/dgbl-wechat-metadata-v0.2.0.csv) |
| 元数据 Schema | 程序化字段校验 | [下载 Schema](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/dgbl-wechat-metadata-v0.2.0.schema.json) |
| SHA256 | 核验全部 7 个数据资产 | [下载校验和](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.2.0/SHA256SUMS.txt) |

## 本版内容

- 475 篇按年份组织的 Markdown 正文；
- 475 条结构化全文记录，正文位于 `body_markdown`；
- 可点击文章目录、`llms.txt` 检索索引与知识站全文搜索；
- 不含正文的 JSONL/CSV 轻量元数据，方便目录和描述性分析；
- 许可清单、全文/元数据 Schema、Manifest、QA 与完整性报告；
- 可复现、确定性的 Release 构建脚本。

## 权利与隐私

- 文章原创文字：CC BY-NC 4.0，署名“靓点迷人”；
- 公开元数据与项目文档：CC BY 4.0；
- 软件代码：MIT；
- 原始图片、论文图表、期刊封面、照片和其他第三方素材：未进入公开仓库或数据包；
- 14,334 个图片出现位置只保留文字占位符；
- 5 处论文通讯作者邮箱已从正文删除，审计记录不公开邮箱值。

## 完整性边界

本版完整覆盖目前发现的公开合集位置 1–475，不声明覆盖公众号后台全部原创内容。主页截图同期
仍有 12 篇历史差额待后台清单核对；编号 3、94、435 未决，356–364 高度疑似一次性编号跳号。
