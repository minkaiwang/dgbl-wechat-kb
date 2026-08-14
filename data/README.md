# 数据文件

- `article-metadata.jsonl`：可进入首发 Git 提交的公开安全元数据，不含正文、摘要片段或本地文章路径。
- `articles.jsonl`：本地全文检索索引，包含正文片段；正文许可确认前不进入 Git。
- `import-status.jsonl`：逐篇导入、匹配和质量状态的审计记录。
- `jieba-user-dict.txt`：中文全文搜索的领域词典。

公开索引不得包含 Cookie、Token、AppSecret、浏览器配置或读者个人数据。
