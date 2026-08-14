v0.1.1 是公众号公开元数据集的首次增量更新。Release 主体仍是帖子公开元数据，skill 和
处理脚本用于维护数据集，不作为独立数据产品。

## 下载

- [完整 ZIP 数据包](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.1/dgbl-wechat-metadata-v0.1.1.zip)
- [JSONL](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.1/dgbl-wechat-metadata-v0.1.1.jsonl)
- [CSV（UTF-8 BOM）](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.1/dgbl-wechat-metadata-v0.1.1.csv)
- [JSON Schema](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.1/dgbl-wechat-metadata-v0.1.1.schema.json)
- [SHA256SUMS.txt](https://github.com/minkaiwang/dgbl-wechat-kb/releases/download/v0.1.1/SHA256SUMS.txt)

## 数据更新

- 记录数：475，较 v0.1.0 新增 1 条；
- 新增位置：475；
- 新增编号：483；
- 新增文章发布时间：2026-08-14 16:56:20（UTC+8）；
- 完整日期范围：2024-07-11 至 2026-08-14；
- 稳定 ID 与来源 URL 重复数：0 / 0。

新增文章为“[数字游戏学习 483] 研学旅行前加入生成式 AI 聊天脚手架的数字游戏，学生会
学得更好吗？”。原有 474 条记录无删除、无字段变化。

## 工程与审计更新

- 导入器增加受限于 `https://mp.weixin.qq.com/` 的系统 `curl` 回退，在 Python 直连遇到
  微信验证页时仍能处理同一公开原文 URL；
- 主页截图与当前合集改用异步口径记录：截图同期差额仍为 12 篇，不把新增文章误算成
  历史差额减少；
- 补查本机公众号工作区、PDF、微信短链接和搜狗微信 10 页结果，未发现可核实的合集外文章；
- README 信息图、数据字典、Schema、引用文件和公开发布门禁同步更新。

## 公开边界

Release 只包含标题、日期、栏目、稳定 ID、作者字段、原文链接和权利状态等元数据，不包含
文章正文、摘要片段、原始 HTML、图片、接口快照或私有日志。元数据采用 CC BY 4.0；代码采用
MIT License。文章正文和第三方素材保持原有权利状态。

## 已知限制

用户提供的主页截图显示 486 篇原创内容，截图同期合集为 474 篇，历史差额为 12 篇。编号
483 发布后的主页原创数尚未重新核验。编号 3、94、435 仍待后台清单核对，356–364 暂记为
高度疑似一次性编号跳号。
