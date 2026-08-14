# 数据文件

- `article-metadata.jsonl`：公开安全元数据，不含正文、摘要片段或本地文章路径。
- `articles.jsonl`：本地全文检索索引，包含正文片段；正文许可确认前不进入 Git。
- `import-status.jsonl`：逐篇导入、匹配和质量状态的审计记录。
- `jieba-user-dict.txt`：中文全文搜索的领域词典。

公开索引不得包含 Cookie、Token、AppSecret、浏览器配置或读者个人数据。

`article-metadata.jsonl` 与 `import-status.jsonl` 按根目录 `DATA-LICENSE.md` 中的 CC BY 4.0
提供；其中的微信文章正文与素材权利状态不因元数据开放而改变。
