#!/usr/bin/env python3
"""Fail-closed checks of a fully generated GitHub Pages site."""
from __future__ import annotations
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re


class PageLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links=[]
        self.ids=[]
        self.language=False
    def handle_starttag(self, tag, attrs):
        attr=dict(attrs)
        if tag=='html':
            self.language=bool(attr.get('lang'))
        if 'id' in attr:self.ids.append(attr['id'])
        if tag in ('a','script','link') and (key:='href' if tag!='script' else 'src') in attr:
            self.links.append(attr[key])
        if tag in ('img','iframe') and 'src' in attr:
            self.links.append(attr['src'])


def check(out: Path) -> dict:
    files=[p for p in out.rglob('*') if p.is_file()]
    html_files=[p for p in files if p.suffix=='.html']
    if len(html_files)!=30:
        raise ValueError(f'Unexpected HTML page count: {len(html_files)} (expected 30)')
    if any(p.suffix.lower() in ('.pdf','.png','.jpg','.jpeg','.mp3') for p in files):
        raise ValueError('No scans/photographs/audio belong in the initial text-first build')
    for rel in ['index.html','assets/style.css','assets/app.js','assets/favicon.svg','gita/index.html','search/index.html','search/verses.json','sources/index.html','sitemap.xml','robots.txt','.nojekyll']:
        if not (out/rel).is_file():raise ValueError(f'Missing required file {rel}')
    data=json.loads((out/'search/verses.json').read_text(encoding='utf-8'))
    if len(data)!=701 or sorted(set(row['chapter'] for row in data))!=list(range(1,19)):
        raise ValueError('Search index incomplete')
    for n in range(1,19):
        page=(out/f'gita/{n}/index.html').read_text(encoding='utf-8')
        matches=re.findall(r'<article class="verse" id="v(\d+)">',page)
        actual=[str(v['verse']) for v in data if v['chapter']==n]
        if matches!=actual:raise ValueError(f'Chapter {n} missing/duplicate verse anchors')
        for row in (v for v in data if v['chapter']==n):
            if row['text'].splitlines()[0].strip().replace('&','&amp;').replace('<','&lt;').replace('>','&gt;') not in page:
                raise ValueError(f'Gita verse {n}.{row["verse"]} text not rendered')
    originals=[p for p in (out/'downloads').glob('*.txt')]
    if len(originals)!=8:raise ValueError('Expected exactly eight downloadable English originals')
    for page in html_files:
        parsed=PageLinks();parsed.feed(page.read_text(encoding='utf-8'))
        if not parsed.language:raise ValueError(f'Missing document language: {page.relative_to(out)}')
        if len(parsed.ids)!=len(set(parsed.ids)):raise ValueError(f'Duplicate HTML IDs: {page.relative_to(out)}')
        for href in parsed.links:
            if not href.startswith('/') or href.startswith('//'):continue
            bare=href.split('#',1)[0].split('?',1)[0]
            if not bare:continue
            dest=(out/bare.lstrip('/'))
            if dest.is_dir():dest=dest/'index.html'
            if not dest.is_file():raise ValueError(f'Broken internal link {href} in {page.relative_to(out)}')
        text=page.read_text(encoding='utf-8').lower()
        if any(marker in text for marker in ('anubhab_dey_public_resume', 'software engineer · devops', 'anubhabdey.in')):
            raise ValueError(f'Personal-site content leaked into {page.relative_to(out)}')
    return {'pages':len(html_files),'sanskrit_verses':len(data),'english_downloads':len(originals),'total_files':len(files),'bytes':sum(x.stat().st_size for x in files)}


def main():
    p=argparse.ArgumentParser();p.add_argument('--site',type=Path,default=Path(__file__).resolve().parent.parent/'_site');args=p.parse_args()
    print('SITE_CHECK_OK',json.dumps(check(args.site)))


if __name__=='__main__':main()
