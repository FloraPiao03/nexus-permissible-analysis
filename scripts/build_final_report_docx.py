#!/usr/bin/env python3
"""Build the mentor-facing DOCX from reviewed Markdown using macOS textutil."""
from __future__ import annotations

import html
import re
import subprocess
import sys
import zipfile
from pathlib import Path


def inline(text: str) -> str:
    value = html.escape(text, quote=False)
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", value)
    return value


def markdown_to_html(markdown: str) -> str:
    lines = markdown.splitlines()
    output: list[str] = []
    index = 0
    cover_open = False
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if stripped.startswith("# "):
            output.append(f'<section class="cover"><h1>{inline(stripped[2:])}</h1>')
            cover_open = True
            index += 1
            continue
        if stripped.startswith("## "):
            if cover_open:
                output.append("</section>")
                cover_open = False
            output.append(f"<h2>{inline(stripped[3:])}</h2>")
            index += 1
            continue
        if stripped.startswith("### "):
            output.append(f"<h3>{inline(stripped[4:])}</h3>")
            index += 1
            continue
        if stripped == "---":
            output.append("<hr>")
            index += 1
            continue
        if stripped.startswith("> "):
            parts = []
            while index < len(lines) and lines[index].strip().startswith("> "):
                parts.append(lines[index].strip()[2:])
                index += 1
            output.append(f'<div class="callout">{inline(" ".join(parts))}</div>')
            continue
        if "|" in stripped and index + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[index + 1]):
            headers = [cell.strip() for cell in stripped.strip("|").split("|")]
            index += 2
            rows = []
            while index < len(lines) and "|" in lines[index] and lines[index].strip():
                rows.append([cell.strip() for cell in lines[index].strip().strip("|").split("|")])
                index += 1
            output.append('<table border="1" cellspacing="0" cellpadding="5"><thead><tr>' + "".join(f"<th>{inline(cell)}</th>" for cell in headers) + "</tr></thead><tbody>")
            for row in rows:
                cells = []
                for cell in row:
                    numeric = re.match(r"^[+−-]?(?:\d[\d,]*(?:\.\d+)?(?:%| pp)?|N/A|\d+/\d+ PASS)$", cell)
                    css_class = ' class="numeric"' if numeric else ""
                    cells.append(f"<td{css_class}>{inline(cell)}</td>")
                output.append("<tr>" + "".join(cells) + "</tr>")
            output.append("</tbody></table>")
            continue
        if re.match(r"^- ", stripped):
            items = []
            while index < len(lines) and re.match(r"^- ", lines[index].strip()):
                items.append(lines[index].strip()[2:])
                index += 1
            output.extend(f'<p class="listitem">•&nbsp;&nbsp;{inline(item)}</p>' for item in items)
            continue
        if re.match(r"^\d+\. ", stripped):
            items = []
            while index < len(lines) and re.match(r"^\d+\. ", lines[index].strip()):
                items.append(re.sub(r"^\d+\. ", "", lines[index].strip()))
                index += 1
            output.extend(
                f'<p class="listitem">{number}.&nbsp;&nbsp;{inline(item)}</p>'
                for number, item in enumerate(items, start=1)
            )
            continue
        if cover_open:
            # Keep each cover metadata item on its own line. Markdown's two-space
            # hard breaks are otherwise lost by the deliberately small parser.
            output.append(f'<p class="metadata">{inline(stripped)}</p>')
            index += 1
            continue
        paragraph = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate or candidate.startswith(("#", "> ", "- ")) or candidate == "---" or re.match(r"^\d+\. ", candidate):
                break
            if "|" in candidate and index + 1 < len(lines) and re.match(r"^\s*\|?\s*:?-+", lines[index + 1]):
                break
            paragraph.append(candidate)
            index += 1
        css_class = ' class="metadata"' if cover_open else ""
        output.append(f"<p{css_class}>{inline(' '.join(paragraph))}</p>")
    if cover_open:
        output.append("</section>")
    return "\n".join(output)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: build_final_report_docx.py INPUT.md OUTPUT.docx")
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    output.parent.mkdir(parents=True, exist_ok=True)
    body = markdown_to_html(source.read_text(encoding="utf-8"))
    css = """
@page { size: Letter portrait; margin: 1in; }
body { font-family: Calibri, Arial, sans-serif; font-size: 11pt; line-height: 1.10; color: #20252b; margin: 0; }
.cover { text-align: center; padding-top: 0.35in; padding-bottom: 0.18in; border-bottom: 1px solid #b8c2cc; }
h1 { font-size: 24pt; line-height: 1.08; color: #17365d; margin: 0 0 16pt 0; font-weight: 700; }
.metadata { color: #5a6570; font-size: 11pt; margin: 5pt 0; }
h2 { font-size: 16pt; color: #2e74b5; margin: 16pt 0 8pt 0; page-break-after: avoid; }
h3 { font-size: 13pt; color: #2e74b5; margin: 12pt 0 6pt 0; page-break-after: avoid; }
p { margin: 0 0 6pt 0; }
.listitem { margin: 0 0 5pt 0.24in; text-indent: -0.18in; }
table { width: 100%; border-collapse: collapse; table-layout: auto; margin: 6pt 0 12pt 0; font-size: 9.5pt; page-break-inside: auto; }
thead { display: table-header-group; }
tr { page-break-inside: avoid; }
th { background: #f2f4f7; color: #17365d; font-weight: 700; border: 1px solid #b8c2cc; padding: 5pt 6pt; vertical-align: middle; }
td { border: 1px solid #cbd2d9; padding: 5pt 6pt; vertical-align: middle; }
td.numeric { text-align: right; }
.callout { background: #f4f6f9; border-left: 4px solid #2e74b5; padding: 9pt 12pt; margin: 10pt 0 12pt 0; color: #17365d; font-weight: 600; }
code { font-family: Menlo, Consolas, monospace; font-size: 9pt; color: #17365d; }
hr { border: 0; border-top: 1px solid #b8c2cc; margin: 18pt 0 10pt 0; }
"""
    document = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>ClinicalTrials.gov Nexus / Permissible Time-Period Analysis</title><style>{css}</style></head><body>{body}</body></html>'
    html_path = Path("/private/tmp/final_nexus_time_analysis_report.html")
    html_path.write_text(document, encoding="utf-8")
    subprocess.run(["/usr/bin/textutil", "-convert", "docx", "-output", str(output), str(html_path)], check=True)
    if not output.is_file() or output.stat().st_size == 0 or not zipfile.is_zipfile(output):
        raise RuntimeError("DOCX generation failed structural validation")
    with zipfile.ZipFile(output) as archive:
        # textutil emits a valid, intentionally minimal OOXML package. Styles may
        # be embedded in document.xml instead of a separate word/styles.xml part.
        required = {"[Content_Types].xml", "word/document.xml"}
        if not required.issubset(archive.namelist()):
            raise RuntimeError("Generated DOCX is missing required OOXML parts")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
