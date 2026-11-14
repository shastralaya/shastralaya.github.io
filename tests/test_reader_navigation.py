
"""Semantics and boundaries for left-side page lists and keyboard navigation."""
from __future__ import annotations
import sys
import unittest
from pathlib import Path
from html.parser import HTMLParser

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import build


class SidebarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = []
        self.selects = 0
    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == 'a':
            self.links.append(d.get('href', ''))
            if d.get('aria-current') == 'page':
                self.current.append(d.get('href'))
        elif tag == 'select' and 'data-reading-range' in d:
            self.selects += 1


class ReadingNavigationTests(unittest.TestCase):
    def test_short_books_contain_accessible_full_page_list(self):
        page = build.page_sidebar('/texts/gita-arnold/', 3, 8, 'The Song Celestial')
        parser = SidebarParser()
        parser.feed(page)
        self.assertIn('class="reading-sidebar-desktop"', page)
        self.assertIn('<details class="reading-sidebar-mobile">', page)
        self.assertEqual(parser.selects, 0)
        self.assertEqual(parser.current, ['/texts/gita-arnold/3/'] * 2)
        self.assertEqual(len(parser.links), 18)  # Eight pages twice + two book links.
        self.assertNotIn('/texts/gita-arnold/9/', page)

    def test_long_book_lists_only_current_twenty_with_group_switch(self):
        page = build.page_sidebar('/works/bhagavata-purana/', 47, 387, 'Bhāgavata Purāṇa')
        parser = SidebarParser()
        parser.feed(page)
        self.assertEqual(parser.selects, 2)
        self.assertEqual(parser.current, ['/works/bhagavata-purana/47/'] * 2)
        self.assertEqual(len(parser.links), 42)  # Twenty page links twice, plus book links.
        self.assertIn('value="41" selected', page)
        self.assertIn('Page 41', page)
        self.assertIn('Page 60', page)
        self.assertNotIn('/works/bhagavata-purana/61/', page)
        self.assertNotIn('/works/bhagavata-purana/21/', page)

    def test_page_bounds_and_paths_refuse_invalid_render(self):
        for args in [
            ('/texts/book/', 0, 5, 'Book'),
            ('/works/book/', 6, 5, 'Book'),
            ('//evil.example/', 1, 5, 'Book'),
            ('/admin/', 1, 5, 'Book'),
        ]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                build.page_sidebar(*args)

    def test_reader_pages_and_chapters_expose_real_edge_links(self):
        book = {'slug': 'example', 'title': 'Example', 'kind': 'English',
                'translator': 'Scholar', 'category': 'Sanskrit'}
        page = {'lines': [(1, 'ātmā śrīḥ\n'), (2, '\n')], 'first_line': 1, 'last_line': 2}
        for render, prefix in [
            (build.render_english_part, '/texts/example/'),
            (build.render_gretil_part, '/works/example/'),
        ]:
            with self.subTest(prefix=prefix):
                first = render(book, page, 1, 4)
                middle = render(book, page, 2, 4)
                last = render(book, page, 4, 4)
                self.assertIn('data-reading-sidebar', middle)
                self.assertIn('reading-content-column', middle)
                self.assertIn(f'data-reader-prev href="{prefix}1/"', middle)
                self.assertIn(f'data-reader-next href="{prefix}3/"', middle)
                self.assertNotIn('data-reader-prev', first)
                self.assertNotIn('data-reader-next', last)
        metadata = {n: {'sanskrit': 'अध्यायः', 'english': f'Chapter {n}'} for n in range(1, 19)}
        first = build.render_gita_chapter(1, [{'verse': 1, 'text': 'ॐ शान्तिः'}], metadata)
        last = build.render_gita_chapter(18, [{'verse': 1, 'text': 'ॐ शान्तिः'}], metadata)
        self.assertIn('data-reading-sidebar', first)
        self.assertIn('aria-current="page"', first)
        self.assertIn('data-reader-next href="/gita/2/"', first)
        self.assertNotIn('data-reader-prev', first)
        self.assertNotIn('data-reader-next', last)

    def test_keyboard_guard_and_responsive_disclosure_present(self):
        js = (ROOT / 'src/assets/app.js').read_text(encoding='utf-8')
        css = (ROOT / 'src/assets/style.css').read_text(encoding='utf-8')
        self.assertIn("event.key!=='ArrowLeft'", js)
        self.assertIn("event.key!=='ArrowRight'", js)
        self.assertIn('event.repeat', js)
        self.assertIn('event.ctrlKey', js)
        self.assertIn('event.altKey', js)
        self.assertIn('[contenteditable]', js)
        self.assertIn("window.getSelection()?.toString()", js)
        self.assertIn("link.getAttribute('href')!==expected", js)
        self.assertIn('.reading-sidebar-mobile{display:none}', css)
        self.assertIn('@media(max-width:899px)', css)
        self.assertIn('body.focus-reading .reading-page-sidebar{display:none', css)


if __name__ == '__main__':
    unittest.main()
