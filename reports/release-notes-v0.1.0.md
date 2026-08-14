这是本项目首次正式数据发布。Release 的主体是 **474 条公众号帖子公开元数据**；处理代码、
质量报告和 `dgbl-kb` Skill 随仓库源码提供，Skill 不是本次发布的独立数据产品。

## 下载

- [完整 ZIP 数据包](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.0/dgbl-wechat-metadata-v0.1.0.zip)
- [JSONL](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.0/dgbl-wechat-metadata-v0.1.0.jsonl)
- [CSV（UTF-8 BOM）](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.0/dgbl-wechat-metadata-v0.1.0.csv)
- [JSON Schema](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.0/dgbl-wechat-metadata-v0.1.0.schema.json)
- [SHA256SUMS.txt](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.0/SHA256SUMS.txt)

## 数据快照

- 记录数：474；
- 公开合集位置：1–474，连续；
- 发布时间：2024-07-11 至 2026-08-12；
- 稳定 ID 重复：0；
- 原文 URL 重复：0；
- 正文、摘要片段、原始 HTML 与图片：0。

## 数据包内容

完整 ZIP 包含 JSONL、CSV、JSON Schema、`MANIFEST.json`、数据许可和包内 README。所有资产
均由 `scripts/build_release_assets.py` 确定性生成，并通过 `SHA256SUMS.txt` 校验。

## 许可与边界

公开元数据、信息图与项目文档采用 CC BY 4.0；软件代码采用 MIT。微信文章正文、摘要片段、
图片及第三方材料保持原有权利状态，不包含在本 Release 中。

## 已知缺口

公众号主页显示 486 篇原创内容，公开合集当前为 474 篇，差额 12 篇尚待后台清单对账。
编号 3、94、435 未决；356–364 暂记为高度疑似一次性编号跳号。

字段字典、质量口径和复现命令见仓库 [README](https://github.com/minkaiwang/dgbl-wechat-kb)
及[数据集说明](https://github.com/minkaiwang/dgbl-wechat-kb/blob/main/docs/dataset.md)。
