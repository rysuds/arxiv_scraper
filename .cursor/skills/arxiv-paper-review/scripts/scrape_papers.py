"""
Scrape arxiv papers by topic and date range using paperscraper.
Outputs a JSON file with paper metadata for downstream summarization.

Usage:
    python scrape_papers.py --topic "machine learning" --start 2025-01-01 --end 2025-06-01 --output papers.json
    python scrape_papers.py --topic "transformer,attention" --start 2025-01-01 --output papers.json
    python scrape_papers.py --local-dir ./my_papers --output papers.json
    python scrape_papers.py --topic "LLM" --start 2025-01-01 --local-dir ./extras --output papers.json
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def scrape_arxiv(topic_keywords: list[list[str]], output_path: str, start_date: str | None = None, end_date: str | None = None) -> list[dict]:
    from paperscraper.arxiv import get_and_dump_arxiv_papers

    jsonl_path = output_path.replace(".json", "_raw.jsonl")
    get_and_dump_arxiv_papers(topic_keywords, output_filepath=jsonl_path)

    papers = []
    with open(jsonl_path, "r") as f:
        for line in f:
            if line.strip():
                paper = json.loads(line)
                papers.append(paper)

    if start_date or end_date:
        papers = filter_by_date(papers, start_date, end_date)

    papers.sort(key=lambda p: p.get("date", ""), reverse=True)
    return papers


def filter_by_date(papers: list[dict], start_date: str | None, end_date: str | None) -> list[dict]:
    filtered = []
    for p in papers:
        pub_date = p.get("date", "")
        if not pub_date:
            filtered.append(p)
            continue
        try:
            d = pub_date[:10]
            if start_date and d < start_date:
                continue
            if end_date and d > end_date:
                continue
            filtered.append(p)
        except (ValueError, TypeError):
            filtered.append(p)
    return filtered


def extract_from_local_files(local_dir: str) -> list[dict]:
    """Extract minimal metadata from local .md, .pdf, .tex files."""
    papers = []
    local_path = Path(local_dir)
    if not local_path.exists():
        print(f"Warning: local directory {local_dir} does not exist", file=sys.stderr)
        return papers

    for fpath in sorted(local_path.iterdir()):
        if fpath.suffix.lower() in (".md", ".tex", ".txt"):
            text = fpath.read_text(errors="ignore")
            title = extract_title_from_text(text, fpath.name)
            abstract = extract_abstract_from_text(text)
            papers.append({
                "title": title,
                "authors": "",
                "date": datetime.fromtimestamp(fpath.stat().st_mtime).strftime("%Y-%m-%d"),
                "abstract": abstract,
                "doi": "",
                "source_file": str(fpath),
            })
        elif fpath.suffix.lower() == ".pdf":
            papers.append({
                "title": fpath.stem.replace("_", " ").replace("-", " ").title(),
                "authors": "",
                "date": datetime.fromtimestamp(fpath.stat().st_mtime).strftime("%Y-%m-%d"),
                "abstract": f"[PDF file: {fpath.name} — abstract extraction requires PDF parsing]",
                "doi": "",
                "source_file": str(fpath),
            })

    return papers


def extract_title_from_text(text: str, fallback: str) -> str:
    for line in text.split("\n")[:20]:
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
        match = re.match(r"\\title\{(.+?)\}", line)
        if match:
            return match.group(1)
    return Path(fallback).stem.replace("_", " ").replace("-", " ").title()


def extract_abstract_from_text(text: str) -> str:
    abstract_match = re.search(
        r"(?:## Abstract|\\begin\{abstract\})(.*?)(?:## |\\end\{abstract\}|\n## )",
        text, re.DOTALL | re.IGNORECASE
    )
    if abstract_match:
        return abstract_match.group(1).strip()[:2000]

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return " ".join(lines[:10])[:2000]


def main():
    parser = argparse.ArgumentParser(description="Scrape arxiv papers by topic and date range")
    parser.add_argument("--topic", type=str, help="Comma-separated keywords (e.g. 'LLM,transformer')")
    parser.add_argument("--start", type=str, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", type=str, help="End date YYYY-MM-DD")
    parser.add_argument("--local-dir", type=str, help="Path to local paper files (.md, .pdf, .tex)")
    parser.add_argument("--output", type=str, default="papers.json", help="Output JSON file path")
    parser.add_argument("--max-results", type=int, default=50, help="Max number of papers to return")
    args = parser.parse_args()

    all_papers = []

    if args.topic:
        keywords = [kw.strip().split(",") for kw in args.topic.split(";")]
        if len(keywords) == 1:
            keywords = [keywords[0]]
        all_papers.extend(scrape_arxiv(keywords, args.output, args.start, args.end))

    if args.local_dir:
        all_papers.extend(extract_from_local_files(args.local_dir))

    if not args.topic and not args.local_dir:
        print("Error: provide --topic and/or --local-dir", file=sys.stderr)
        sys.exit(1)

    all_papers = all_papers[:args.max_results]

    with open(args.output, "w") as f:
        json.dump(all_papers, f, indent=2, default=str)

    print(f"Scraped {len(all_papers)} papers -> {args.output}")


if __name__ == "__main__":
    main()
