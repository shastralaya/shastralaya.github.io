#!/usr/bin/env python3
"""Generate a zero-dependency, static, source-attributed Śāstra library.

No unverified Sanskrit/translation alignment, no silent omission of PG licence,
no public output until all required source files pass validation.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
from collections import defaultdict
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
from fetch import validate_gita, validate_pg  # noqa: E402

SITE_ORIGIN = 'https://shastralaya.github.io'

# Runs before CSS loads to prevent a light-theme flash on dark-mode systems.
# Manual preference is honoured on every reader, search page and source page.
THEME_BOOTSTRAP = """<script>
(function () {
  var preference = null;
  try { preference = localStorage.getItem('shastralaya-theme'); } catch (_) {}
  var systemDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  var theme = (preference === 'dark' || preference === 'light') ? preference : (systemDark ? 'dark' : 'light');
  document.documentElement.dataset.theme = theme;
  var meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = (theme === 'dark' ? '#151e1b' : '#f8f6ef');
})();
</script>"""


def e(v) -> str:
    return html.escape(str(v), quote=True)


def norm_space(s: str) -> str:
    return ' '.join(str(s).split())


def document(title: str, desc: str, content: str, canonical_path: str = '/') -> str:
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#f8f6ef"><meta name="color-scheme" content="light dark">
{THEME_BOOTSTRAP}
<meta name="description" content="{e(desc)}"><link rel="canonical" href="{SITE_ORIGIN}{e(canonical_path)}">
<link rel="icon" type="image/svg+xml" href="/assets/favicon.svg">
<link rel="stylesheet" href="/assets/style.css"><script src="/assets/app.js" defer></script>
<title>{e(title)} · Śāstrālaya</title></head>
<body><a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><div class="wrap header-inner">
<a class="brand" href="/" aria-label="Śāstrālaya home"><span class="brand-symbol" lang="sa">श्री</span><span class="brand-words">Śāstrālaya<small>A library of original words</small></span></a>
<nav class="nav" aria-label="Main navigation"><a href="/">Library</a><a href="/search/">Search verses</a><a href="/sources/">Sources</a></nav>
<button type="button" class="icon-button theme-toggle" data-theme-toggle aria-label="Switch to dark mode" aria-pressed="false" title="Switch to dark mode"><span aria-hidden="true">☾</span></button>
</div></header>
<main id="main">{content}</main>
<footer class="site-footer"><div class="wrap footer-inner"><div><strong>Śāstrālaya</strong><p>Read carefully. Attribute faithfully. Preserve without alteration.</p></div><div><a href="/sources/">Editions &amp; rights</a><span class="dot" aria-hidden="true">·</span><span>No ads. No analytics.</span></div></div></footer>
</body></html>'''


def write(root: Path, rel: str, body: str | bytes) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        path.write_bytes(body)
    else:
        path.write_text(body, encoding='utf-8')


def read_verse_records(raw: bytes, gita: dict) -> list[dict]:
    data = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data, list) or len(data) != gita['expected_verses']:
        raise ValueError('Bhagavad Gita: unexpected total verse records')
    grouped: dict[int, dict[int, dict]] = defaultdict(dict)
    for row in data:
        if not isinstance(row, dict):
            raise ValueError('Gita record must be an object')
        chapter = row.get('chapter_number')
        number = row.get('verse_number')
        raw_text = row.get('text')
        if not isinstance(chapter, int) or not isinstance(number, int) or not isinstance(raw_text, str):
            raise ValueError('Gita record missing chapter, verse or text')
        if not 1 <= chapter <= gita['expected_chapters'] or number in grouped[chapter]:
            raise ValueError(f'Gita duplicate or invalid verse: {chapter}.{number}')
        if len(raw_text.strip()) < 12 or not re.search('[\u0900-\u097f]', raw_text):
            raise ValueError(f'Gita verse {chapter}.{number} lacks Sanskrit text')
        grouped[chapter][number] = {'chapter': chapter, 'verse': number, 'text': raw_text.strip()}
    if sorted(grouped) != list(range(1, 19)):
        raise ValueError('Gita missing chapters')
    ordered = []
    for chapter in range(1, 19):
        count = gita['verse_counts'][chapter - 1]
        if sorted(grouped[chapter]) != list(range(1, count + 1)):
            raise ValueError(f'Gita chapter {chapter}: verse sequence differs from pinned record')
        ordered.extend(grouped[chapter][i] for i in range(1, count + 1))
    return ordered


def chapter_metadata(raw: bytes) -> dict[int, dict]:
    arr = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(arr, list) or len(arr) != 18:
        raise ValueError('Expected exactly 18 Gita chapter metadata records')
    result = {}
    for row in arr:
        num = row.get('chapter_number')
        if not isinstance(num, int) or not (1 <= num <= 18) or num in result:
            raise ValueError('Gita chapter metadata invalid')
        title = row.get('name')
        if not isinstance(title, str) or len(title.strip()) < 2:
            raise ValueError(f'Gita chapter {num}: missing Sanskrit name')
        result[num] = {'sanskrit': title.strip(), 'english': str(row.get('name_translation') or f'Chapter {num}').strip(), 'verses_count': row.get('verses_count')}
    if sorted(result) != list(range(1, 19)):
        raise ValueError('Gita metadata sequence invalid')
    return result


def render_card(title: str, label: str, detail: str, href: str, eyebrow: str, keywords: str, kind: str, symbol='॥') -> str:
    return f'''<article class="book-card" data-kind="{e(kind)}" data-search="{e(keywords.casefold())}">
  <div class="book-card-head"><span class="eyebrow">{e(eyebrow)}</span><span class="small-symbol" lang="sa">{e(symbol)}</span></div>
  <h3>{e(title)}</h3><p class="edition-tag">{e(label)}</p><p class="book-description">{e(detail)}</p>
  <a class="card-link" href="{e(href)}">Open text <span aria-hidden="true">↗</span></a>
</article>'''


def render_home(manifest: dict, chapters: dict[int, dict], count: int) -> str:
    cards = [render_card('Bhagavad Gītā', 'Sanskrit · 18 chapters', 'Verse-by-verse digital Sanskrit text with stable chapter links. This is one attributed digital edition.', '/gita/', 'Mūla · Sanskrit', 'gita bhagavad गीता संस्कृत sanskrit krishna कृष्ण', 'sanskrit', 'गी')]
    for b in manifest['english']:
        cards.append(render_card(b['title'], b['kind'] + ' · English', b['description'], '/texts/' + b['slug'] + '/', 'Historical English', ' '.join([b['title'], b['work'], b['translator'], b['description'], b['slug']]), 'english'))
    lead = f'''<section class="hero wrap"><div class="hero-text">
<p class="eyebrow hero-overline">A free, independent reading library</p>
<h1>Come closer<br>to the <em>text.</em></h1>
<p class="hero-desc">The original Sanskrit where we can verify it. Historical translations with their authors named. A calm space for reading, inquiry, and study.</p>
<div class="hero-ctas"><a class="button button-primary" href="/gita/">Begin with the Gītā <span aria-hidden="true">→</span></a><a class="quiet-link" href="#collection">Browse the collection ↓</a></div>
</div><div class="hero-art" aria-hidden="true"><div class="art-circle art-circle-outer"></div><div class="art-circle art-circle-inner"></div><div class="art-script" lang="sa">श्री</div><div class="art-caption">पठनम् · मननम्</div></div></section>
<div class="wrap"><div class="divider-ornament"><span>✧</span></div></div>
<section class="collection wrap" id="collection" aria-labelledby="collection-title"><div class="section-heading"><div><p class="eyebrow">The reading room</p><h2 id="collection-title">The collection<span class="accent">.</span></h2><p>Each card identifies the language and scope of its edition. Books without a verified Sanskrit edition are never presented as Sanskrit originals.</p></div><div class="collection-stat">{count} texts<span>1 Sanskrit mūla · {len(manifest['english'])} English editions</span></div></div>
<div class="toolbar"><div class="search-input-wrap"><label for="library-search">Find a work</label><input id="library-search" type="search" placeholder="Try Gītā, Upaniṣad, yoga, Viṣṇu…" autocomplete="off" data-library-search></div>
<div class="filter-tabs" role="group" aria-label="Filter editions"><button type="button" class="filter-tab selected" data-filter="all" aria-pressed="true">All</button><button type="button" class="filter-tab" data-filter="sanskrit" aria-pressed="false">Sanskrit</button><button type="button" class="filter-tab" data-filter="english" aria-pressed="false">English</button></div></div>
<p class="result-count" data-result-count role="status" aria-live="polite">Showing {count} editions</p>
<div class="book-grid" data-book-grid>{''.join(cards)}</div><p class="empty-message" data-empty-message hidden>No editions match your search. Try a different name or language.</p></section>
<section class="afterword wrap"><div><p class="eyebrow">Our approach</p><h2>One text at a time.<br><em>No borrowed certainty.</em></h2></div><p>Every published transcription has a named source. Different recensions, commentaries, and translations remain distinct. Scans and research leads do not count as hosted readable books. The library expands only when an edition meets its checks. <a href="/sources/">Read the editorial method →</a></p></section>'''
    return document('The reading library', 'Free, text-first Sanskrit scriptures and attributed historical English editions.', lead)


def render_gita_index(meta: dict[int, dict], verses: list[dict], gita: dict) -> str:
    cards = []
    for n in range(1, 19):
        info = meta[n]
        cards.append(f'''<a href="/gita/{n}/" class="chapter-card"><span class="chapter-number">{n:02d}</span><div><span class="chapter-native" lang="sa">{e(info['sanskrit'])}</span><span class="chapter-trans">{e(info['english'])}</span></div><span class="chapter-count">{gita['verse_counts'][n-1]} verses</span><span class="chapter-arrow" aria-hidden="true">↗</span></a>''')
    body = f'''<div class="wrap page-container"><a class="breadcrumb" href="/">← Library</a>
<div class="intro-block"><p class="eyebrow">Sanskrit · Itihāsa</p><h1>Bhagavad <em>Gītā.</em></h1><p class="native-subtitle" lang="sa">श्रीमद्भगवद्गीता</p><p>All {len(verses)} verse records from the identified <em>gita/gita</em> digital transcription, grouped in 18 chapters. No English translation has been silently paired with these verses.</p><div class="source-strip"><span>18 chapters</span><span>{len(verses)} verse records</span><a href="/sources/#gita">Edition &amp; attribution ↗</a></div></div>
<section aria-label="Chapters" class="chapter-section"><h2 class="section-title">Choose a chapter</h2><div class="chapter-grid">{''.join(cards)}</div></section>
<div class="reading-note"><strong>About this witness</strong><p>{e(gita['disclaimer'])}</p></div></div>'''
    return document('Bhagavad Gītā', 'Read all 18 chapters of a source-attributed Sanskrit Bhagavad Gītā.', body, '/gita/')


def render_gita_chapter(chapter: int, entries: list[dict], meta: dict[int, dict]) -> str:
    item = meta[chapter]
    verse_html = []
    for v in entries:
        ref = f'{chapter}.{v["verse"]}'
        verse_html.append(f'''<article class="verse" id="v{v['verse']}"><div class="verse-meta"><span>Verse {e(ref)}</span><a class="verse-permalink" href="#v{v['verse']}" aria-label="Direct link to verse {e(ref)}">#</a></div>
<p class="verse-devanagari" lang="sa">{e(v['text'])}</p><button type="button" class="copy-verse" data-copy-verse data-ref="{e(ref)}">Copy verse <span aria-hidden="true">⧉</span></button></article>''')
    options=''.join(f'<option value="/gita/{i}/"'+(' selected' if i==chapter else '')+f'>Chapter {i:02d}: {e(meta[i]["english"])}</option>' for i in range(1,19))
    prev=f'<a href="/gita/{chapter-1}/">← Chapter {chapter-1}</a>' if chapter>1 else '<span></span>'
    next_=f'<a href="/gita/{chapter+1}/">Chapter {chapter+1} →</a>' if chapter<18 else '<a href="/gita/">All chapters ↑</a>'
    body=f'''<div class="wrap reader-layout"><aside class="reader-side"><a class="breadcrumb" href="/gita/">← All chapters</a><div class="side-card"><p class="eyebrow">Bhagavad Gītā</p><strong>Chapter {chapter}</strong><p lang="sa">{e(item['sanskrit'])}</p><label for="chapter-jump">Change chapter</label><select id="chapter-jump" data-chapter-jump>{options}</select><small>{len(entries)} verses · Sanskrit</small><a href="/sources/#gita">Source &amp; rights ↗</a></div></aside>
<div class="reader-main"><div class="chapter-heading"><p class="eyebrow">अध्याय {chapter} · Chapter {chapter:02d}</p><h1 lang="sa">{e(item['sanskrit'])}</h1><p>{e(item['english'])}</p><div class="read-tools"><span>Original Sanskrit transcription</span><div class="font-tools"><button type="button" data-font-step="-1" aria-label="Decrease verse font size">A−</button><button type="button" data-font-step="1" aria-label="Increase verse font size">A+</button></div></div></div>
<div class="verses">{''.join(verse_html)}</div><nav class="chapter-nav" aria-label="Adjacent chapters">{prev}{next_}</nav><p class="end-note">This is a named digital transcription, not a claim that all Sanskrit manuscripts agree on every reading.</p></div></div>'''
    return document(f'Chapter {chapter}: {item["english"]}', f'Bhagavad Gītā Chapter {chapter}, Sanskrit verses from a documented digital edition.', body, f'/gita/{chapter}/')


def render_english(book: dict, text: str) -> str:
    body=f'''<div class="wrap english-reader"><div class="english-top"><a class="breadcrumb" href="/">← Library</a><p class="eyebrow">Historical English edition · Project Gutenberg #{book['id']}</p><h1>{e(book['title'])}</h1><p class="english-byline">{e(book['translator'])}</p><p>{e(book['description'])}</p><div class="english-actions"><a class="button button-outline" href="/downloads/{book['slug']}.txt" download>Download original TXT ↓</a><a class="quiet-link" href="https://www.gutenberg.org/ebooks/{book['id']}" target="_blank" rel="noopener noreferrer">Original source ↗</a><div class="font-tools"><button type="button" data-font-step="-1" aria-label="Decrease text size">A−</button><button type="button" data-font-step="1" aria-label="Increase text size">A+</button></div></div></div><div class="english-note"><strong>Edition note.</strong> Historical English source text, not an original Sanskrit transcription. Full original Gutenberg text, including licence and editorial notices, is retained below. Use browser Find (Ctrl+F) for in-text search.</div><div class="english-content" data-reader-text>{e(text)}</div><a class="back-to-top" href="#main">Back to top ↑</a></div>'''
    return document(book['title'], f"{book['title']}, a historical English edition attributed to {book['translator']}.", body, f"/texts/{book['slug']}/")


def render_search() -> str:
    body='''<section class="wrap search-page"><a class="breadcrumb" href="/">← Library</a><div class="intro-block compact-intro"><p class="eyebrow">Explore the Sanskrit</p><h1>Find a <em>verse.</em></h1><p>Search the published Bhagavad Gītā transcription by Devanagari text or verse reference, such as <strong>2.47</strong>. Results link directly to the corresponding chapter and verse.</p></div>
<div class="search-box-large"><label for="verse-search">Search Sanskrit verses</label><input type="search" id="verse-search" placeholder="Enter Sanskrit words or 2.47" autocomplete="off" data-verse-search><p class="hint">Only this one transcription is indexed. More works will be added after source checks.</p></div>
<p class="result-count" role="status" aria-live="polite" data-verse-status>Enter a word or verse reference to begin.</p><div data-verse-results class="search-results"></div></section>'''
    return document('Verse search', 'Search source-attributed Sanskrit Bhagavad Gītā verse text.', body, '/search/')


def render_sources(manifest: dict, receipts: dict) -> str:
    g=manifest['sanskrit'][0]
    rows=[]
    for b in manifest['english']:
        rows.append(f'''<tr><td><a href="/texts/{e(b['slug'])}/">{e(b['title'])}</a></td><td>{e(b['translator'])}</td><td>English, {e(b['kind'])}</td><td><a href="https://www.gutenberg.org/ebooks/{b['id']}">PG #{b['id']}</a></td></tr>''')
    receipt_rows=''.join(f'<li><code>{e(r["file"])}</code> · SHA-256 <code>{e(r["sha256"])}</code></li>' for r in receipts['receipts'])
    body=f'''<div class="wrap sources-page"><a class="breadcrumb" href="/">← Library</a><div class="intro-block compact-intro"><p class="eyebrow">Accountability</p><h1>Sources &amp; <em>editions.</em></h1><p>Every hosted book identifies where its text came from, which edition is represented, and what we do not claim. Sources are not interchangeable with translations or commentaries.</p></div>
<section class="source-detail" id="gita"><h2>Bhagavad Gītā · Sanskrit</h2><p><strong>Edition:</strong> {e(g['edition'])}. <strong>Declared scope:</strong> {e(g['scope'])}.</p><p><a href="{e(g['source'])}">Pinned upstream Git revision ↗</a> · <a href="{e(g['license_url'])}">Upstream Unlicense ↗</a>. Attribution is supplied even though the source release dedicates its contents to the public domain.</p><p>{e(g['disclaimer'])}</p><p>The text's original Sanskrit is ancient. The modern digital transcription is separately attributed. No modern translations, AI explanations, or commentaries are reproduced under this licence claim.</p></section>
<section class="source-detail"><h2>Historical English editions</h2><p>These are specific complete Project Gutenberg e-books, not whole scripture corpora. Source text is preserved in full, including original Gutenberg notices. The website is independent of Project Gutenberg; its trademark is used only to identify provenance.</p><div class="table-scroll"><table><thead><tr><th>Hosted work</th><th>Translator / editor</th><th>Scope</th><th>Source</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section class="source-detail"><h2>What is not published yet</h2><p>Modern translations without redistribution permission; uncollated Sanskrit witnesses; the SARIT editions with unresolved edition-specific checks; and scanned PDFs. These are not shown as hosted books.</p></section>
<section class="source-detail"><h2>Build receipts</h2><p>These SHA-256 hashes identify the exact source bytes used for this particular generated release. Upstream Gutenberg texts can change; future releases must generate new receipts. The Sanskrit Git blobs are separately pinned by original Git object hash.</p><ul class="receipt-list">{receipt_rows}</ul></section>
<section class="source-detail"><h2>Corrections and stewardship</h2><p>Notice a missing passage or transcription error? Report it with the text, chapter, verse and a cited witness. We preserve the source reading and document any correction rather than silently mixing editions.</p><p>Traditional teachings are presented as attributed historical sources. A reader should distinguish the mūla, each bhāṣya, and any modern editorial interpretation. Historical medicine, law and astrology are not presented as modern professional advice.</p></section></div>'''
    return document('Sources and editorial policy', 'Source records, licenses, and editorial status for every hosted text.', body, '/sources/')


def build(source_dir: Path, out: Path, manifest: dict | None = None) -> dict:
    manifest = manifest or json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    g = manifest['sanskrit'][0]
    vbytes = (source_dir / 'gita-verses.json').read_bytes()
    cbytes = (source_dir / 'gita-chapters.json').read_bytes()
    validate_gita(vbytes, g['git_blob_sha1'], 'Gita verses')
    validate_gita(cbytes, g['chapter_blob_sha1'], 'Gita chapters')
    verse_records = read_verse_records(vbytes, g)
    chapters = chapter_metadata(cbytes)
    for n in range(1, 19):
        if chapters[n]['verses_count'] != g['verse_counts'][n - 1]:
            raise ValueError(f'Gita chapter {n}: chapter metadata count mismatch')
    english = {}
    for book in manifest['english']:
        raw = (source_dir / f"pg{book['id']}.txt").read_bytes()
        validate_pg(raw, book)
        english[book['slug']] = raw.decode('utf-8-sig')
    receipts = {'schema': 1, 'receipts': [
        {'file': name, 'sha256': hashlib.sha256((source_dir / name).read_bytes()).hexdigest(), 'bytes': (source_dir / name).stat().st_size}
        for name in ['gita-verses.json', 'gita-chapters.json'] + [f"pg{b['id']}.txt" for b in manifest['english']]
    ]}
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'Output must be absent or empty (safe build): {out}')
    out.mkdir(parents=True, exist_ok=True)
    assets = ROOT / 'src' / 'assets'
    (out / 'assets').mkdir(exist_ok=True)
    for file in ('style.css', 'app.js', 'favicon.svg'):
        shutil.copyfile(assets / file, out / 'assets' / file)
    write(out, 'index.html', render_home(manifest, chapters, 1 + len(manifest['english'])))
    write(out, 'gita/index.html', render_gita_index(chapters, verse_records, g))
    grouped = defaultdict(list)
    for v in verse_records:
        grouped[v['chapter']].append(v)
    for n in range(1, 19):
        write(out, f'gita/{n}/index.html', render_gita_chapter(n, grouped[n], chapters))
    for book in manifest['english']:
        write(out, f"texts/{book['slug']}/index.html", render_english(book, english[book['slug']]))
        write(out, f"downloads/{book['slug']}.txt", english[book['slug']])
    write(out, 'search/index.html', render_search())
    write(out, 'sources/index.html', render_sources(manifest, receipts))
    write(out, 'search/verses.json', json.dumps(verse_records, ensure_ascii=False, separators=(',', ':')) + '\n')
    write(out, 'source-receipts.json', json.dumps(receipts, ensure_ascii=False, indent=2) + '\n')
    paths = ['/','/gita/','/search/','/sources/'] + [f'/gita/{n}/' for n in range(1,19)] + [f"/texts/{b['slug']}/" for b in manifest['english']]
    write(out, 'sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{SITE_ORIGIN}{p}</loc></url>\n' for p in paths) + '</urlset>\n')
    write(out, 'robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE_ORIGIN}/sitemap.xml\n')
    write(out, '.nojekyll', '')
    return {'books': 9, 'sanskrit_verses': len(verse_records), 'chapters': 18, 'html_pages': len(paths), 'size_bytes': sum(p.stat().st_size for p in out.rglob('*') if p.is_file())}


def main() -> None:
    arg = argparse.ArgumentParser()
    arg.add_argument('--source-dir', type=Path, default=ROOT / '_sources')
    arg.add_argument('--out', type=Path, default=ROOT / '_site')
    options=arg.parse_args()
    print('BUILD_OK', json.dumps(build(options.source_dir, options.out), ensure_ascii=False))


if __name__ == '__main__':
    main()
