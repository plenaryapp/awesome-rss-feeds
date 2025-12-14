#!/usr/bin/env python3
"""Generate a comprehensive report of all removed outline entries by comparing
`backups/` to the current repository OPML files.

Writes `reports/removed_links_all.md`.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict


def parse_outlines(text: str) -> List[Dict[str, str]]:
    # Try XML parse, fallback to regex extraction
    try:
        root = ET.fromstring(text)
        items = []
        for elem in root.findall('.//'):
            if elem.tag.lower().endswith('outline'):
                items.append({'title': elem.attrib.get('title') or elem.attrib.get('text') or '', 'xml': elem.attrib.get('xmlUrl') or '', 'html': elem.attrib.get('htmlUrl') or elem.attrib.get('htmlurl') or ''})
        return items
    except ET.ParseError:
        import re
        items = []
        for tag in re.findall(r'<outline[^>]*>', text, flags=re.IGNORECASE):
            title = (re.search(r'title\s*=\s*"([^\"]+)"', tag) or re.search(r'text\s*=\s*"([^\"]+)"', tag))
            xml = re.search(r'xmlUrl\s*=\s*"([^\"]+)"', tag)
            html = re.search(r'htmlUrl\s*=\s*"([^\"]+)"', tag, flags=re.IGNORECASE)
            items.append({'title': title.group(1) if title else '', 'xml': xml.group(1) if xml else '', 'html': html.group(1) if html else ''})
        return items


def main() -> int:
    backups = Path('backups')
    rows = []
    if not backups.exists():
        print('No backups/ directory found; nothing to report')
        return 1

    for path in backups.rglob('*.opml'):
        rel = path.relative_to(backups)
        orig_text = path.read_text(encoding='utf-8', errors='replace')
        cur_path = Path('.') / rel
        if not cur_path.exists():
            continue
        cur_text = cur_path.read_text(encoding='utf-8', errors='replace')
        orig_items = parse_outlines(orig_text)
        cur_items = parse_outlines(cur_text)
        # identify items in orig but not in current by url
        cur_urls = set(it['xml'] or it['html'] for it in cur_items if it['xml'] or it['html'])
        for it in orig_items:
            url = it['xml'] or it['html']
            if url and url not in cur_urls:
                rows.append({'opml': str(rel), 'title': it['title'], 'url': url})

    out = Path('reports/removed_links_all.md')
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as fh:
        fh.write('# All Removed Links\n\n')
        fh.write('| OPML file | Title | URL |\n')
        fh.write('|---|---|---|\n')
        for r in rows:
            fh.write(f"| {r['opml']} | {r['title']} | {r['url']} |\n")

    print(f'Wrote {len(rows)} removed link entries to {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
