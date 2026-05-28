#!/usr/bin/env python3
"""Tests for source_evaluator.py — scoring logic and the --json CLI."""

import json
import os
import subprocess
import sys
import unittest
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
import source_evaluator  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'source_evaluator.py')


class TestScoring(unittest.TestCase):
    def setUp(self):
        self.ev = source_evaluator.SourceEvaluator()

    def test_high_authority_scores_high(self):
        score = self.ev.evaluate_source(
            url='https://www.nature.com/articles/x',
            title='A Specific Empirical Result',
            publication_date='2025-10-15',
        )
        self.assertGreaterEqual(score.overall_score, 80)
        self.assertEqual(score.recommendation, 'high_trust')

    def test_sensational_low_authority_scores_lower(self):
        high = self.ev.evaluate_source(
            url='https://www.nature.com/articles/x', title='Result', publication_date='2025-10-15',
        )
        low = self.ev.evaluate_source(
            url='https://someblog.wordpress.com/p',
            title="SHOCKING! You Won't Believe This Secret!",
            publication_date='2018-01-01',
        )
        self.assertLess(low.overall_score, high.overall_score)

    def test_score_components_bounded(self):
        score = self.ev.evaluate_source(url='https://x.test/p', title='Plain title')
        for value in (score.overall_score, score.domain_authority, score.recency,
                      score.expertise, score.bias_score):
            self.assertGreaterEqual(value, 0)
            self.assertLessEqual(value, 100)


class TestCLI(unittest.TestCase):
    def _run(self, payload: str) -> Any:
        return subprocess.run(
            [sys.executable, SCRIPT, '--json', payload],
            capture_output=True, text=True,
        )

    def test_cli_emits_json_score(self):
        out = self._run('{"url": "https://www.nature.com/x", "title": "T", "publication_date": "2025-10-15"}')
        self.assertEqual(out.returncode, 0, out.stderr)
        data = json.loads(out.stdout)
        self.assertIn('overall_score', data)
        self.assertIn('recommendation', data)

    def test_missing_required_fields_exits_nonzero(self):
        out = self._run('{"url": "https://x.test"}')
        self.assertEqual(out.returncode, 1)

    def test_invalid_json_exits_nonzero(self):
        out = self._run('not json')
        self.assertEqual(out.returncode, 1)


if __name__ == '__main__':
    unittest.main()
