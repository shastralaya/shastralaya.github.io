#!/usr/bin/env python3
"""Fail-closed checks of a fully generated GitHub Pages site."""
from __future__ import annotations
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re


class LineReplay(HTMLParser):
    """Read exact original line text from semantic HTML without rewriting it."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=False
        self.parts=[]
        self.count=0
    def handle_starttag(self,tag,attrs):
        if tag=='span' and 'data-source-line' in dict(attrs):
            if self.active:raise ValueError('Nested original source lines')
            self.active=True;self.count+=1
    def handle_data(self,data):
        if self.active:self.parts.append(data)
    def handle_endtag(self,tag):
        if tag=='span' and self.active:self.active=False


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
    english=json.loads((out/'english-build.json').read_text(encoding='utf-8'))
    gretil=json.loads((out/'gretil-build.json').read_text(encoding='utf-8'))
    if len(english)!=8 or len(gretil)!=12:
        raise ValueError('Book source inventory differs from 8 English + 12 Sanskrit e-texts')
    expected=30 + len(gretil) + sum(b['pages'] for b in english + gretil)
    if len(html_files)!=expected:
        raise ValueError(f'Unexpected HTML page count: {len(html_files)} (expected {expected})')
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
    if len(originals)!=20:raise ValueError('Expected exactly eight English plus twelve Sanskrit originals')
    for family,records in [('texts',english),('works',gretil)]:
        for book in records:
            slug=book['slug'];start=1;combined=[];total=0
            for segment in book['segments']:
                n=segment['number']
                if n != start:raise ValueError(f'{slug}: non-consecutive reading pages')
                path=out/f'{family}/{slug}/{n}/index.html'
                if not path.is_file():raise ValueError(f'{slug}: missing reading page {n}')
                replay=LineReplay();replay.feed(path.read_bytes().decode('utf-8'))
                if replay.active:raise ValueError(f'{slug}: unclosed source line')
                expected_lines=segment['last_line']-segment['first_line']+1
                if replay.count!=expected_lines:raise ValueError(f'{slug}: line count changed in reading page {n}')
                combined.append(''.join(replay.parts));total+=replay.count;start+=1
            if total!=book['lines']:raise ValueError(f'{slug}: source line count differs')
            original_bytes=(out/f'downloads/{slug}.txt').read_bytes()
            original=original_bytes.decode('utf-8-sig' if family=='texts' else 'utf-8')
            if ''.join(combined)!=original:
                raise ValueError(f'{slug}: HTML reading pages differ from the complete source text')
            if hashlib.sha256(original_bytes).hexdigest()!=book['sha256']:
                raise ValueError(f'{slug}: source hash differs from verified build')
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
