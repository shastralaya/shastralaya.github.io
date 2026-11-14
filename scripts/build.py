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
from gretil import validate_text as validate_gretil, segment as segment_gretil  # noqa: E402

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
        path.write_bytes(body.encode('utf-8'))  # preserves CRLF and Unicode on Windows, too


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
    for b in manifest['gretil']:
        cards.append(render_card(b['title'], 'Sanskrit · IAST · ' + b['category'],
            b['source_note'] + ' Original line order preserved; exact source and licence recorded.',
            '/works/' + b['slug'] + '/', 'Sanskrit e-text',
            ' '.join([b['title'], b['category'], b['source_note'], b['slug']]), 'sanskrit'))
    for b in manifest['english']:
        cards.append(render_card(b['title'], b['kind'] + ' · English', b['description'], '/texts/' + b['slug'] + '/', 'Historical English', ' '.join([b['title'], b['work'], b['translator'], b['description'], b['slug']]), 'english'))
    lead = f'''<section class="hero wrap"><div class="hero-text">
<p class="eyebrow hero-overline">A free, independent reading library</p>
<h1>Come closer<br>to the <em>text.</em></h1>
<p class="hero-desc">The original Sanskrit where we can verify it. Historical translations with their authors named. A calm space for reading, inquiry, and study.</p>
<div class="hero-ctas"><a class="button button-primary" href="/gita/">Begin with the Gītā <span aria-hidden="true">→</span></a><a class="quiet-link" href="#collection">Browse the collection ↓</a></div>
</div><div class="hero-art" aria-hidden="true"><div class="art-circle art-circle-outer"></div><div class="art-circle art-circle-inner"></div><div class="art-script" lang="sa">श्री</div><div class="art-caption">पठनम् · मननम्</div></div></section>
<div class="wrap"><div class="divider-ornament"><span>✧</span></div></div>
<section class="collection wrap" id="collection" aria-labelledby="collection-title"><div class="section-heading"><div><p class="eyebrow">The reading room</p><h2 id="collection-title">The collection<span class="accent">.</span></h2><p>Each card identifies the language and scope of its edition. Books without a verified Sanskrit edition are never presented as Sanskrit originals.</p></div><div class="collection-stat">{count} texts<span>{1+len(manifest['gretil'])} Sanskrit e-texts · {len(manifest['english'])} English editions</span></div></div>
<div class="toolbar"><div class="search-input-wrap"><label for="library-search">Find a work</label><input id="library-search" type="search" placeholder="Try Gītā, Upaniṣad, yoga, Viṣṇu…" autocomplete="off" data-library-search></div>
<div class="filter-tabs" role="group" aria-label="Filter editions"><button type="button" class="filter-tab selected" data-filter="all" aria-pressed="true">All</button><button type="button" class="filter-tab" data-filter="sanskrit" aria-pressed="false">Sanskrit</button><button type="button" class="filter-tab" data-filter="english" aria-pressed="false">English</button></div></div>
<p class="result-count" data-result-count role="status" aria-live="polite">Showing {count} editions</p>
<div class="book-grid" data-book-grid>{''.join(cards)}</div><p class="empty-message" data-empty-message hidden>No editions match your search. Try a different name or language.</p></section>
<section class="afterword wrap"><div><p class="eyebrow">Our approach</p><h2>Texts first, always.<br><em>No borrowed certainty.</em></h2></div><p>Every published transcription has a named source. Different recensions, commentaries, and translations remain distinct. Scans and research leads do not count as hosted readable books. The library expands only when an edition meets its checks. <a href="/sources/">Read the editorial method →</a></p></section>'''
    return document('The reading library', 'Free, text-first Sanskrit scriptures and attributed historical English editions.', lead)


def render_gita_index(meta: dict[int, dict], verses: list[dict], gita: dict) -> str:
    cards = []
    for n in range(1, 19):
        info = meta[n]
        cards.append(f'''<a href="/gita/{n}/" class="chapter-card"><span class="chapter-number">{n:02d}</span><div><span class="chapter-native" lang="sa">{e(info['sanskrit'])}</span><span class="chapter-trans">{e(info['english'])}</span></div><span class="chapter-count">{gita['verse_counts'][n-1]} verses</span><span class="chapter-arrow" aria-hidden="true">↗</span></a>''')
    body = f'''<div class="wrap page-container"><a class="breadcrumb" href="/">← Library</a>
<div class="intro-block"><p class="eyebrow">Sanskrit · Itihāsa</p><h1>Bhagavad <em>Gītā.</em></h1><p class="native-subtitle" lang="sa">श्रीमद्भगवद्गीता</p><p>All {len(verses)} verse records from the identified <em>gita/gita</em> digital transcription, grouped in 18 chapters. No English translation has been silently paired with these verses.</p><div class="source-strip"><span>18 chapters</span><span>{len(verses)} verse records</span><a href="/sources/#gita">Edition &amp; attribution ↗</a></div></div>
<p class="continue-note" data-continue-book="gita" hidden></p><section aria-label="Chapters" class="chapter-section"><h2 class="section-title">Choose a chapter</h2><div class="chapter-grid">{''.join(cards)}</div></section>
<div class="reading-note"><strong>About this witness</strong><p>{e(gita['disclaimer'])}</p></div></div>'''
    return document('Bhagavad Gītā', 'Read all 18 chapters of a source-attributed Sanskrit Bhagavad Gītā.', body, '/gita/')



def page_sidebar(prefix: str, current: int, total: int, title: str,
                 kind: str = 'Page', labels: dict[int, str] | None = None) -> str:
    """Accessible, bounded left-side navigation for a static reading page.

    Always render the current twenty-page group in HTML, independently of JS.
    Other groups can be selected in place with JS, without loading hundreds
    of links in every one of a long book's reading pages.
    """
    if not 1 <= current <= total:
        raise ValueError('Reader page outside its published range')
    if not re.fullmatch(r'/(?:gita|texts/[a-z0-9-]+|works/[a-z0-9-]+)/', prefix):
        raise ValueError('Invalid reader URL prefix')
    group = 20
    first = ((current - 1) // group) * group + 1
    last = min(first + group - 1, total)
    labels = labels or {}
    items = ''.join(
        '<li><a href="' + e(f'{prefix}{i}/') + '"'
        + (' aria-current="page"' if i == current else '')
        + '><span>' + e(f'{kind} {i}') + '</span>'
        + (f'<small>{e(labels[i])}</small>' if i in labels else '')
        + '</a></li>'
        for i in range(first, last + 1)
    )
    ranges = ''
    if total > group:
        choices = ''.join(
            f'<option value="{i}"' + (' selected' if i == first else '')
            + f'>{e(kind)}s {i}–{min(i + group - 1, total)}</option>'
            for i in range(1, total + 1, group)
        )
        ranges = (f'<label class="reading-range-label">Choose {kind.lower()} range'
                  f'<select data-reading-range>{choices}</select></label>')
    content = (
        f'<p class="eyebrow">Reading navigation</p>'
        f'<a class="reading-sidebar-book" href="{e(prefix)}">{e(title)}</a>'
        f'<p class="reading-sidebar-count">{e(kind)} {current} of {total}</p>'
        f'<p class="reading-sidebar-hint">Use ← / → to turn {kind.lower()}s</p>'
        f'{ranges}<nav aria-label="{e(kind)} list"><ol class="reading-sidebar-list"'
        f' data-reading-page-list>{items}</ol></nav>'
    )
    attrs = (f'data-reading-sidebar data-reading-base="{e(prefix)}"'
             f' data-reading-total="{total}" data-reading-current="{current}"'
             f' data-reading-kind="{e(kind)}"')
    # Two responsive views share the same source-generated links; the mobile
    # disclosure stays closed until the reader explicitly opens it.
    return (
        f'<div class="reading-page-sidebar" {attrs}>'
        f'<div class="reading-sidebar-desktop">{content}</div>'
        f'<details class="reading-sidebar-mobile"><summary>'
        f'{e(kind)}s <strong>{current} / {total}</strong> <span>View list</span>'
        f'</summary><div class="reading-sidebar-mobile-content">{content}</div>'
        f'</details></div>'
    )


def render_gita_chapter(chapter: int, entries: list[dict], meta: dict[int, dict]) -> str:
    item = meta[chapter]
    verse_html = []
    for v in entries:
        ref = f'{chapter}.{v["verse"]}'
        verse_html.append(f'''<article class="verse" id="v{v['verse']}"><div class="verse-meta"><span>Verse {e(ref)}</span><a class="verse-permalink" href="#v{v['verse']}" aria-label="Direct link to verse {e(ref)}">#</a></div>
<p class="verse-devanagari" lang="sa">{e(v['text'])}</p><button type="button" class="copy-verse" data-copy-verse data-ref="{e(ref)}">Copy verse <span aria-hidden="true">⧉</span></button></article>''')
    options=''.join(f'<option value="/gita/{i}/"'+(' selected' if i==chapter else '')+f'>Chapter {i:02d}: {e(meta[i]["english"])}</option>' for i in range(1,19))
    prev=f'<a data-reader-prev href="/gita/{chapter-1}/">← Chapter {chapter-1}</a>' if chapter>1 else '<span></span>'
    next_=f'<a data-reader-next href="/gita/{chapter+1}/">Chapter {chapter+1} →</a>' if chapter<18 else '<a href="/gita/">All chapters ↑</a>'
    body=f'''<div class="wrap reader-layout"><aside class="reader-side"><a class="breadcrumb" href="/gita/">← All chapters</a><div class="side-card"><p class="eyebrow">Bhagavad Gītā</p><strong>Chapter {chapter}</strong><p lang="sa">{e(item['sanskrit'])}</p><label for="chapter-jump">Change chapter</label><select id="chapter-jump" data-chapter-jump>{options}</select><small>{len(entries)} verses · Sanskrit</small><a href="/sources/#gita">Source &amp; rights ↗</a></div>
{page_sidebar('/gita/',chapter,18,'Bhagavad Gītā','Chapter',{n:meta[n]['english'] for n in range(1,19)})}</aside>
<div class="reader-main" data-reading-page data-book-id="gita" data-part="{chapter}" data-part-total="18"><div class="chapter-heading"><p class="eyebrow">अध्याय {chapter} · Chapter {chapter:02d}</p><h1 lang="sa">{e(item['sanskrit'])}</h1><p>{e(item['english'])}</p><div class="read-tools"><span>Original Sanskrit transcription</span></div></div>
{reader_controls(False)}<div class="verses" data-reader-text>{''.join(verse_html)}</div><nav class="chapter-nav" aria-label="Adjacent chapters">{prev}{next_}</nav><p class="end-note">This is a named digital transcription, not a claim that all Sanskrit manuscripts agree on every reading.</p></div></div>'''
    return document(f'Chapter {chapter}: {item["english"]}', f'Bhagavad Gītā Chapter {chapter}, Sanskrit verses from a documented digital edition.', body, f'/gita/{chapter}/')



def reader_controls(show_lines: bool = True) -> str:
    return f'''<div class="reading-toolbar" aria-label="Reading preferences">
      <div class="reading-toolbar-label"><span aria-hidden="true">✦</span> Reading room</div>
      <div class="reading-toolbar-actions">
        <div class="font-tools" role="group" aria-label="Text size"><button type="button" data-font-step="-1" aria-label="Decrease text size">A−</button><button type="button" data-font-step="1" aria-label="Increase text size">A+</button></div>
        {"<button type=\"button\" class=\"reader-tool-button\" data-lines-toggle aria-pressed=\"false\">Original lines</button>" if show_lines else ""}
        <button type="button" class="reader-tool-button" data-width-toggle aria-pressed="false">Wider page</button>
        <button type="button" class="reader-tool-button" data-focus-toggle aria-pressed="false">Focus</button>
      </div>
    </div>'''


def reading_paragraphs(page: dict, lang: str = 'en', poetic: bool = False) -> str:
    """Render genuine paragraphs using source blank lines; preserve every codepoint.

    All original characters, including newlines and blank rows, remain in
    .source-line elements and are reconstructed by the independent checker.
    Visible paragraph breaks are based solely on blank source lines.
    """
    groups=[]
    current=[]
    for number, line in page['lines']:
        if line.strip():
            current.append((number, line))
        else:
            if current:
                groups.append(('paragraph',current));current=[]
            groups.append(('blank',[(number,line)]))
    if current:groups.append(('paragraph',current))
    result=[]
    for kind,lines in groups:
        nodes=''.join(f'<span class="source-line" data-source-line id="l{n}">{e(line)}</span>' for n,line in lines)
        if kind=='blank':
            result.append(f'<span class="source-gap" aria-hidden="true">{nodes}</span>')
        else:
            result.append(f'<p class="reading-paragraph">{nodes}</p>')
    return ''.join(result)


def page_jump(prefix: str, total: int) -> str:
    """Keyboard-accessible jump; no dependence on a server-side route handler."""
    return (f'<form class="page-jump" data-page-jump-form data-page-base="{e(prefix)}" data-page-total="{total}">'
            f'<label>Go to reading page <input type="number" name="page" min="1" max="{total}" required inputmode="numeric" autocomplete="off" placeholder="1–{total}"></label>'
            '<button type="submit">Go →</button></form>')


def book_parts(book: dict, parts: list[dict], prefix: str) -> str:
    def entries_for(start: int, end: int) -> str:
        return ''.join(f'<li><a href="{prefix}{i}/"><span class="part-number">{i:02d}</span><span>Reading page {i}</span><small>Source lines {parts[i-1]["first_line"]}–{parts[i-1]["last_line"]}</small><span class="part-arrow" aria-hidden="true">↗</span></a></li>' for i in range(start, end+1))
    if len(parts) <= 24:
        return f'<ol class="part-list">{entries_for(1,len(parts))}</ol>'
    # Hundreds of pages must not produce a huge *landing-page* scroll.
    grouped=''.join(f'<details class="part-range"><summary>Reading pages {first}–{min(first+19,len(parts))} <span aria-hidden="true">⌄</span></summary><ol class="part-list">{entries_for(first,min(first+19,len(parts)))}</ol></details>' for first in range(1,len(parts)+1,20))
    return page_jump(prefix,len(parts)) + '<div class="page-ranges">' + grouped + '</div>'


def upanishad_sections(text: str, pages: list[dict]) -> dict[str, str]:
    """Find real Gutenberg volume headings, not imagined verse alignment.

    Only exact heading lines immediately followed by Peace Chant qualify.
    Extract nothing and alter no source bytes.
    """
    labels={'isa':'Isa-Upanishad','katha':'Katha-Upanishad','kena':'Kena-Upanishad'}
    lines=text.splitlines(keepends=True)
    results={}
    for key,label in labels.items():
        for idx,line in enumerate(lines):
            if line.strip().casefold()!=label.casefold():
                continue
            lookahead=[x.strip().casefold() for x in lines[idx+1:idx+16] if x.strip()]
            if not lookahead or lookahead[0]!='peace chant':
                continue
            number=idx+1
            matches=[i for i,p in enumerate(pages,1) if p['first_line']<=number<=p['last_line']]
            if len(matches)!=1:raise ValueError(f'English {label}: boundary not present in published segments')
            if key in results:raise ValueError(f'English {label}: ambiguous opening')
            results[key]=f'/texts/upanishads-paramananda/{matches[0]}/#l{number}'
    return results


def related_edition(book: dict, companions: dict[str,str]) -> str:
    slug=book['slug']
    if slug in ('katha-upanishad','isha-upanishad-sankara'):
        key='katha' if slug=='katha-upanishad' else 'isa'
        label='Kaṭha' if key=='katha' else 'Īśā'
        link=companions.get(key,'/texts/upanishads-paramananda/')
        return f'<aside class="reading-note companion-note"><strong>Read a historical English rendering</strong><p>Swami Paramananda’s 1919 English translation and explanation of the {label} Upaniṣad is hosted separately. It reflects the translator’s interpretive tradition, not a certified line-by-line match to this digital Sanskrit witness.</p><a class="quiet-link" href="{e(link)}">Read Paramananda’s {label} section →</a></aside>'
    related={
      'patanjali-yoga-sutra':('/texts/yoga-sutras-johnston/','Charles Johnston’s historical English interpretation'),
      'brahma-sutra':('/texts/vedanta-sutras-sankara/','George Thibaut’s English rendering of the Śaṅkara commentary (Volume I)'),
      'gita-four-commentaries':('/gita/','Bhagavad Gītā Sanskrit mūla in another digital edition'),
      'ramanuja-gita-bhashya':('/gita/','Bhagavad Gītā Sanskrit mūla in another digital edition'),
    }
    if slug not in related:return ''
    link,label=related[slug]
    return f'<aside class="reading-note companion-note"><strong>Related edition, not automatic verse alignment</strong><p>{e(label)} is available as a separate source. Its text, editorial choices and doctrinal viewpoint are not silently merged with this edition.</p><a class="quiet-link" href="{e(link)}">Open related edition →</a></aside>'


def render_english_index(book: dict, pages: list[dict], sections: dict[str,str] | None = None) -> str:
    prefix=f"/texts/{book['slug']}/"
    body=f'''<div class="wrap page-container book-landing"><a class="breadcrumb" href="/">← Library</a>
    <div class="intro-block"><p class="eyebrow">Historical English · {e(book['kind'])}</p>
    <h1>{e(book['title'])}</h1><p class="english-byline">{e(book['translator'])}</p><p>{e(book['description'])}</p>
    <div class="hero-ctas"><a class="button button-primary" href="{prefix}1/">Start reading →</a><a class="button button-outline" href="/downloads/{e(book['slug'])}.txt" download>Original source TXT ↓</a></div>
    <p class="continue-note" data-continue-book="{e(book['slug'])}" hidden></p></div>
    {('<aside class="reading-note companion-note"><strong>Jump to a translated Upaniṣad</strong><p>These are Paramananda’s own English passages and commentary, preserved in their original order. They are not silently synchronised with another Sanskrit edition.</p>' + ''.join(f'<a class="companion-link" href="{e(sections[key])}">{e(name)} translation →</a>' for key,name in (("isa","Īśā"),("katha","Kaṭha"),("kena","Kena"))) + '</aside>') if book['slug']=="upanishads-paramananda" and sections and all(sections.get(k) for k in ("isa","katha","kena")) else ''}
    <div class="reading-note"><strong>What you're reading</strong><p>The complete, attributed Project Gutenberg edition including its notices, displayed as comfortable HTML reading pages. These pages are <em>not</em> source chapters. The original download remains unchanged.</p></div>
    <section class="parts-section" aria-label="Reading pages"><h2 class="section-title">Reading pages <span class="subtle-count">{len(pages)}</span></h2>{book_parts(book,pages,prefix)}</section></div>'''
    return document(book['title'],f"Read the historical English text {book['title']} by {book['translator']} in a comfortable web reader.",body,prefix)


def render_english_part(book: dict, page: dict, index: int, total: int) -> str:
    prefix=f"/texts/{book['slug']}/"
    prev=f'<a data-reader-prev href="{prefix}{index-1}/">← Previous page</a>' if index>1 else '<span></span>'
    next_=f'<a data-reader-next href="{prefix}{index+1}/">Next page →</a>' if index<total else f'<a href="{prefix}">All pages ↑</a>'
    poetic=(book['slug']=='gita-arnold')
    body=f'''<div class="wrap literary-reader reading-with-sidebar" data-reading-page data-book-id="{e(book['slug'])}" data-part="{index}" data-part-total="{total}" data-default-lines="{'true' if poetic else 'false'}">
    {page_sidebar(prefix,index,total,book['title'])}
    <div class="reading-content-column"><a class="breadcrumb" href="{prefix}">← {e(book['title'])} · All pages</a>
    <div class="book-page-heading"><p class="eyebrow">Historical English · {e(book['kind'])}</p><h1>{e(book['title'])}</h1><p>{e(book['translator'])} · Reading page {index} / {total}</p></div>
    {reader_controls()}
    {page_jump(prefix,total)}
    <div class="reader-paper" data-reader-text><div class="reader-prose {'poetic-lines' if poetic else ''}" lang="en" data-source-lines>{reading_paragraphs(page)}</div></div>
    <nav class="chapter-nav reading-pager" aria-label="Page navigation">{prev}{next_}</nav>
    <div class="reader-end"><a href="{prefix}">All pages</a> · <a href="/sources/">Edition notes</a> · <a href="/downloads/{e(book['slug'])}.txt" download>Download exact original</a></div></div></div>'''
    return document(f"{book['title']} · Reading page {index}", f"Read page {index} of {book['title']}, historical English edition.",body,f'{prefix}{index}/')

def render_search() -> str:
    body='''<section class="wrap search-page"><a class="breadcrumb" href="/">← Library</a><div class="intro-block compact-intro"><p class="eyebrow">Search the actual words</p><h1>Find a <em>passage.</em></h1><p>Search the Sanskrit Gītā in Devanagari and other attributed Sanskrit texts in IAST. Enter a phrase, title, or Gītā reference such as <strong>2.47</strong>.</p></div>
<div class="search-box-large"><label for="verse-search">Search Sanskrit texts</label><input type="search" id="verse-search" placeholder="Try kṛṣṇa, bhakti, yoga or 2.47" autocomplete="off" data-verse-search><p class="hint">Source spellings and original punctuation are preserved. IAST text is not an English translation. Index loads only on this page.</p></div>
<p class="result-count" role="status" aria-live="polite" data-verse-status>Enter at least two characters to begin.</p><div data-verse-results class="search-results"></div></section>'''
    return document('Search Sanskrit texts', 'Search attributed Sanskrit source lines and Bhagavad Gītā verses.', body, '/search/')



def render_gretil_index(book: dict, pages: list[dict], companions: dict[str,str] | None = None) -> str:
    prefix=f"/works/{book['slug']}/"
    body=f'''<div class="wrap page-container book-landing"><a class="breadcrumb" href="/">← Library</a>
<div class="intro-block"><p class="eyebrow">{e(book['category'])} · Sanskrit / IAST</p><h1>{e(book['title'])}</h1>
<p>{e(book['source_note'])}</p><div class="source-strip"><span>{len(pages)} reading pages</span><span>{pages[-1]['last_line']:,} source lines</span><a href="/sources/#{e(book['slug'])}">Source &amp; rights ↗</a></div>
<div class="hero-ctas"><a class="button button-primary" href="{prefix}1/">Start reading →</a><a class="button button-outline" href="/downloads/{e(book['slug'])}.txt" download>Exact original TXT ↓</a></div>
<p class="continue-note" data-continue-book="{e(book['slug'])}" hidden></p></div>
<div class="reading-note"><strong>Faithful presentation.</strong><p>Readable IAST Sanskrit, with original line order and punctuation preserved. Page divisions below are technical reading segments, not traditional chapters or skandhas. This is one attributed digital witness, not a modern translation or independent collation.</p></div>{related_edition(book,companions or {})}
<section class="parts-section" aria-label="Reading pages"><h2 class="section-title">Reading pages <span class="subtle-count">{len(pages)}</span></h2>{book_parts(book,pages,prefix)}</section></div>'''
    return document(book['title'], f"Source-attributed IAST Sanskrit e-text: {book['title']}", body, prefix)


def render_gretil_part(book: dict, page: dict, index: int, total: int) -> str:
    prefix=f"/works/{book['slug']}/"
    prev=f'<a data-reader-prev href="{prefix}{index-1}/">← Previous page</a>' if index>1 else '<span></span>'
    next_=f'<a data-reader-next href="{prefix}{index+1}/">Next page →</a>' if index<total else f'<a href="{prefix}">All pages ↑</a>'
    body=f'''<div class="wrap literary-reader reading-with-sidebar" data-reading-page data-book-id="{e(book['slug'])}" data-part="{index}" data-part-total="{total}" data-default-lines="true">
    {page_sidebar(prefix,index,total,book['title'])}
    <div class="reading-content-column"><a class="breadcrumb" href="{prefix}">← {e(book['title'])} · All pages</a>
    <div class="book-page-heading"><p class="eyebrow">{e(book['category'])} · Sanskrit in IAST</p><h1>{e(book['title'])}</h1><p>Reading page {index} / {total} · Source lines {page['first_line']}–{page['last_line']}</p></div>
    {reader_controls()}
    {page_jump(prefix,total)}
    <div class="reader-paper" data-reader-text><div class="reader-prose sanskrit-lines" lang="sa-Latn" data-source-lines>{reading_paragraphs(page,lang='sa-Latn',poetic=True)}</div></div>
    <nav class="chapter-nav reading-pager" aria-label="Reading navigation">{prev}{next_}</nav>
    <p class="reader-end">Navigation pages are not traditional chapters. <a href="/sources/#{e(book['slug'])}">Edition and licence</a> · <a href="/downloads/{e(book['slug'])}.txt" download>Exact source TXT</a></p></div></div>'''
    return document(f'{book["title"]}, page {index}',f'IAST Sanskrit reading page {index} of {book["title"]}.',body,f'{prefix}{index}/')

def render_sources(manifest: dict, receipts: dict) -> str:
    g=manifest['sanskrit'][0]
    rows=[]
    for b in manifest['english']:
        rows.append(f'''<tr><td><a href="/texts/{e(b['slug'])}/">{e(b['title'])}</a></td><td>{e(b['translator'])}</td><td>English, {e(b['kind'])}</td><td><a href="https://www.gutenberg.org/ebooks/{b['id']}">PG #{b['id']}</a></td></tr>''')
    gretil_rows=''.join(f'''<article class="source-detail" id="{e(b['slug'])}"><h2>{e(b['title'])}</h2><p><strong>Category:</strong> {e(b['category'])}. <strong>Source witness:</strong> {e(b['source_note'])}</p><p><strong>Form:</strong> IAST Sanskrit, preserving line order and source markers. Not a paired translation, not independently collated against print. <a href="/works/{e(b['slug'])}/">Read the edition</a> · <a href="{e(b['source'])}">Pinned original text ↗</a></p><p><strong>Text licence:</strong> <a href="{e(b['license_url'])}">{e(b['license'])}</a>. Credits: GRETIL / SUB Göttingen; INDOLOGY GRETIL-mirror; derived plain-text extraction by tokushige-koyasan. No commercial use; adapted presentation is shared under the same licence. Source details remain with the downloaded text.</p></article>''' for b in manifest['gretil'])
    receipt_rows=''.join(f'<li><code>{e(r["file"])}</code> · SHA-256 <code>{e(r["sha256"])}</code></li>' for r in receipts['receipts'])
    body=f'''<div class="wrap sources-page"><a class="breadcrumb" href="/">← Library</a><div class="intro-block compact-intro"><p class="eyebrow">Accountability</p><h1>Sources &amp; <em>editions.</em></h1><p>Every hosted book identifies where its text came from, which edition is represented, and what we do not claim. Sources are not interchangeable with translations or commentaries.</p></div>
<section class="source-detail" id="gita"><h2>Bhagavad Gītā · Sanskrit</h2><p><strong>Edition:</strong> {e(g['edition'])}. <strong>Declared scope:</strong> {e(g['scope'])}.</p><p><a href="{e(g['source'])}">Pinned upstream Git revision ↗</a> · <a href="{e(g['license_url'])}">Upstream Unlicense ↗</a>. Attribution is supplied even though the source release dedicates its contents to the public domain.</p><p>{e(g['disclaimer'])}</p><p>The text's original Sanskrit is ancient. The modern digital transcription is separately attributed. No modern translations, AI explanations, or commentaries are reproduced under this licence claim.</p></section>
<section class="source-detail"><h2>Historical English editions</h2><p>These are specific complete Project Gutenberg e-books, not whole scripture corpora. Source text is preserved in full, including original Gutenberg notices. The website is independent of Project Gutenberg; its trademark is used only to identify provenance.</p><div class="table-scroll"><table><thead><tr><th>Hosted work</th><th>Translator / editor</th><th>Scope</th><th>Source</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>
<section class="source-detail"><h2>New Sanskrit digital editions</h2><p>These are GRETIL-derived TEI body extractions (not page scans) preserved in IAST, each identified by a pinned upstream Git blob, retaining editorial markers and source spelling. Extracted source notes are not a substitute for independent collation. Each digital text is licensed CC BY-NC-SA 4.0; reuse requires attribution, non-commerciality and share-alike. The shared website interface has separate rights from these texts.</p></section>{gretil_rows}
<section class="source-detail"><h2>What is not published yet</h2><p>Modern translations without redistribution permission; uncollated Sanskrit witnesses; uncleared SARIT-specific editorial reconstructions; and scanned PDFs. These are not shown as hosted books.</p></section>
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
        english[book['slug']] = {'text': raw.decode('utf-8-sig'), 'raw': raw}
    gretil = {}
    for item in manifest['gretil']:
        raw = (source_dir / f"gretil-{item['slug']}.txt").read_bytes()
        gretil[item['slug']] = {'raw':raw, 'text':validate_gretil(raw, item), 'pages':None}
        gretil[item['slug']]['pages'] = segment_gretil(gretil[item['slug']]['text'])
    receipts = {'schema': 2, 'receipts': [
        {'file': name, 'sha256': hashlib.sha256((source_dir / name).read_bytes()).hexdigest(), 'bytes': (source_dir / name).stat().st_size}
        for name in ['gita-verses.json', 'gita-chapters.json'] + [f"pg{b['id']}.txt" for b in manifest['english']] + [f"gretil-{b['slug']}.txt" for b in manifest['gretil']]
    ]}
    if out.exists() and any(out.iterdir()):
        raise ValueError(f'Output must be absent or empty (safe build): {out}')
    out.mkdir(parents=True, exist_ok=True)
    assets = ROOT / 'src' / 'assets'
    (out / 'assets').mkdir(exist_ok=True)
    for file in ('style.css', 'app.js', 'favicon.svg'):
        shutil.copyfile(assets / file, out / 'assets' / file)
    write(out, 'index.html', render_home(manifest, chapters, 1 + len(manifest['english']) + len(manifest['gretil'])))
    write(out, 'gita/index.html', render_gita_index(chapters, verse_records, g))
    grouped = defaultdict(list)
    for v in verse_records:
        grouped[v['chapter']].append(v)
    for n in range(1, 19):
        write(out, f'gita/{n}/index.html', render_gita_chapter(n, grouped[n], chapters))
    english_records=[]
    english_pages={book['slug']:segment_gretil(english[book['slug']]['text']) for book in manifest['english']}
    pg_sections=upanishad_sections(english['upanishads-paramananda']['text'],english_pages['upanishads-paramananda'])
    if set(pg_sections) != {'isa','katha','kena'}:
        raise ValueError('Paramananda source no longer exposes three verified Upaniṣad openings; refusing to mislink them')
    for book in manifest['english']:
        pages=english_pages[book['slug']]
        prefix=f"texts/{book['slug']}"
        write(out, f"{prefix}/index.html", render_english_index(book, pages, pg_sections))
        for i,page in enumerate(pages,1):
            write(out, f"{prefix}/{i}/index.html", render_english_part(book,page,i,len(pages)))
        write(out, f"downloads/{book['slug']}.txt", english[book['slug']]['raw'])
        english_records.append({'slug':book['slug'],'pages':len(pages),'lines':pages[-1]['last_line'],
            'sha256':hashlib.sha256(english[book['slug']]['raw']).hexdigest(),
            'segments':[{'number':i,'first_line':p['first_line'],'last_line':p['last_line']} for i,p in enumerate(pages,1)]})
    write(out,'english-build.json',json.dumps(english_records,ensure_ascii=False,indent=2)+'\n')
    # Every original e-text is downloadable without any transformation.
    gretil_records=[]
    companion_sections=pg_sections
    global_index=[]
    for row in verse_records:
        global_index.append({'book':'Bhagavad Gītā','kind':'gita','ref':f"{row['chapter']}.{row['verse']}",'text':row['text'],'url':f"/gita/{row['chapter']}/#v{row['verse']}"})
    for item in manifest['gretil']:
        data=gretil[item['slug']]
        pages=data['pages']
        write(out, f"downloads/{item['slug']}.txt", data['raw'])
        write(out, f"works/{item['slug']}/index.html",render_gretil_index(item,pages,companion_sections))
        for i,page in enumerate(pages,1):
            write(out, f"works/{item['slug']}/{i}/index.html",render_gretil_part(item,page,i,len(pages)))
            for n,line in page['lines']:
                if line.strip():
                    global_index.append({'book':item['title'],'kind':'gretil','ref':f'Line {n}','text':line.rstrip('\r\n'),'url':f"/works/{item['slug']}/{i}/#l{n}"})
        gretil_records.append({'slug':item['slug'],'pages':len(pages),'lines':pages[-1]['last_line'],
             'sha256':hashlib.sha256(data['raw']).hexdigest(),
             'segments':[{'number':i,'first_line':p['first_line'],'last_line':p['last_line']} for i,p in enumerate(pages,1)]})
    write(out,'gretil-build.json',json.dumps(gretil_records,ensure_ascii=False,indent=2)+'\n')
    write(out,'search/library.json',json.dumps(global_index,ensure_ascii=False,separators=(',',':'))+'\n')
    write(out, 'search/index.html', render_search())
    write(out, 'sources/index.html', render_sources(manifest, receipts))
    write(out, 'search/verses.json', json.dumps(verse_records, ensure_ascii=False, separators=(',', ':')) + '\n')
    write(out, 'source-receipts.json', json.dumps(receipts, ensure_ascii=False, indent=2) + '\n')
    paths = ['/','/gita/','/search/','/sources/'] + [f'/gita/{n}/' for n in range(1,19)] + [f"/texts/{b['slug']}/" for b in manifest['english']] + [f"/texts/{b['slug']}/{n}/" for b in manifest['english'] for n in range(1,len(english_pages[b['slug']])+1)] + [f"/works/{b['slug']}/" for b in manifest['gretil']] + [f"/works/{b['slug']}/{n}/" for b in manifest['gretil'] for n in range(1,len(gretil[b['slug']]['pages'])+1)]
    write(out, 'sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + ''.join(f'  <url><loc>{SITE_ORIGIN}{p}</loc></url>\n' for p in paths) + '</urlset>\n')
    write(out, 'robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE_ORIGIN}/sitemap.xml\n')
    write(out, '.nojekyll', '')
    return {'books': 9 + len(manifest['gretil']), 'sanskrit_verses': len(verse_records), 'gretil_books':len(manifest['gretil']), 'gretil_lines':sum(x['lines'] for x in gretil_records),'english_reading_pages':sum(len(v) for v in english_pages.values()), 'chapters': 18, 'html_pages': len(paths), 'size_bytes': sum(p.stat().st_size for p in out.rglob('*') if p.is_file())}


def main() -> None:
    arg = argparse.ArgumentParser()
    arg.add_argument('--source-dir', type=Path, default=ROOT / '_sources')
    arg.add_argument('--out', type=Path, default=ROOT / '_site')
    options=arg.parse_args()
    print('BUILD_OK', json.dumps(build(options.source_dir, options.out), ensure_ascii=False))


if __name__ == '__main__':
    main()
