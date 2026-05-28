#!/usr/bin/env python3
"""Tests for md_to_html.py — markdown->HTML conversion and CLI disk output."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import md_to_html  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'md_to_html.py')

SAMPLE = """# Quantum Report

## Executive Summary

A concise summary with a citation [1] and emphasis on **key** results.

## Finding 1

Detailed prose about the finding with another citation [2] in the body.

## Bibliography

[1] Smith (2024). "First" - https://example.com/a
[2] Jones (2023). "Second" - https://example.com/b
"""


class TestConversion(unittest.TestCase):
    def test_splits_content_and_bibliography(self):
        content, bib = md_to_html.convert_markdown_to_html(SAMPLE)
        self.assertIn('<h2 class="section-title">Finding 1</h2>', content)
        self.assertNotIn('Bibliography', content)
        self.assertIn('bib-entry', bib)

    def test_derive_title_prefers_h1(self):
        self.assertEqual(md_to_html.derive_title(SAMPLE), 'Quantum Report')

    def test_count_sources(self):
        bib_md = SAMPLE.split('## Bibliography')[1]
        self.assertEqual(md_to_html.count_sources(bib_md), 2)

    def test_fallback_document_is_self_contained(self):
        html = md_to_html.fallback_document(SAMPLE)
        self.assertTrue(html.lstrip().startswith('<!DOCTYPE html>'))
        self.assertIn('Quantum Report', html)


class TestCLI(unittest.TestCase):
    def _run(self, *args: str) -> Any:
        result = subprocess.run(
            [sys.executable, SCRIPT, *args],
            capture_output=True, text=True,
        )
        return result

    def test_writes_full_document_to_disk(self):
        with tempfile.TemporaryDirectory() as d:
            md = os.path.join(d, 'r.md')
            with open(md, 'w') as f:
                f.write(SAMPLE)
            out = self._run(md)
            self.assertEqual(out.returncode, 0, out.stderr)
            payload = json.loads(out.stdout)
            html_path = payload['output']
            self.assertTrue(os.path.exists(html_path))
            html = open(html_path).read()
            # Template placeholders must be fully substituted.
            self.assertNotIn('{{', html)
            self.assertIn('Quantum Report', html)

    def test_fragments_only(self):
        with tempfile.TemporaryDirectory() as d:
            md = os.path.join(d, 'r.md')
            out_html = os.path.join(d, 'frag.html')
            with open(md, 'w') as f:
                f.write(SAMPLE)
            out = self._run(md, '-o', out_html, '--fragments-only')
            self.assertEqual(out.returncode, 0, out.stderr)
            self.assertTrue(os.path.exists(out_html))

    def test_missing_file_exits_nonzero(self):
        out = self._run(os.path.join('does', 'not', 'exist.md'))
        self.assertEqual(out.returncode, 1)


if __name__ == '__main__':
    unittest.main()
