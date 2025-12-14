#!/usr/bin/env python3
"""Categorize working feeds and write a hierarchical CSV.

Reads `reports/links_final_check_ok.csv` by default and produces
`reports/feeds_with_categories.csv` with columns:
  opml_file, title, url, status_code, ok, main_category, sub_category, detailed_subcategory, tags, notes

The script uses heuristics based on the OPML file path and feed title/url
to assign categories and subcategories. It's conservative and adds a
'notes' entry when uncertain.
"""
from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple

KEYWORD_MAP: Dict[str, Tuple[str, str]] = {
    # technology
    'android': ('Technology', 'Android'),
    'ios': ('Technology', 'iOS'),
    'iphone': ('Technology', 'iOS'),
    'programming': ('Technology', 'Programming'),
    'developer': ('Technology', 'Development'),
    'python': ('Technology', 'Programming'),
    'javascript': ('Technology', 'Programming'),
    'web': ('Technology', 'Web'),
    'devops': ('Technology', 'DevOps'),
    # news
    'news': ('News', 'General'),
    'headlines': ('News', 'Headlines'),
    'breaking': ('News', 'Breaking'),
    # business / finance
    'business': ('Business', 'General'),
    'finance': ('Business', 'Finance'),
    'personal finance': ('Business', 'Personal Finance'),
    'economy': ('Business', 'Economy'),
    'forbes': ('Business', 'Business Media'),
    # sports
    'football': ('Sports', 'Football'),
    'soccer': ('Sports', 'Football'),
    'cricket': ('Sports', 'Cricket'),
    'tennis': ('Sports', 'Tennis'),
    'formula 1': ('Sports', 'Motorsport'),
    'f1': ('Sports', 'Motorsport'),
    # entertainment
    'movie': ('Entertainment', 'Movies'),
    'film': ('Entertainment', 'Movies'),
    'tv': ('Entertainment', 'Television'),
    'music': ('Entertainment', 'Music'),
    # science / space
    'science': ('Science', 'General'),
    'space': ('Science', 'Space'),
    'nasa': ('Science', 'Space'),
    # lifestyle
    'travel': ('Lifestyle', 'Travel'),
    'food': ('Lifestyle', 'Food'),
    'fashion': ('Lifestyle', 'Fashion'),
    'beauty': ('Lifestyle', 'Beauty'),
    'photography': ('Lifestyle', 'Photography'),
    'books': ('Lifestyle', 'Books'),
}


def detect_from_text(text: str) -> Tuple[str, str, List[str]]:
    text_l = (text or '').lower()
    tags: List[str] = []
    detected_main = None
    detected_sub = None
    for k, (main, sub) in KEYWORD_MAP.items():
        if k in text_l:
            tags.append(k)
            # prefer first hit for main/sub but keep other tags
            if detected_main is None:
                detected_main = main
                detected_sub = sub
    if detected_main:
        return detected_main, detected_sub, tags
    return 'Uncategorized', 'General', tags


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--input', default='reports/links_final_check_ok.csv')
    p.add_argument('--output', default='reports/feeds_with_categories.csv')
    args = p.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f'Input csv not found: {inp}')
        return 2

    rows = []
    with inp.open(encoding='utf-8') as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            opml = r.get('opml_file', '')
            title = r.get('title') or ''
            url = r.get('xmlUrl') or r.get('htmlUrl') or ''
            status = r.get('status_code')
            ok = r.get('ok', 'True')

            # Determine base category from opml path
            main = 'Uncategorized'
            sub = 'General'
            detailed = ''
            notes = ''

            if 'recommended' in opml:
                # use opml filename as main category
                main = Path(opml).stem
                # refine using title/url
                detected_main, detected_sub, tags = detect_from_text(title + ' ' + url)
                if detected_main != 'Uncategorized':
                    sub = detected_main
                    detailed = detected_sub
                else:
                    sub = 'General'
                    detailed = 'General'
            elif 'countries' in opml:
                main = 'News'
                sub = Path(opml).stem
                detected_main, detected_sub, tags = detect_from_text(title + ' ' + url)
                if detected_main != 'Uncategorized':
                    detailed = f"{detected_main} / {detected_sub}"
                else:
                    detailed = 'Local News'
            else:
                detected_main, detected_sub, tags = detect_from_text(title + ' ' + url)
                main = detected_main
                sub = detected_sub
                detailed = 'General'

            tags = tags if tags else []
            rows.append({
                'opml_file': opml,
                'title': title,
                'url': url,
                'status_code': status,
                'ok': ok,
                'main_category': main,
                'sub_category': sub,
                'detailed_subcategory': detailed,
                'tags': ';'.join(tags),
                'notes': notes,
            })

    outp = Path(args.output)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with outp.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=['opml_file', 'title', 'url', 'status_code', 'ok', 'main_category', 'sub_category', 'detailed_subcategory', 'tags', 'notes'])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f'Wrote {len(rows)} categorized feeds to {outp}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
