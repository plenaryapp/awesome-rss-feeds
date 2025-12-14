#!/usr/bin/env python3
"""Scan .opml files and check feed links.

Usage:
  python3 scripts/check_opml_links.py --output reports/links_report.csv

Outputs CSV with columns: opml_file,title,xmlUrl,htmlUrl,status_code,ok,error
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional

try:
    import requests
except Exception:
    print("Missing dependency 'requests'. Please install with: pip install requests", file=sys.stderr)
    raise


@dataclass
class LinkCheckResult:
    opml_file: str
    title: Optional[str]
    xmlUrl: Optional[str]
    htmlUrl: Optional[str]
    status_code: Optional[int]
    ok: bool
    error: Optional[str]


def find_outlines(elem: ET.Element):
    # Recursively yield outline elements
    if elem.tag.lower().endswith('outline'):
        yield elem
    for child in elem:
        yield from find_outlines(child)


def parse_opml(path: Path) -> List[LinkCheckResult]:
    results: List[LinkCheckResult] = []
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        for out in find_outlines(root):
            xmlUrl = out.attrib.get('xmlUrl')
            htmlUrl = out.attrib.get('htmlUrl') or out.attrib.get('htmlurl')
            title = out.attrib.get('title') or out.attrib.get('text')
            if not xmlUrl and not htmlUrl:
                continue
            results.append(LinkCheckResult(
                opml_file=str(path),
                title=title,
                xmlUrl=xmlUrl,
                htmlUrl=htmlUrl,
                status_code=None,
                ok=False,
                error=None,
            ))
        return results
    except ET.ParseError:
        # Fallback: some OPML files aren't strictly valid XML (unescaped & etc.).
        # Use a regex to extract xmlUrl/htmlUrl/title attributes.
        import re

        text = path.read_text(encoding='utf-8', errors='replace')
        pattern = re.compile(r'<outline[^>]*>')
        for match in pattern.finditer(text):
            tag = match.group(0)
            xml_match = re.search(r'xmlUrl\s*=\s*"([^\"]+)"', tag)
            html_match = re.search(r'htmlUrl\s*=\s*"([^\"]+)"', tag, re.IGNORECASE)
            title_match = re.search(r'title\s*=\s*"([^\"]+)"', tag)
            text_match = re.search(r'text\s*=\s*"([^\"]+)"', tag)
            xmlUrl = xml_match.group(1) if xml_match else None
            htmlUrl = html_match.group(1) if html_match else None
            title = title_match.group(1) if title_match else (text_match.group(1) if text_match else None)
            if not xmlUrl and not htmlUrl:
                continue
            results.append(LinkCheckResult(
                opml_file=str(path),
                title=title,
                xmlUrl=xmlUrl,
                htmlUrl=htmlUrl,
                status_code=None,
                ok=False,
                error=None,
            ))
        return results


def check_url(url: str, timeout: int = 10) -> (Optional[int], Optional[str]):
    headers = {"User-Agent": "awesome-rss-feeds-link-checker/1.0"}
    try:
        # Use HEAD first to be lighter; fall back to GET if not allowed
        resp = requests.head(url, allow_redirects=True, timeout=timeout, headers=headers)
        # Some servers return 405 for HEAD; try GET then
        if resp.status_code == 405:
            resp = requests.get(url, allow_redirects=True, timeout=timeout, headers=headers)
        return resp.status_code, None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def check_result_item(item: LinkCheckResult, timeout: int = 10) -> LinkCheckResult:
    # Prefer xmlUrl then htmlUrl
    target = item.xmlUrl or item.htmlUrl
    if not target:
        item.ok = False
        item.error = "no-url"
        return item
    status, error = check_url(target, timeout=timeout)
    item.status_code = status
    item.error = error
    item.ok = (status is not None and status < 400)
    return item


def gather_opml_files(root_dir: Path) -> List[Path]:
    files = list(root_dir.rglob('*.opml'))
    return files


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--dirs', nargs='*', default=['countries', 'recommended'], help='Directories to scan')
    p.add_argument('--output', default='reports/links_report.csv')
    p.add_argument('--workers', type=int, default=10)
    p.add_argument('--timeout', type=int, default=10)
    args = p.parse_args()

    root = Path('.')
    opml_paths: List[Path] = []
    for d in args.dirs:
        opml_paths.extend(gather_opml_files(root / d))

    if not opml_paths:
        print('No .opml files found in', args.dirs, file=sys.stderr)
        return 2

    all_items: List[LinkCheckResult] = []
    for opml in sorted(opml_paths):
        all_items.extend(parse_opml(opml))

    os.makedirs(Path(args.output).parent, exist_ok=True)

    # Check concurrently
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(check_result_item, it, args.timeout): it for it in all_items}
        for fut in as_completed(futures):
            # result() will propagate exceptions if any
            fut.result()

    # Write full CSV
    with open(args.output, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['opml_file', 'title', 'xmlUrl', 'htmlUrl', 'status_code', 'ok', 'error'])
        writer.writeheader()
        for it in all_items:
            writer.writerow(asdict(it))

    # Write filtered CSVs
    ok_file = Path(args.output).with_name(Path(args.output).stem + '_ok.csv')
    bad_file = Path(args.output).with_name(Path(args.output).stem + '_broken.csv')
    passed = sum(1 for it in all_items if it.ok)
    failed = sum(1 for it in all_items if not it.ok)

    with open(ok_file, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['opml_file', 'title', 'xmlUrl', 'htmlUrl', 'status_code', 'ok', 'error'])
        writer.writeheader()
        for it in all_items:
            if it.ok:
                writer.writerow(asdict(it))

    with open(bad_file, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=['opml_file', 'title', 'xmlUrl', 'htmlUrl', 'status_code', 'ok', 'error'])
        writer.writeheader()
        for it in all_items:
            if not it.ok:
                writer.writerow(asdict(it))

    print(f'Results written to {args.output}: {passed} working, {failed} broken')
    print(f'Working list: {ok_file}   Broken list: {bad_file}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
