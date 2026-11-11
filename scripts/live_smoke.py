#!/usr/bin/env python3
"""After Pages deploy: verify the *actual served* reading site, not a green job badge.

A GitHub default Jekyll job once overwrote this site with the rendered README.
This check rejects such an outcome by inspecting distinct generated pages.
"""
from __future__ import annotations
import sys
import time
import urllib.request

ORIGIN='https://shastralaya.github.io'
EXPECTED={
    '/': ('<main id="main">','class="hero wrap"','The collection'),
    '/gita/2/': ('<main id="main">','id="v47"','Bhagavad Gītā'),
    '/works/mukundamala/1/': ('<main id="main">','data-source-lines','Mukundamālā'),
    '/texts/gita-arnold/1/': ('<main id="main">','reader-paper','The Song Celestial'),
    '/search/': ('<main id="main">','data-verse-search','Find a'),
}


def validate_response(path: str, content: str) -> None:
    for needle in EXPECTED[path]:
        if needle not in content:
            raise ValueError(f'{path}: missing {needle!r}; wrong or incomplete deployed artifact')


def probe() -> None:
    # Read 5 distinct URLs; a successful deployment of only README.md fails.
    # Retry only because the Pages CDN might briefly serve the previous release.
    for attempt in range(1,13):
        try:
            for path in EXPECTED:
                url=ORIGIN+path
                req=urllib.request.Request(url,headers={
                    'User-Agent':'Shastralaya-deploy-check/1.2',
                    'Cache-Control':'no-cache',
                })
                with urllib.request.urlopen(req,timeout=15) as response:
                    if response.status != 200:
                        raise ValueError(f'{path}: HTTP {response.status}')
                    raw=response.read(300_001)
                    if len(raw)>300_000:
                        raise ValueError(f'{path}: response unexpectedly large')
                    charset=response.headers.get_content_charset() or 'utf-8'
                    content=raw.decode(charset)
                    validate_response(path,content)
            print('LIVE_SITE_OK: homepage, Bhagavad Gita 2, Mukundamala, English reader, search')
            return
        except (OSError,ValueError,UnicodeError) as err:
            if attempt==12:
                raise SystemExit(f'LIVE_SITE_FAILED after 12 attempts: {err}')
            print(f'LIVE_SITE_RETRY {attempt}/12: {err}',flush=True)
            time.sleep(5)


if __name__=='__main__':
    probe()
