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

The script scans `countries/` and `recommended/` by default and writes `reports/links_report.csv`.
