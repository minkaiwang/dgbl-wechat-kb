# Project layout and release gates

## Paths

- Public Git working tree: `E:\DGBL-WeChat-KB\public-repo`
- Non-Git archive: `E:\DGBL-WeChat-KB\private-archive`
- Source inventory: `private-archive\urls\articles.jsonl`
- Public import state: `public-repo\data\import-status.jsonl`
- Machine index: `public-repo\data\articles.jsonl`
- Human QA reports: `public-repo\reports\`

## Status rules

- `discovered`: present in inventory, not processed yet.
- `imported`: Markdown exists and minimum automated checks passed.
- `failed`: fetch or conversion failed; keep the error.
- `uncertain`: content exists but identity, fidelity, or rights need review.
- `missing`: expected from an authoritative list but no retrievable source is known.
- `duplicate`: stable ID or canonical source duplicates another item.

## Release gates

Require all of the following before public release:

1. Reconcile the profile count, public album count, and missing issue numbers.
2. Resolve failed and duplicate states or document each accepted exception.
3. Confirm a license for article text separately from the MIT code license.
4. Clear, replace, omit, or separately license every third-party image.
5. Pass tests, Ruff, `mkdocs build --strict`, and a rendered sample review.
6. Obtain explicit user confirmation before remote creation, push, Pages deployment, or visibility changes.
