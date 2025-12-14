#!/usr/bin/env python3
"""Remove broken feed links from OPML files using the broken CSV.

Usage:
  python3 scripts/remove_broken_links.py --broken reports/links_report_broken.csv

This will back up modified OPMLs to `backups/` and write a report to
`reports/removed_links.md`.
"""
from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, List


def load_broken_csv(path: Path) -> Dict[Path, List[str]]:
    mapping = defaultdict(list)
    with path.open(encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            opml = Path(row['opml_file'])
            url = row['xmlUrl'] or row['htmlUrl']
            if not url:
                continue
            mapping[opml].append(url)
    return mapping


def remove_from_opml(opml_path: Path, urls: List[str]) -> List[Dict[str, str]]:
    removed = []
    if not opml_path.exists():
        return removed

    try:
        tree = ET.parse(opml_path)
        root = tree.getroot()
        changed = False
        # find outline elements with matching xmlUrl or htmlUrl
        for parent in root.findall('.//'):
            # iterate children copy since we'll delete
            for child in list(parent):
                if child.tag.lower().endswith('outline'):
                    xml = child.attrib.get('xmlUrl')
                    html = child.attrib.get('htmlUrl') or child.attrib.get('htmlurl')
                    if xml in urls or html in urls:
                        removed.append({'opml': str(opml_path), 'title': child.attrib.get('title') or child.attrib.get('text') or '', 'url': xml or html})
                        parent.remove(child)
                        changed = True
        if changed:
            tree.write(opml_path, encoding='utf-8', xml_declaration=True)
        return removed
    except ET.ParseError:
        # fallback to regex removal for malformed files
        import re
        text = opml_path.read_text(encoding='utf-8', errors='replace')
        orig = text
        for url in urls:
            # remove entire outline tags that contain the url
            text = re.sub(r'<outline[^>]*(?:xmlUrl|htmlUrl)\s*=\s*"%s"[^>]*/?>' % re.escape(url), '', text, flags=re.IGNORECASE)
        if text != orig:
            opml_path.write_text(text, encoding='utf-8')
            # best-effort: record removals by url
            for url in urls:
                if url in orig and url not in text:
                    removed.append({'opml': str(opml_path), 'title': '', 'url': url})
        return removed


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--broken', required=True)
    p.add_argument('--backup-dir', default='backups')
    p.add_argument('--report', default='reports/removed_links.md')
    args = p.parse_args()

    broken_map = load_broken_csv(Path(args.broken))
    os.makedirs(args.backup_dir, exist_ok=True)
    all_removed = []
    for opml, urls in broken_map.items():
        src = Path(opml)
        if not src.exists():
            continue
        # backup
        dst = Path(args.backup_dir) / opml
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        removed = remove_from_opml(src, urls)
        all_removed.extend(removed)

    # write report
    rep = Path(args.report)
    rep.parent.mkdir(parents=True, exist_ok=True)
    with rep.open('w', encoding='utf-8') as fh:
        fh.write('# Removed Broken Links\n\n')
        fh.write('This file lists links removed from OPML files because the link checker reported them as broken.\n\n')
        fh.write('| OPML file | Title | URL |\n')
        fh.write('|---|---|---|\n')
        for r in all_removed:
            fh.write(f"| {r['opml']} | {r['title']} | {r['url']} |\n")

    print(f'Removed {len(all_removed)} entries; report written to {rep}; backups in {args.backup_dir}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
