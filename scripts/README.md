Link checker
============

Quick script to check feed links in OPML files and write a CSV report.

Install:

```bash
pip install -r requirements.txt
```

Run:

```bash
python3 scripts/check_opml_links.py --output reports/links_report.csv
```

Categorize feeds and write hierarchical CSV:

```bash
python3 scripts/categorize_feeds.py --input reports/links_final_check_ok.csv --output reports/feeds_with_categories.csv
```

The script scans `countries/` and `recommended/` by default and writes `reports/links_report.csv`.
