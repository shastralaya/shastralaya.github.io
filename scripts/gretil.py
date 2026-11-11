"""Pinned GRETIL-derived Sanskrit e-texts, preserved without textual corrections.

Text units are original lines; navigation segments are explicitly not scripture
chapters. The license applies to the adapted digital presentation, not to every
independent edition of the ancient work.
"""
from __future__ import annotations
import hashlib
import re

MAX_PART_CHARS = 52_000
MAX_LINE_CHARS = 12_000


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def validate_text(raw: bytes, item: dict) -> str:
    if len(raw) != item['expected_bytes']:
        raise ValueError(f"{item['slug']}: upstream byte length differs from pinned file")
    if git_blob_sha1(raw) != item['git_blob_sha1']:
        raise ValueError(f"{item['slug']}: pinned Git blob mismatch")
    text = raw.decode('utf-8')
    if not text.strip() or '\x00' in text or '\ufffd' in text:
        raise ValueError(f"{item['slug']}: empty, damaged or binary source")
    if len(text.splitlines()) < 8:
        raise ValueError(f"{item['slug']}: unexpectedly short transcription")
    if any(len(line) > MAX_LINE_CHARS for line in text.splitlines()):
        raise ValueError(f"{item['slug']}: source contains a pathologically long line")
    if not re.search(r'[āīūṛṝḷṅñṭḍṇśṣṃḥ]', text, flags=re.I):
        raise ValueError(f"{item['slug']}: expected IAST Sanskrit not detected")
    return text


def segment(text: str, cap: int = MAX_PART_CHARS) -> list[dict]:
    """Page boundaries never change, reorder, or drop one source codepoint."""
    if cap <= MAX_LINE_CHARS:
        raise ValueError('Page size too small for maximum source line')
    lines = text.splitlines(keepends=True)
    if ''.join(lines) != text:
        raise AssertionError('Source lost in line splitting')
    pages = []
    current = []
    size = 0
    first = 1
    for no, line in enumerate(lines, start=1):
        if current and size + len(line) > cap:
            pages.append({'first_line':first, 'last_line':no-1, 'lines':current})
            first = no
            current = []
            size = 0
        current.append((no,line))
        size += len(line)
    if current:
        pages.append({'first_line':first, 'last_line':len(lines), 'lines':current})
    if not pages or ''.join(line for page in pages for _,line in page['lines']) != text:
        raise AssertionError('Segment reconstruction failed')
    return pages
