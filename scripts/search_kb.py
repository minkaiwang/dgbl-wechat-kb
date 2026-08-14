from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

import jieba
from build_index import plain_text
from kb_common import jsonl_load, read_markdown_frontmatter

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def tokenize(value: str) -> list[str]:
    tokens: list[str] = []
    for token in jieba.lcut_for_search(value.lower()):
        clean = token.strip()
        if not clean or re.fullmatch(r"[\W_]+", clean):
            continue
        if len(clean) == 1 and not clean.isascii():
            continue
        tokens.append(clean)
    return tokens


def excerpt(text: str, terms: list[str], width: int = 180) -> str:
    lower = text.lower()
    positions = [lower.find(term.lower()) for term in terms if lower.find(term.lower()) >= 0]
    start = max(0, (min(positions) if positions else 0) - width // 3)
    value = text[start : start + width].strip()
    return ("…" if start else "") + value + ("…" if start + width < len(text) else "")


def search(public_root: Path, query: str, limit: int) -> list[dict]:
    root = public_root.resolve()
    index_path = root / "data" / "articles.jsonl"
    if not index_path.exists():
        raise FileNotFoundError("缺少 data/articles.jsonl；请先运行 scripts/build_index.py")
    rows = jsonl_load(index_path)
    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    documents: list[tuple[dict, str, Counter[str]]] = []
    document_frequency: Counter[str] = Counter()
    for row in rows:
        path = root / row["markdown_path"]
        _, body = read_markdown_frontmatter(path)
        text = plain_text(body)
        counts = Counter(tokenize(text))
        documents.append((row, text, counts))
        document_frequency.update(set(counts))

    average_length = sum(sum(counts.values()) for _, _, counts in documents) / max(
        1, len(documents)
    )
    results: list[dict] = []
    for row, text, counts in documents:
        document_length = sum(counts.values())
        score = 0.0
        for term in query_tokens:
            frequency = counts[term]
            if not frequency:
                continue
            df = document_frequency[term]
            inverse = math.log(1 + (len(documents) - df + 0.5) / (df + 0.5))
            denominator = frequency + 1.5 * (1 - 0.75 + 0.75 * document_length / average_length)
            score += inverse * frequency * 2.5 / denominator
        title = str(row["display_title"])
        if query.lower() in title.lower():
            score += 8.0
        score += sum(1.5 for term in set(query_tokens) if term in tokenize(title))
        if score > 0:
            results.append(
                {
                    "score": round(score, 4),
                    "title": title,
                    "published_at": row["published_at"],
                    "series": row["series"],
                    "markdown_path": row["markdown_path"],
                    "source_url": row["source_url"],
                    "excerpt": excerpt(text, query_tokens),
                }
            )
    results.sort(key=lambda item: (item["score"], item["published_at"]), reverse=True)
    return results[:limit]


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the local WeChat knowledge base")
    parser.add_argument("query")
    parser.add_argument("--public-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = search(args.public_root, args.query, args.limit)
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0
    for number, item in enumerate(results, start=1):
        print(f"{number}. [{item['score']:.3f}] {item['title']}")
        print(f"   {item['published_at'][:10]} · {item['series']}")
        print(f"   {item['excerpt']}")
        print(f"   {item['source_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
