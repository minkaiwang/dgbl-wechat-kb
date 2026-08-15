---
name: dgbl-kb
description: 'Maintain the “数字游戏学习研究” WeChat Official Account knowledge base on E: by discovering album items, importing public articles into auditable Markdown, separating private raw assets from Git content, building Chinese search indexes, and running completeness, quality, and rights checks. Use for updating, repairing, searching, auditing, or preparing this specific公众号知识库 for Git review or publication.'
---

# DGBL 公众号知识库

Work in `E:\DGBL-WeChat-KB\public-repo`. Read `AGENTS.md`, `README.md`, `RIGHTS.md`, and the latest files in `reports/` before making changes.

## Workflow

1. Preserve the two-layer boundary: raw HTML, original images, response snapshots, and uncertain items stay in `E:\DGBL-WeChat-KB\private-archive`; only reviewed derivatives enter Git.
2. Refresh the public album inventory with `scripts/discover_album.py`. Preserve `chksm` in article URLs; removing it causes WeChat verification redirects.
3. Import with `scripts/import_articles.py`. Keep `image-mode=placeholder` until asset rights are cleared. Use resume state; never silently omit failures.
4. Run `scripts/build_index.py`, then `scripts/qa_kb.py`, tests, and `mkdocs build --strict`.
5. Search with `scripts/search_kb.py "query"`. Answers must cite the local article path and original WeChat URL.
6. Stop before creating a remote repository, pushing, enabling Pages, or declaring article text/images open source unless the user has confirmed the content license and publication scope.
7. Use v0.2.0's 475 articles as the maintenance baseline. Prepare a routine repository and dataset Release update after each 25 newly authorized, audited, publicly eligible articles; the next routine target is 500. Treat this count only as a scheduling trigger, and handle corrections, security, privacy, retractions, and rights issues immediately.

Read [references/project-layout.md](references/project-layout.md) when repairing paths, interpreting statuses, or preparing a release.
