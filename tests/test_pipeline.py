"""Offline tests. All Sanskrit in fixtures is marked synthetic and never shipped."""
from __future__ import annotations
import ast
import hashlib
import json
import copy
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
import gretil
import live_smoke


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads((ROOT/'sources.json').read_text(encoding='utf-8'))

    def test_data_manifest_sanity(self):
        self.assertEqual(self.manifest['sanskrit'][0]['expected_verses'],701)
        self.assertEqual(sum(self.manifest['sanskrit'][0]['verse_counts']),701)
        self.assertEqual(len(self.manifest['english']),8)
        self.assertEqual(len(self.manifest['gretil']),12)
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

    def test_sanskrit_source_hash_and_line_boundaries(self):
        item=copy.deepcopy(self.manifest['gretil'][0])
        raw=('śrī kṛṣṇa nāmaḥ bhaktiḥ || 1 ||\n\n'*10).encode('utf-8')
        item['expected_bytes']=len(raw)
        item['git_blob_sha1']=gretil.git_blob_sha1(raw)
        self.assertEqual(gretil.validate_text(raw,item),raw.decode('utf-8'))
        pages=gretil.segment(raw.decode('utf-8'))
        self.assertEqual(''.join(line for p in pages for _,line in p['lines']),raw.decode('utf-8'))
        with self.assertRaisesRegex(ValueError,'mismatch'):
            gretil.validate_text(raw.replace(b'bhakti',b'shakti',1),item)

    def test_pg_truncation_and_wrong_identity_blocked(self):
        b=self.manifest['english'][0]
        for invalid in (b'',b'Project Gutenberg eBook #2388 The Song Celestial',b'Project Gutenberg eBook #2389 The Song Celestial' + b' '*20000):
            with self.assertRaises(ValueError):fetch.validate_pg(invalid,b)

    def test_escaping_of_adversarial_text(self):
        fake={'id':999,'slug':'fake','title':'<script>alert(1)</script>','translator':'Test','description':'Test'}
        page=build.reading_paragraphs({'lines': [(1, '<img src=x onerror=alert(1)>\n')]})
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

    def test_live_site_rejects_readme_and_missing_reader(self):
        with self.assertRaisesRegex(ValueError,'wrong or incomplete'):
            live_smoke.validate_response('/', '<h1>shastralaya</h1><p>README documentation</p>')
        for path,needs in live_smoke.EXPECTED.items():
            live_smoke.validate_response(path, ' '.join(needs))

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

    def test_windows_compatibility_gates_production_build(self):
        workflow=(ROOT/'.github/workflows/pages.yml').read_text(encoding='utf-8')
        self.assertIn('windows-compat:',workflow)
        self.assertIn('runs-on: windows-latest',workflow)
        self.assertIn("python-version: '3.14'",workflow)
        self.assertIn('needs: windows-compat',workflow)
        deploy_section=workflow.split('  deploy:', 1)[1]
        self.assertIn('uses: actions/checkout@v4', deploy_section)
        self.assertLess(deploy_section.index('uses: actions/checkout@v4'), deploy_section.index('run: python scripts/live_smoke.py'))
        self.assertIn('uses: actions/setup-python@v5', deploy_section)

    def test_restore_generated_reader_without_platform_newline_conversion(self):
        """Tamper+restore preserves original LF, CRLF, UTF-8 and blank lines."""
        original = "śrī kṛṣṇa\n\nśāntiḥ\r\n".encode('utf-8')
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'reader.html'
            path.write_bytes(original)
            corrupted=path.read_bytes().replace('kṛṣṇa'.encode('utf-8'), b'changed')
            self.assertNotEqual(corrupted, original)
            try:
                path.write_bytes(corrupted)
                self.assertNotEqual(path.read_bytes(), original)
            finally:
                path.write_bytes(original)
            self.assertEqual(path.read_bytes(), original)
            # A Windows newline translation would damage the restored bytes.
            self.assertNotEqual(original.replace(b'\n', b'\r\n'), original)

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
                raw=text.encode('utf-8')
                if b['id']==2388:
                    raw=b'\xef\xbb\xbf'+text.replace('\n','\r\n').encode('utf-8')
                (inputs/f"pg{b['id']}.txt").write_bytes(raw)
            fake_manifest=copy.deepcopy(self.manifest)
            for book in fake_manifest['gretil']:
                synthetic='śrī kṛṣṇa nāmaḥ prītiḥ bhaktiḥ\n\n'*14
                raw=synthetic.encode('utf-8')
                book['expected_bytes']=len(raw)
                book['git_blob_sha1']=gretil.git_blob_sha1(raw)
                (inputs/f"gretil-{book['slug']}.txt").write_bytes(raw)
            with patch.object(build,'validate_gita',return_value=None):
                report=build.build(inputs,out,fake_manifest)
            self.assertEqual(report['books'],21)
            self.assertEqual(report['chapters'],18)
            self.assertEqual(check.check(out)['sanskrit_verses'],701)
            for path in live_smoke.EXPECTED:
                file=out/path.lstrip('/')/'index.html'
                live_smoke.validate_response(path,file.read_text(encoding='utf-8'))
            self.assertEqual((inputs/'pg2388.txt').read_bytes(),(out/'downloads/gita-arnold.txt').read_bytes())
            self.assertIn('reader-paper',(out/'texts/gita-arnold/1/index.html').read_text(encoding='utf-8'))
            self.assertIn('reading-paragraph',(out/'works/mukundamala/1/index.html').read_text(encoding='utf-8'))
            self.assertEqual(len(list((out/'works').glob('*/index.html'))),12)
            self.assertIn('परीक्षण', (out/'gita/18/index.html').read_text(encoding='utf-8'))
            self.assertNotIn('resume', (out/'index.html').read_text(encoding='utf-8').lower())
            self.assertFalse(list(out.rglob('*.pdf')))
            # The builder emits the exact source newline codepoints. Never
            # restore a generated HTML page with write_text(): Windows text
            # mode changes LF to CRLF and makes the *test* corrupt the page.
            target=out/'works/mukundamala/1/index.html'
            original=target.read_bytes()
            tampered=original.replace('śrī kṛṣṇa'.encode('utf-8'), 'śrī rāma'.encode('utf-8'), 1)
            self.assertNotEqual(tampered, original)
            try:
                target.write_bytes(tampered)
                with self.assertRaisesRegex(ValueError,'differ from the complete source'):
                    check.check(out)
            finally:
                target.write_bytes(original)
            self.assertEqual(target.read_bytes(), original)
            check.check(out)
            with self.assertRaisesRegex(ValueError,'Output must be'):
                with patch.object(build,'validate_gita',return_value=None):build.build(inputs,out,fake_manifest)

if __name__=='__main__':unittest.main()
