# v0.2.0 发布后复核

## 公开状态

- 仓库：<https://github.com/minkaiwang/dgbl-wechat-kb>，可见性为 Public；
- Release：<https://github.com/minkaiwang/dgbl-wechat-kb/releases/tag/v0.2.0>，正式版、非草稿、非预发布；
- 发布时 `main` 与注释标签 `v0.2.0` 均指向
  `f877962fc25b15456b7b087c3edc9fd2574f8c87`；该标签继续固定 v0.2.0，`main` 可接收后续维护记录；
- GitHub Actions CI：成功，包含 Ruff、31 项测试、确定性 Release 构建、完整历史扫描与严格站点构建；
- 匿名 HTTP 复核：仓库页、Release 页与 `SHA256SUMS.txt` 均返回 200。

## 数据资产

- GitHub Release 上传资产：8 个，总计 11,628,453 字节；
- 8/8 个匿名下载文件与本地发布候选的字节数和 SHA256 完全一致；
- `SHA256SUMS.txt` 中 7 条数据资产校验全部通过；
- 全文 JSONL：475 条；元数据 JSONL：475 条；
- 全文 ZIP：483 个条目；元数据 ZIP：6 个条目；
- GitHub 页面显示 `Assets 10` 时，另 2 个为平台自动生成的源码 ZIP 和 TAR，不属于上传数据资产。

## 展示与边界

- GitHub README 与 Release 的自绘 SVG 横幅、数据概览、下载表和许可说明均正常渲染；
- 自动化浏览器检查覆盖桌面 1440 × 1000 与移动 390 × 844；该证据不等同于真人可用性测试；
- 文章原创文字按 CC BY-NC 4.0 署名“靓点迷人”；公开原图为 0，第三方素材保持原有权利状态；
- 私有 HTML、原始图片、响应快照、抓取日志与浏览器配置未进入公开 Git 历史或 Release。

## 持续更新

以 v0.2.0 的 475 篇为公开基线，每累计新增 25 篇经授权、通过审计且可公开的文章，常规更新
一次 GitHub 仓库与数据集 Release；下一常规批次目标为 500 篇。每批同步正文、元数据、索引、
许可、QA、站点、引用信息、变更记录与数据包。纠错、安全、隐私、撤稿或权利问题不等待批次。
