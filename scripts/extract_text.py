#!/usr/bin/env python3
"""Extract text from every examiner report PDF into research/corpus/*.txt.

Only examiner reports are extracted (question papers and mark schemes are kept
as PDFs for reference). Filenames encode board/paper/series so downstream coding
can cite an exact source.
"""
import pathlib
import re
import sys

from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "research" / "corpus"

# Which files in each board dir are examiner reports.
REPORT_PATTERNS = {
    "aqa-7136": re.compile(r"-WRE-", re.I),
    "ocr-h460": re.compile(r"examiners-report", re.I),
    "edexcel-9ec0": re.compile(r"[-_]pef[-_]", re.I),
    "caie-9708": re.compile(r"_er\.pdf|examiner-report", re.I),
    "edexcel-ial": re.compile(r"[-_]pef[-_]", re.I),
    "ap-econ": re.compile(r"cr-report|scoring-statistics", re.I),
}


def extract(pdf: pathlib.Path) -> str:
    reader = PdfReader(str(pdf))
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception:
            pass
    parts = []
    for i, page in enumerate(reader.pages, 1):
        try:
            parts.append(f"\n<<<PAGE {i}>>>\n" + (page.extract_text() or ""))
        except Exception as exc:
            parts.append(f"\n<<<PAGE {i} EXTRACT_ERROR {exc}>>>\n")
    return "".join(parts)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    total_chars = 0
    rows = []
    for board, pat in REPORT_PATTERNS.items():
        bdir = ROOT / "sources" / board
        if not bdir.exists():
            continue
        for pdf in sorted(bdir.glob("*.pdf")) + sorted(bdir.glob("*.PDF")):
            if not pat.search(pdf.name):
                continue
            try:
                text = extract(pdf)
            except Exception as exc:
                print(f"  FAIL {board}/{pdf.name}: {exc}")
                continue
            dest = OUT / f"{board}__{pdf.stem}.txt"
            dest.write_text(text, encoding="utf-8")
            pages = text.count("<<<PAGE")
            total_chars += len(text)
            rows.append((board, pdf.name, pages, len(text)))
            print(f"  {board:15s} {pdf.name[:52]:52s} {pages:3d}p {len(text):7d}ch")
    print(f"\n{len(rows)} reports, {total_chars:,} chars -> {OUT}")


if __name__ == "__main__":
    main()
