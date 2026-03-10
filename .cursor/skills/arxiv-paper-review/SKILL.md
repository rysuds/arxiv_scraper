---
name: arxiv-paper-review
description: Scrape arxiv papers by topic and date range, generate LLM-powered high-level summaries, and output a timeline/feed-style PDF review document. Use when the user asks to review, summarize, or survey arxiv papers, create a literature review, or generate a research overview for a topic and time period.
---

# Arxiv Paper Review Generator

Scrape arxiv papers using [paperscraper](https://pypi.org/project/paperscraper/), summarize them with your own inference, and produce a polished timeline-style PDF.

## Prerequisites

Install dependencies once per environment:

```bash
pip install -r .cursor/skills/arxiv-paper-review/scripts/requirements.txt
```

## Workflow

Copy this checklist and track progress:

```
Task Progress:
- [ ] Step 1: Parse user request (topic, date range, local files)
- [ ] Step 2: Scrape papers from arxiv
- [ ] Step 3: Generate summaries for each paper
- [ ] Step 4: Generate the PDF
- [ ] Step 5: Report results to user
```

### Step 1: Parse the User Request

Extract from the user's message:

| Parameter | Required | Example |
|-----------|----------|---------|
| **Topic** | Yes | `"large language models"`, `"graph neural networks"` |
| **Start date** | Yes | `2025-01-01` |
| **End date** | No (defaults to today) | `2025-06-01` |
| **Local files** | No | Path to a directory with `.md`, `.pdf`, `.tex` files |
| **Max papers** | No (default 30) | `50` |

If the user provides keywords with multiple facets, separate them with semicolons for AND logic:
- `"transformer;attention mechanism"` → papers matching **both**
- `"LLM,GPT,Claude"` → papers matching **any** of these (OR within a group)

### Step 2: Scrape Papers

Run the scraper:

```bash
python .cursor/skills/arxiv-paper-review/scripts/scrape_papers.py \
  --topic "<KEYWORDS>" \
  --start "<YYYY-MM-DD>" \
  --end "<YYYY-MM-DD>" \
  --max-results <N> \
  --output papers.json
```

To also include local paper files:

```bash
python .cursor/skills/arxiv-paper-review/scripts/scrape_papers.py \
  --topic "<KEYWORDS>" \
  --start "<YYYY-MM-DD>" \
  --local-dir ./path/to/papers \
  --output papers.json
```

After running, read `papers.json` to verify the scrape returned results.

### Step 3: Generate Summaries

Read `papers.json` and produce a `summaries.json` file. For each paper, write a JSON object with:

```json
{
  "title": "Exact title from papers.json",
  "summary": "2-4 sentence high-level summary of the paper's contribution and significance",
  "key_findings": [
    "First key finding or contribution",
    "Second key finding or result",
    "Third finding (optional)"
  ]
}
```

**Guidelines for writing summaries:**
- Focus on **what's new** — the core contribution, not background
- Highlight practical implications or state-of-the-art improvements
- Use plain language accessible to a broad technical audience
- Mention quantitative results when available (e.g. "achieves 94.2% accuracy, a 3.1% improvement")
- Keep each summary to 2-4 sentences

After summarizing all papers, also write an **executive summary** (3-5 sentences) covering the overall landscape: dominant themes, notable trends, and standout papers.

Write `summaries.json` as a JSON array of the above objects.

### Step 4: Generate the PDF

```bash
python .cursor/skills/arxiv-paper-review/scripts/generate_pdf.py \
  --papers papers.json \
  --summaries summaries.json \
  --title "<Report Title>" \
  --period "<Start> – <End>" \
  --executive-summary "<Executive summary text>" \
  --output review.pdf
```

This produces:
- `review.pdf` — the final timeline-style PDF
- `review.html` — an HTML preview

### Step 5: Report Results

Tell the user:
1. How many papers were found and reviewed
2. The path to the generated PDF
3. A brief (2-3 sentence) verbal summary of the key themes

## Customization

### Modifying the template

The HTML/CSS template is at `.cursor/skills/arxiv-paper-review/scripts/template.html`. It uses:
- **Jinja2** for templating
- **WeasyPrint** for HTML-to-PDF conversion
- Cursor brand accent color (`#f54e00`) for timeline markers and highlights
- Source Serif 4 + Inter font pairing

### Adjusting output style

Edit `template.html` to change layout, colors, or typography. The template receives these variables:

| Variable | Type | Description |
|----------|------|-------------|
| `title` | str | Report title |
| `subtitle` | str | Subtitle line |
| `period` | str | Date range label |
| `paper_count` | int | Total papers |
| `generated_date` | str | Generation timestamp |
| `executive_summary` | str | Overall summary |
| `date_range_days` | int | Span in days |
| `unique_authors` | int | Distinct author count |
| `date_groups` | list | Papers grouped by month |

Each paper in `date_groups[].papers` has: `title`, `authors`, `date`, `doi`, `summary`, `key_findings`.
