#!/usr/bin/env python3
"""Tests for verify_citations.py — network-free coverage of parsing + heuristics.

verify_doi / verify_url hit the network, so these tests exercise only the pure
logic: bibliography parsing, hallucination heuristics, title similarity, and the
no-URL short-circuit.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import verify_citations  # noqa: E402


def make_verifier(report_text: str) -> verify_citations.CitationVerifier:
    tmp = tempfile.NamedTemporaryFile('w', suffix='.md', delete=False)
    tmp.write(report_text)
    tmp.close()
    return verify_citations.CitationVerifier(Path(tmp.name))


class TestBibliographyParsing(unittest.TestCase):
    def test_parses_entries(self):
        report = (
            '## Bibliography\n'
            '[1] Smith, J. (2025). "A Real Title". Journal. https://example.com/a\n'
            '[2] Doe, A. (2023). "Another". Venue. https://doi.org/10.1000/xyz\n'
        )
        v = make_verifier(report)
        entries = v.extract_bibliography()
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]['num'], '1')
        self.assertEqual(entries[0]['year'], '2025')
        self.assertEqual(entries[0]['title'], 'A Real Title')
        self.assertEqual(entries[0]['url'], 'https://example.com/a')
        self.assertEqual(entries[1]['doi'], '10.1000/xyz')

    def test_missing_bibliography_records_error(self):
        v = make_verifier('# Report\n\nNo bibliography here.\n')
        entries = v.extract_bibliography()
        self.assertEqual(entries, [])
        self.assertTrue(any('Bibliography' in e for e in v.errors))


class TestHallucinationHeuristics(unittest.TestCase):
    def setUp(self):
        self.v = make_verifier('## Bibliography\n[1] x\n')

    def test_future_year_flagged(self):
        future = datetime.now().year + 2
        issues = self.v.detect_hallucination_patterns(
            {'title': 'Some Study', 'year': str(future), 'doi': None, 'url': None}
        )
        self.assertTrue(any('Future year' in i for i in issues))

    def test_anachronistic_ai_flagged(self):
        issues = self.v.detect_hallucination_patterns(
            {'title': 'Deep LLM Transformers', 'year': '1995', 'doi': None, 'url': None}
        )
        self.assertTrue(any('Anachronistic' in i for i in issues))

    def test_recent_without_verification_flagged(self):
        recent = datetime.now().year
        issues = self.v.detect_hallucination_patterns(
            {'title': 'Brand New Finding', 'year': str(recent), 'doi': None, 'url': None}
        )
        self.assertTrue(any('no verification method' in i for i in issues))

    def test_clean_entry_has_no_issues(self):
        issues = self.v.detect_hallucination_patterns(
            {'title': 'A Specific Empirical Result on Widgets', 'year': '2020',
             'doi': '10.1/x', 'url': 'https://example.com'}
        )
        self.assertEqual(issues, [])


class TestTitleSimilarity(unittest.TestCase):
    def setUp(self):
        self.v = make_verifier('## Bibliography\n[1] x\n')

    def test_identical_titles(self):
        self.assertEqual(self.v.check_title_similarity('Quantum Computing', 'Quantum Computing'), 1.0)

    def test_disjoint_titles(self):
        self.assertEqual(self.v.check_title_similarity('apples oranges', 'rockets planets'), 0.0)

    def test_empty_title(self):
        self.assertEqual(self.v.check_title_similarity('', 'anything'), 0.0)


class TestVerifyUrlNoNetwork(unittest.TestCase):
    def test_empty_url_short_circuits(self):
        v = make_verifier('## Bibliography\n[1] x\n')
        ok, msg = v.verify_url('')
        self.assertFalse(ok)
        self.assertEqual(msg, 'No URL')


if __name__ == '__main__':
    unittest.main()
