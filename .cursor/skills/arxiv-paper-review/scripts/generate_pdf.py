"""
Generate a timeline/feed-style PDF from a papers JSON + summaries JSON.

Usage:
    python generate_pdf.py --papers papers.json --summaries summaries.json --output review.pdf \
        --title "LLM Research Review" --period "Jan 2025 – Jun 2025"
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML


TEMPLATE_DIR = Path(__file__).parent
TEMPLATE_FILE = "template.html"


def group_papers_by_month(papers: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for p in papers:
        raw_date = p.get("date", "")
        try:
            dt = datetime.strptime(raw_date[:10], "%Y-%m-%d")
            key = dt.strftime("%Y-%m")
            label = dt.strftime("%B %Y")
        except (ValueError, TypeError):
            key = "unknown"
            label = "Undated"
        groups[key].append(p)

    sorted_keys = sorted(groups.keys(), reverse=True)
    return [{"label": _month_label(k, groups[k]), "papers": groups[k]} for k in sorted_keys]


def _month_label(key: str, papers: list) -> str:
    if key == "unknown":
        return "Undated"
    try:
        dt = datetime.strptime(key, "%Y-%m")
        return dt.strftime("%B %Y")
    except ValueError:
        return key


def count_unique_authors(papers: list[dict]) -> int:
    authors = set()
    for p in papers:
        raw = p.get("authors", "")
        if isinstance(raw, list):
            for a in raw:
                authors.add(a.strip().lower())
        elif isinstance(raw, str) and raw:
            for a in raw.split(","):
                authors.add(a.strip().lower())
    authors.discard("")
    return len(authors)


def compute_date_span(papers: list[dict]) -> int | None:
    dates = []
    for p in papers:
        try:
            dates.append(datetime.strptime(p["date"][:10], "%Y-%m-%d"))
        except (ValueError, TypeError, KeyError):
            pass
    if len(dates) < 2:
        return None
    return (max(dates) - min(dates)).days


def merge_summaries(papers: list[dict], summaries: list[dict]) -> list[dict]:
    summary_map = {}
    for s in summaries:
        key = s.get("title", "").strip().lower()
        summary_map[key] = s

    merged = []
    for p in papers:
        key = p.get("title", "").strip().lower()
        s = summary_map.get(key, {})
        merged.append({
            "title": p.get("title", "Untitled"),
            "authors": p.get("authors", ""),
            "date": p.get("date", ""),
            "doi": p.get("doi", ""),
            "summary": s.get("summary", p.get("abstract", "")),
            "key_findings": s.get("key_findings", []),
        })
    return merged


def render_pdf(papers: list[dict], output_path: str, title: str, period: str, executive_summary: str = ""):
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template(TEMPLATE_FILE)

    date_groups = group_papers_by_month(papers)

    html_str = template.render(
        title=title,
        subtitle=f"Arxiv Literature Review — {period}",
        period=period,
        paper_count=len(papers),
        generated_date=datetime.now().strftime("%B %d, %Y"),
        executive_summary=executive_summary,
        date_range_days=compute_date_span(papers),
        unique_authors=count_unique_authors(papers),
        date_groups=date_groups,
    )

    html_out = output_path.replace(".pdf", ".html")
    with open(html_out, "w") as f:
        f.write(html_str)

    HTML(string=html_str, base_url=str(TEMPLATE_DIR)).write_pdf(output_path)
    print(f"PDF generated -> {output_path}")
    print(f"HTML preview  -> {html_out}")


def main():
    parser = argparse.ArgumentParser(description="Generate timeline PDF from paper data")
    parser.add_argument("--papers", required=True, help="Path to papers.json (from scrape_papers.py)")
    parser.add_argument("--summaries", required=True, help="Path to summaries.json (agent-generated)")
    parser.add_argument("--output", default="review.pdf", help="Output PDF path")
    parser.add_argument("--title", default="Arxiv Paper Review", help="Report title")
    parser.add_argument("--period", default="", help="Time period label (e.g. 'Jan–Jun 2025')")
    parser.add_argument("--executive-summary", default="", help="Executive summary text")
    args = parser.parse_args()

    with open(args.papers) as f:
        papers = json.load(f)
    with open(args.summaries) as f:
        summaries = json.load(f)

    merged = merge_summaries(papers, summaries)
    render_pdf(merged, args.output, args.title, args.period, args.executive_summary)


if __name__ == "__main__":
    main()
