#!/usr/bin/env python3
"""Obtain exact Gita Git blobs and validate eight Project Gutenberg sources.

No dependencies; no TLS verification bypass. Always revalidate bytes, even when
reusing local copies. Downloads to temporary files; never touch public output.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
USER_AGENT = 'Shastralaya/1.0 (public-domain historical text preservation; no bulk scraping)'
MAX_GITA = 2_000_000
MAX_PG = 18_000_000
MAX_GRETIL = 3_000_000
from gretil import validate_text as validate_gretil


def git_blob_sha1(content: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(content)).encode('ascii') + b'\0' + content).hexdigest()


def validate_pg(content: bytes, book: dict) -> None:
    if not (12_000 <= len(content) <= MAX_PG):
        raise ValueError(f"PG #{book['id']}: unexpected source size {len(content)}")
    text = content.decode('utf-8-sig')
    head = text[:9000].casefold()
    tail = text[-65000:].casefold()
    identifier = str(book['id'])
    if 'project gutenberg' not in head or not any(
        tag in head for tag in (f'ebook #{identifier}', f'ebook # {identifier}', f'ebook no. {identifier}')
    ):
        raise ValueError(f'PG #{identifier}: identity marker missing')
    if book['expected_title'].casefold() not in head:
        raise ValueError(f'PG #{identifier}: expected title missing')
    if 'end of the project gutenberg ebook' not in tail:
        raise ValueError(f'PG #{identifier}: closing marker missing')
    if 'full project gutenberg license' not in tail:
        raise ValueError(f'PG #{identifier}: complete licence missing')


def validate_gita(content: bytes, sha1: str, label: str) -> None:
    if not (50 <= len(content) <= MAX_GITA):
        raise ValueError(f'{label}: unexpected size {len(content)}')
    if git_blob_sha1(content) != sha1:
        raise ValueError(f'{label}: original Git blob SHA-1 mismatch')
    json.loads(content.decode('utf-8-sig'))


def download(url: str, max_bytes: int) -> bytes:
    if not url.startswith('https://'):
        raise ValueError('HTTPS is required')
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=65) as response:
        if response.status != 200:
            raise RuntimeError(f'{url}: HTTP {response.status}')
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(f'{url}: download exceeds limit')
    return payload


def obtain(path: Path, url: str, validator, max_bytes: int) -> tuple[bytes, bool]:
    if path.is_file():
        data = path.read_bytes()
        try:
            validator(data)
            return data, True
        except (ValueError, UnicodeError, json.JSONDecodeError):
            # Never reuse a wrong/corrupt file. Download it again and revalidate.
            pass
    data = download(url, max_bytes)
    validator(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix='verified-', dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(data)
            f.flush()
        finally:
            pass
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)
    return data, False


def fetch_all(dest: Path, manifest: dict) -> dict:
    receipts = []
    gita = manifest['sanskrit'][0]
    items = [
        ('gita-verses.json', gita['url'], lambda d: validate_gita(d, gita['git_blob_sha1'], 'Gita verses'), MAX_GITA),
        ('gita-chapters.json', gita['chapter_url'], lambda d: validate_gita(d, gita['chapter_blob_sha1'], 'Gita chapters'), MAX_GITA),
    ]
    for book in manifest['english']:
        book_id = book['id']
        items.append((f'pg{book_id}.txt', f'https://www.gutenberg.org/cache/epub/{book_id}/pg{book_id}.txt', lambda d, b=book: validate_pg(d, b), MAX_PG))
    # Pin original Git objects from the GRETIL-derived corpus. Check the
    # complete file SHA-1 and size instead of heuristically trusting a title.
    for book in manifest.get('gretil', []):
        if book['expected_bytes'] > MAX_GRETIL:
            raise ValueError(f"GRETIL {book['slug']}: size over cap")
        url = f"https://raw.githubusercontent.com/tokushige-koyasan/gretil-corpus/{book['upstream_commit']}/{book['source_path']}"
        items.append((f"gretil-{book['slug']}.txt",url, lambda d,b=book: validate_gretil(d,b),MAX_GRETIL))
    for filename, url, validator, cap in items:
        data, reused = obtain(dest / filename, url, validator, cap)
        receipts.append({'file': filename, 'url': url, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data), 'reused': reused})
        print(f"SOURCE_OK {filename}: {len(data):,} bytes; {'cache validated' if reused else 'downloaded'}")
    out = {'schema': 1, 'receipts': receipts}
    (dest / 'receipts.json').write_text(json.dumps(out, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dest', type=Path, default=ROOT / '_sources')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
    fetch_all(args.dest, manifest)


if __name__ == '__main__':
    main()
