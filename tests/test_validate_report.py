#!/usr/bin/env python3
"""Tests for validate_report.py — the gating structure validator."""

import os
import subprocess
import sys
import tempfile
import unittest
from typing import Any

SCRIPT = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'validate_report.py')
FIXTURES = os.path.join(os.path.dirname(__file__), 'fixtures')


def run_vr(report_path: str) -> Any:
    """Run validate_report.py, return (exit_code, combined_output)."""
    result = subprocess.run(
        [sys.executable, SCRIPT, '--report', report_path],
        capture_output=True, text=True,
    )
    return result.returncode, result.stdout + result.stderr


def make_report(n_sources: int) -> str:
    """Build a self-consistent report whose only variable is the source count."""
    cites = ' '.join(f'[{i}]' for i in range(1, n_sources + 1))
    bib = '\n'.join(
        f'[{i}] Author{i} (2024). "Title {i}". Venue {i}. https://example.com/{i}'
        for i in range(1, n_sources + 1)
    )
    summary = (
        'This generated executive summary is written with enough flowing prose to land '
        'inside the accepted word band so the structure checks focus purely on the source '
        'floor behaviour under test here, nothing more and nothing less. '
    ) * 3
    return f"""# Research Report: Generated

## Executive Summary

{summary}

## Introduction

Scope and methodology are described here in adequate prose for the section to exist.

## Main Analysis

### Finding 1
The findings reference sources {cites} throughout the body text to satisfy citation checks
with sufficient surrounding prose to read as a genuine paragraph of analysis.

## Synthesis & Insights

Patterns and implications are discussed here with enough prose to count as a section.

## Limitations & Caveats

Known gaps are noted here so the limitations section is present and non-trivial.

## Recommendations

Immediate actions and next steps are described here for the recommendations section.

## Bibliography

{bib}

## Appendix: Methodology

The research process and verification approach are summarised in this appendix section.
"""


class TestFixtures(unittest.TestCase):
    def test_valid_report_passes(self):
        code, _ = run_vr(os.path.join(FIXTURES, 'valid_report.md'))
        self.assertEqual(code, 0)

    def test_invalid_report_fails(self):
        code, _ = run_vr(os.path.join(FIXTURES, 'invalid_report.md'))
        self.assertEqual(code, 1)

    def test_missing_file_exits_nonzero(self):
        code, _ = run_vr(os.path.join(FIXTURES, 'does_not_exist.md'))
        self.assertEqual(code, 1)


class TestSourceFloor(unittest.TestCase):
    """rp4: <5 sources is a hard error, 5-9 a warning, >=10 passes clean."""

    def _validate(self, n_sources: int) -> Any:
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'report.md')
            with open(path, 'w') as f:
                f.write(make_report(n_sources))
            return run_vr(path)

    def test_below_hard_floor_errors(self):
        code, out = self._validate(3)
        self.assertEqual(code, 1)
        self.assertIn('floor', out.lower())

    def test_graceful_band_passes_with_warning(self):
        code, out = self._validate(7)
        self.assertEqual(code, 0)
        self.assertIn('7 sources', out)

    def test_at_or_above_ten_passes(self):
        code, _ = self._validate(12)
        self.assertEqual(code, 0)


if __name__ == '__main__':
    unittest.main()
