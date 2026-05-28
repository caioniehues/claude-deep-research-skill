#!/usr/bin/env python3
"""
Markdown to HTML converter for research reports
Properly converts markdown sections to HTML while preserving structure and formatting
"""

import argparse
import json
import re
import sys
from datetime import datetime
from typing import Tuple
from pathlib import Path


def convert_markdown_to_html(markdown_text: str) -> Tuple[str, str]:
    """
    Convert markdown to HTML in two parts: content and bibliography

    Args:
        markdown_text: Full markdown report text

    Returns:
        Tuple of (content_html, bibliography_html)
    """
    # Split content and bibliography
    parts = markdown_text.split('## Bibliography')
    content_md = parts[0]
    bibliography_md = parts[1] if len(parts) > 1 else ""

    # Convert content (everything except bibliography)
    content_html = _convert_content_section(content_md)

    # Convert bibliography separately
    bibliography_html = _convert_bibliography_section(bibliography_md)

    return content_html, bibliography_html


def _convert_content_section(markdown: str) -> str:
    """Convert main content sections to HTML"""
    html = markdown

    # Remove title and front matter (first ## heading is handled separately)
    lines = html.split('\n')
    processed_lines = []
    skip_until_first_section = True

    for line in lines:
        # Skip everything until we hit "## Executive Summary" or first major section
        if skip_until_first_section:
            if line.startswith('## ') and not line.startswith('### '):
                skip_until_first_section = False
                processed_lines.append(line)
            continue
        processed_lines.append(line)

    html = '\n'.join(processed_lines)

    # Convert headers
    # ## Section Title → <div class="section"><h2 class="section-title">Section Title</h2></div>
    html = re.sub(
        r'^## (.+)$',
        r'<div class="section"><h2 class="section-title">\1</h2>',
        html,
        flags=re.MULTILINE
    )

    # ### Subsection → <h3 class="subsection-title">Subsection</h3>
    html = re.sub(
        r'^### (.+)$',
        r'<h3 class="subsection-title">\1</h3>',
        html,
        flags=re.MULTILINE
    )

    # #### Subsubsection → <h4 class="subsubsection-title">Title</h4>
    html = re.sub(
        r'^#### (.+)$',
        r'<h4 class="subsubsection-title">\1</h4>',
        html,
        flags=re.MULTILINE
    )

    # Convert **bold** text
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Convert *italic* text
    html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)

    # Convert inline code `code`
    html = re.sub(r'`(.+?)`', r'<code>\1</code>', html)

    # Convert unordered lists
    html = _convert_lists(html)

    # Convert tables
    html = _convert_tables(html)

    # Convert paragraphs (wrap non-HTML lines in <p> tags)
    html = _convert_paragraphs(html)

    # Close all open sections
    html = _close_sections(html)

    # Wrap executive summary if present
    html = html.replace(
        '<h2 class="section-title">Executive Summary</h2>',
        '<div class="executive-summary"><h2 class="section-title">Executive Summary</h2>'
    )
    if '<div class="executive-summary">' in html:
        # Close executive summary at the next section
        html = html.replace(
            '</h2>\n<div class="section">',
            '</h2></div>\n<div class="section">',
            1
        )

    return html


def _convert_bibliography_section(markdown: str) -> str:
    """Convert bibliography section to HTML"""
    if not markdown.strip():
        return ""

    html = markdown

    # Convert each [N] citation to a proper bibliography entry
    # Look for patterns like [1] Title - URL
    html = re.sub(
        r'\[(\d+)\]\s*(.+?)\s*-\s*(https?://[^\s\)]+)',
        r'<div class="bib-entry"><span class="bib-number">[\1]</span> <a href="\3" target="_blank">\2</a></div>',
        html
    )

    # Convert any remaining **bold** sections
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)

    # Wrap in bibliography content div
    html = f'<div class="bibliography-content">{html}</div>'

    return html


def _convert_lists(html: str) -> str:
    """Convert markdown lists to HTML lists"""
    lines = html.split('\n')
    result = []
    in_list = False
    list_level = 0

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Check for unordered list item
        if stripped.startswith('- ') or stripped.startswith('* '):
            if not in_list:
                result.append('<ul>')
                in_list = True
                list_level = len(line) - len(line.lstrip())

            # Get the content after the marker
            content = stripped[2:]
            result.append(f'<li>{content}</li>')

        # Check for ordered list item
        elif re.match(r'^\d+\.\s', stripped):
            if not in_list:
                result.append('<ol>')
                in_list = True
                list_level = len(line) - len(line.lstrip())

            # Get the content after the number and period
            content = re.sub(r'^\d+\.\s', '', stripped)
            result.append(f'<li>{content}</li>')

        else:
            # Not a list item
            if in_list:
                # Check if we're still in the list (indented continuation)
                current_level = len(line) - len(line.lstrip())
                if current_level > list_level and stripped:
                    # Continuation of previous list item
                    if result[-1].endswith('</li>'):
                        result[-1] = result[-1][:-5] + ' ' + stripped + '</li>'
                    continue
                else:
                    # End of list
                    result.append('</ul>' if '<ul>' in '\n'.join(result[-10:]) else '</ol>')
                    in_list = False
                    list_level = 0

            result.append(line)

    # Close any remaining open list
    if in_list:
        result.append('</ul>' if '<ul>' in '\n'.join(result[-10:]) else '</ol>')

    return '\n'.join(result)


def _convert_tables(html: str) -> str:
    """Convert markdown tables to HTML tables"""
    lines = html.split('\n')
    result = []
    in_table = False

    for i, line in enumerate(lines):
        if '|' in line and line.strip().startswith('|'):
            if not in_table:
                result.append('<table>')
                in_table = True
                # This is the header row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                result.append('<thead><tr>')
                for cell in cells:
                    result.append(f'<th>{cell}</th>')
                result.append('</tr></thead>')
                result.append('<tbody>')
            elif '---' in line:
                # Skip separator row
                continue
            else:
                # Data row
                cells = [cell.strip() for cell in line.split('|')[1:-1]]
                result.append('<tr>')
                for cell in cells:
                    result.append(f'<td>{cell}</td>')
                result.append('</tr>')
        else:
            if in_table:
                result.append('</tbody></table>')
                in_table = False
            result.append(line)

    if in_table:
        result.append('</tbody></table>')

    return '\n'.join(result)


def _convert_paragraphs(html: str) -> str:
    """Wrap non-HTML lines in paragraph tags"""
    lines = html.split('\n')
    result = []
    in_paragraph = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            if in_paragraph:
                result.append('</p>')
                in_paragraph = False
            result.append(line)
            continue

        # Skip lines that are already HTML tags
        if (stripped.startswith('<') and stripped.endswith('>')) or \
           stripped.startswith('</') or \
           '<h' in stripped or '<div' in stripped or '<ul' in stripped or \
           '<ol' in stripped or '<li' in stripped or '<table' in stripped or \
           '</div>' in stripped or '</ul>' in stripped or '</ol>' in stripped:
            if in_paragraph:
                result.append('</p>')
                in_paragraph = False
            result.append(line)
            continue

        # Regular text line - wrap in paragraph
        if not in_paragraph:
            result.append('<p>' + line)
            in_paragraph = True
        else:
            result.append(line)

    if in_paragraph:
        result.append('</p>')

    return '\n'.join(result)


def _close_sections(html: str) -> str:
    """Close all open section divs"""
    # Count open and closed divs
    open_divs = html.count('<div class="section">')
    closed_divs = html.count('</div>')

    # Add closing divs for sections
    # Each section should be closed before the next section starts
    lines = html.split('\n')
    result = []
    section_open = False

    for i, line in enumerate(lines):
        if '<div class="section">' in line:
            if section_open:
                result.append('</div>')  # Close previous section
            section_open = True
        result.append(line)

    # Close final section if still open
    if section_open:
        result.append('</div>')

    return '\n'.join(result)


DEFAULT_TEMPLATE = Path(__file__).resolve().parent.parent / 'templates' / 'mckinsey_report_template.html'


def derive_title(markdown_text: str) -> str:
    """Report title: first '# ' heading, else first '## ' heading."""
    for prefix in ('# ', '## '):
        for line in markdown_text.splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix) and not stripped.startswith(prefix + '#'):
                return stripped[len(prefix):].strip()
    return 'Research Report'


def count_sources(bibliography_md: str) -> int:
    """Count unique [N] entries in the bibliography section."""
    return len(set(re.findall(r'^\[(\d+)\]', bibliography_md, flags=re.MULTILINE)))


def render_document(markdown_text: str, template_text: str) -> str:
    """Fill the report template with converted content and bibliography."""
    content_html, bib_html = convert_markdown_to_html(markdown_text)
    parts = markdown_text.split('## Bibliography')
    bib_md = parts[1] if len(parts) > 1 else ''
    substitutions = {
        '{{TITLE}}': derive_title(markdown_text),
        '{{DATE}}': datetime.now().strftime('%Y-%m-%d'),
        '{{SOURCE_COUNT}}': str(count_sources(bib_md)),
        '{{METRICS_DASHBOARD}}': '',
        '{{CONTENT}}': content_html,
        '{{BIBLIOGRAPHY}}': bib_html,
    }
    out = template_text
    for placeholder, value in substitutions.items():
        out = out.replace(placeholder, value)
    return out


def fallback_document(markdown_text: str) -> str:
    """Minimal self-contained HTML when no template is available."""
    content_html, bib_html = convert_markdown_to_html(markdown_text)
    title = derive_title(markdown_text)
    return (
        '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f'<title>{title}</title>\n</head>\n<body>\n'
        f'<h1>{title}</h1>\n{content_html}\n{bib_html}\n</body>\n</html>\n'
    )


def main():
    parser = argparse.ArgumentParser(
        description='Convert a research report markdown file to HTML.',
    )
    parser.add_argument('markdown_file', help='Path to the markdown report')
    parser.add_argument(
        '-o', '--out',
        help='Output HTML path (default: input path with a .html suffix)',
    )
    parser.add_argument(
        '--template', default=str(DEFAULT_TEMPLATE),
        help='HTML template containing {{CONTENT}}/{{BIBLIOGRAPHY}} placeholders',
    )
    parser.add_argument(
        '--fragments-only', action='store_true',
        help='Write only the content + bibliography HTML fragments (no full document)',
    )
    args = parser.parse_args()

    md_path = Path(args.markdown_file)
    if not md_path.exists():
        print(f'Error: File {md_path} not found', file=sys.stderr)
        sys.exit(1)

    markdown_text = md_path.read_text(encoding='utf-8')
    out_path = Path(args.out) if args.out else md_path.with_suffix('.html')

    if args.fragments_only:
        content_html, bib_html = convert_markdown_to_html(markdown_text)
        html = content_html + '\n' + bib_html
    else:
        template_path = Path(args.template)
        if template_path.exists():
            html = render_document(markdown_text, template_path.read_text(encoding='utf-8'))
        else:
            html = fallback_document(markdown_text)

    out_path.write_text(html, encoding='utf-8')
    print(json.dumps({
        'status': 'ok',
        'input': str(md_path),
        'output': str(out_path),
        'bytes': len(html),
    }))


if __name__ == "__main__":
    main()
