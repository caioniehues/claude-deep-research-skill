#!/usr/bin/env python3
"""Tests for verify_html.py — HTML/markdown consistency checks."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import verify_html  # noqa: E402

GOOD_MD = """# Report

## Executive Summary

Summary with a citation [1].

## Bibliography

[1] Smith (2024). "Title" - https://example.com/a
"""

GOOD_HTML = """<html><head><title>Report</title></head><body>
<div class="header"><h1>Report</h1></div>
<div class="content">
<div class="section"><h2 class="section-title">Executive Summary</h2>
<p>Summary with a citation [1].</p></div>
</div>
<div class="bibliography"><div class="bib-entry">[1] Smith</div></div>
</body></html>
"""


def make_verifier(html: str, md: str) -> verify_html.HTMLVerifier:
    d = tempfile.mkdtemp()
    html_path = Path(d) / 'r.html'
    md_path = Path(d) / 'r.md'
    html_path.write_text(html)
    md_path.write_text(md)
    return verify_html.HTMLVerifier(html_path, md_path)


class TestVerify(unittest.TestCase):
    def test_good_html_passes(self):
        v = make_verifier(GOOD_HTML, GOOD_MD)
        self.assertTrue(v.verify(), v.errors)

    def test_unreplaced_placeholder_fails(self):
        v = make_verifier(GOOD_HTML.replace('<h1>Report</h1>', '<h1>{{TITLE}}</h1>'), GOOD_MD)
        self.assertFalse(v.verify())
        self.assertTrue(any('placeholder' in e.lower() for e in v.errors))

    def test_emoji_fails(self):
        v = make_verifier(GOOD_HTML.replace('<h1>Report</h1>', '<h1>Report \U0001F600</h1>'), GOOD_MD)
        self.assertFalse(v.verify())
        self.assertTrue(any('emoji' in e.lower() for e in v.errors))

    def test_missing_structure_fails(self):
        v = make_verifier('<div>no html/head/body here</div>', GOOD_MD)
        self.assertFalse(v.verify())


if __name__ == '__main__':
    unittest.main()
