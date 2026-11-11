"""Offline tests. All Sanskrit in fixtures is marked synthetic and never shipped."""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
import build
import check
import fetch


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))

    def test_data_manifest_sanity(self):
        self.assertEqual(self.manifest['sanskrit'][0]['expected_verses'],701)
        self.assertEqual(sum(self.manifest['sanskrit'][0]['verse_counts']),701)
        self.assertEqual(len(self.manifest['english']),8)
        self.assertEqual(len({b['slug'] for b in self.manifest['english']}),8)
        self.assertTrue(all(b['expected_title'] for b in self.manifest['english']))

    def test_git_hash_uses_real_blob_framing(self):
        raw=b'hello world\n'
        expected=hashlib.sha1(b'blob 12\0'+raw).hexdigest()
        self.assertEqual(fetch.git_blob_sha1(raw),expected)
        with self.assertRaisesRegex(ValueError,'mismatch'):
            fetch.validate_gita(raw*5,'0'*40,'fixture')

    def test_gita_rejects_duplicate_and_missing_verse(self):
        g=self.manifest['sanskrit'][0]
        rows=[{'chapter_number':n,'verse_number':i,'text':f'परीक्षण पाठ {n}.{i} वाक्यम् समाप्तम् ।'}
              for n,count in enumerate(g['verse_counts'],1) for i in range(1,count+1)]
        self.assertEqual(len(build.read_verse_records(json.dumps(rows).encode(),g)),701)
        rows[1]['verse_number']=1
        with self.assertRaisesRegex(ValueError,'duplicate'):
            build.read_verse_records(json.dumps(rows).encode(),g)
        rows[1]['verse_number']=2
        rows.pop()
        with self.assertRaisesRegex(ValueError,'unexpected total'):
            build.read_verse_records(json.dumps(rows).encode(),g)

    def test_pg_truncation_and_wrong_identity_blocked(self):
        b=self.manifest['english'][0]
        for invalid in (b'',b'Project Gutenberg eBook #2388 The Song Celestial',b'Project Gutenberg eBook #2389 The Song Celestial' + b' '*20000):
            with self.assertRaises(ValueError):fetch.validate_pg(invalid,b)

    def test_escaping_of_adversarial_text(self):
        fake={'id':999,'slug':'fake','title':'<script>alert(1)</script>','translator':'Test','description':'Test'}
        page=build.render_english(fake,'<img src=x onerror=alert(1)>')
        self.assertNotIn('<img src=x',page)
        self.assertNotIn('<script>alert',page)
        self.assertIn('&lt;img src=x',page)

    def test_theme_early_bootstrap_all_pages_and_reader_a11y(self):
        page=build.document('Theme test','Theme check','<p>test</p>')
        self.assertIn('prefers-color-scheme: dark',page)
        self.assertIn("localStorage.getItem('shastralaya-theme')",page)
        self.assertLess(page.index("localStorage.getItem('shastralaya-theme')"),page.index('/assets/style.css'))
        self.assertIn('data-theme-toggle',page)
        self.assertIn('aria-pressed="false"',page)
        js=(ROOT/'src/assets/app.js').read_text(encoding='utf-8')
        css=(ROOT/'src/assets/style.css').read_text(encoding='utf-8')
        self.assertIn('systemTheme?.addEventListener',js)
        self.assertIn('applyTheme(',js)
        self.assertIn(':root[data-theme=dark]',css)
        self.assertIn('color-scheme:dark;',css)

    def test_no_implicit_platform_text_encoding(self):
        """Portable source/test file IO must never inherit Windows cp1252."""
        targets = list((ROOT / 'scripts').glob('*.py')) + list((ROOT / 'tests').glob('*.py'))
        for path in targets:
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                fn = node.func
                if not isinstance(fn, ast.Attribute) or fn.attr not in ('read_text', 'write_text'):
                    continue
                has_explicit_encoding = any(keyword.arg == 'encoding' and keyword.value is not None for keyword in node.keywords)
                self.assertTrue(has_explicit_encoding, f'{path.name}:{node.lineno}: {fn.attr}() must declare encoding')

    def test_full_offline_build_has_no_portfolio_and_all_verses(self):
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d);inputs=folder/'sources';inputs.mkdir();out=folder/'site'
            g=self.manifest['sanskrit'][0]
            verses=[{'chapter_number':n,'verse_number':i,'text':f'परीक्षण {n}.{i}: कृत्रिमं परीक्षणं श्लोकम्।'}
                    for n,count in enumerate(g['verse_counts'],1) for i in range(1,count+1)]
            chapters=[{'chapter_number':n,'name':f'परीक्षणाध्यायः {n}','name_translation':f'Test Chapter {n}','verses_count':cnt}
                      for n,cnt in enumerate(g['verse_counts'],1)]
            (inputs/'gita-verses.json').write_text(json.dumps(verses,ensure_ascii=False),encoding='utf-8')
            (inputs/'gita-chapters.json').write_text(json.dumps(chapters,ensure_ascii=False),encoding='utf-8')
            for b in self.manifest['english']:
                text='Project Gutenberg eBook #'+str(b['id'])+'\n'+b['expected_title']+'\n'+'test line\n'*1500+'\n*** END OF THE PROJECT GUTENBERG EBOOK ***\nFULL PROJECT GUTENBERG LICENSE\n'
                (inputs/f"pg{b['id']}.txt").write_text(text,encoding='utf-8')
            with patch.object(build,'validate_gita',return_value=None):
                report=build.build(inputs,out,self.manifest)
            self.assertEqual(report['books'],9)
            self.assertEqual(report['chapters'],18)
            self.assertEqual(check.check(out)['sanskrit_verses'],701)
            self.assertIn('परीक्षण', (out/'gita/18/index.html').read_text(encoding='utf-8'))
            self.assertNotIn('resume', (out/'index.html').read_text(encoding='utf-8').lower())
            self.assertFalse(list(out.rglob('*.pdf')))
            with self.assertRaisesRegex(ValueError,'Output must be'):
                with patch.object(build,'validate_gita',return_value=None):build.build(inputs,out,self.manifest)

if __name__=='__main__':unittest.main()
