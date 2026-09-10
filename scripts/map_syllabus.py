#!/usr/bin/env python3
"""Map each 专题 module to the syllabus sections it covers, board by board.

A module is only useful for video production if it can name the sections it serves on
each board a viewer might be sitting. Boards number and lay out their specifications
differently — CAIE and AQA put the title on the same line as the number, Edexcel and
OCR put it on the next — so section headings are normalised before matching.

Output: curriculum/syllabus_map.md
"""
import pathlib
import re

from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parent.parent
SYL = ROOT / "sources" / "syllabi"
OUT = ROOT / "curriculum" / "syllabus_map.md"

SPECS = [
    ("CAIE 9708", "caie-9708-595463-2023-2025-syllabus.pdf", r"^(\d\.\d)\s+(.+)$"),
    ("Edexcel 9EC0", "edexcel-9ec0-a-level-specification.pdf", r"^(\d\.\d\.\d)\s*(.*)$"),
    ("AQA 7136", "aqa-7136-specification.pdf", r"^(3(?:\.\d+){2,3})\s+(.+)$"),
    ("OCR H460", "ocr-h460-specification-2021.pdf", r"^(\d\.\d{1,2})\s*(.*)$"),
]

# Module -> regex over section titles. Skill modules have no syllabus home by design.
MODULES = [
    ("专题 1", "Terms of trade vs balance of trade",
     r"terms of trade|balance of payments|current account|exchange rate|"
     r"international trade|trade and (integration|globalisation)"),
    ("专题 2", "The elasticity family",
     r"elasticit"),
    ("专题 3", "Public, merit and demerit goods",
     r"public good|merit good|classification of goods|market failure|externalit|"
     r"information (failure|gaps)|types of market failure"),
    ("专题 6", "Government intervention in markets",
     r"government (intervention|failure)|reasons for government|"
     r"methods and effects of government|price control|maximum price|"
     r"minimum price|subsid|indirect tax|regulation|correcting market failure|"
     r"addressing income and wealth"),
    ("专题 7", "Inflation",
     r"inflation|deflation|price stability|price index|general price level|"
     r"measures of (inflation|economic performance)"),
    ("专题 8", "Protectionism and trade policy",
     r"protection|tariff|trade barrier|globalisation|comparative advantage|"
     r"specialisation|trading bloc|world (economy|trade)"),
    ("专题 9", "Market structures",
     r"market structure|monopol|oligopol|perfect competition|contestab|"
     r"competitive market|concentrated market|business (growth|objectives)"),
    ("专题 10", "Balance of payments vs the government budget",
     r"balance of payments|current account|fiscal polic|public (finance|expenditure)|"
     r"budget|taxation"),
    ("专题 11", "Labour market",
     r"labour market|labour|wage|trade union"),
    ("专题 12", "Costs, revenue and returns to scale",
     r"cost|revenue|returns to scale|economies of scale|production|profit"),
]
MODULES = [(c, n, re.compile(r, re.I)) for c, n, r in MODULES]

SKILL_MODULES = [
    ("专题 4", "From assertion to chain of reasoning"),
    ("专题 5", "Answer the question actually set"),
]

# Headings that are administration, not content.
# A wrapped continuation line starts lower-case or with a connector word.
CONT = re.compile(r"^(?:[a-z]|and\b|of\b|the\b|in\b|on\b|to\b|for\b|"
                  r"with\b|its\b|their\b)", re.I)

ADMIN = re.compile(r"assessment objective|scheme of assessment|command word|"
                   r"grade descript|entry|malpractice|equality|access arrangement|"
                   r"prior learning|progression|why choose|support|administration|"
                   r"result|certificat|appeal|mathematical requirement|weighting|"
                   r"overview|contents|introduction|how to|what students need", re.I)


def sections(pdf: pathlib.Path, pattern: str):
    """Yield (number, title) pairs, joining titles that sit on the next line."""
    raw = "\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages)
    lines = [re.sub(r"\s+", " ", l).strip() for l in raw.split("\n")]
    rx = re.compile(pattern)
    out, seen = [], {}
    for i, line in enumerate(lines):
        m = rx.match(line)
        if not m:
            continue
        num, title = m.group(1), (m.group(2) or "").strip()
        # Titles wrap onto following lines, or sit entirely on the next one.
        j = i
        while j + 1 < len(lines) and len(title) < 70:
            nxt = lines[j + 1]
            if not nxt or rx.match(nxt):
                break
            if not (len(title) < 12 or CONT.match(nxt)):
                break
            title = (title + " " + nxt).strip()
            j += 1
        title = re.sub(r"\s*\.{2,}\s*\d*$", "", title)
        # AQA repeats its table headers; Edexcel runs lettered content straight on.
        title = re.sub(r"\s*Content Additional information.*$", "", title, flags=re.I)
        title = re.sub(r"\s+[a-z]\)\s.*$", "", title)
        # OCR runs the assessment instruction straight on from the heading.
        title = re.sub(r"\s+(Explain|Understand|Analyse|Evaluate|Describe|Define|"
                       r"Calculate|Assess|Discuss)\b.*$", "", title).strip(" .:,")
        if not title or len(title) < 5 or ADMIN.search(title):
            continue
        # OCR restarts numbering in each component, so the number alone is not a key.
        key = (num, title[:20].lower())
        if key in seen and len(title) <= len(seen[key]):
            continue
        seen[key] = title
        out = [o for o in out if o[0:1] + (o[1][:20].lower(),) != key]
        out.append((num, title[:90]))
    return out


def main():
    parsed = {}
    for board, fname, pat in SPECS:
        p = SYL / fname
        if not p.exists():
            print(f"  missing {fname}")
            continue
        parsed[board] = sections(p, pat)
        print(f"{board:14s} {len(parsed[board]):4d} content sections")

    lines = [
        "# Syllabus map — which board sections each 专题 module serves",
        "",
        "Generated by `scripts/map_syllabus.py` from the official specifications in",
        "`sources/syllabi/`. Section numbers are the boards' own.",
        "",
        "Use this to decide what a video can claim. A module that lands on all four",
        "boards is worth making once and promoting broadly; one that lands on a single",
        "board should be pitched to that board's students specifically.",
        "",
    ]
    for code, name, rx in MODULES:
        lines += [f"## {code} — {name}", ""]
        any_hit = False
        for board, _, _ in SPECS:
            hits = [(n, t) for n, t in parsed.get(board, []) if rx.search(t)]
            if not hits:
                lines.append(f"- **{board}** — no matching section heading")
                continue
            any_hit = True
            shown = "; ".join(f"`{n}` {t}" for n, t in hits[:6])
            more = f" _(+{len(hits) - 6} more)_" if len(hits) > 6 else ""
            lines.append(f"- **{board}** — {shown}{more}")
        if not any_hit:
            lines.append("")
            lines.append("_No section matched on any board; check the module's keywords._")
        lines.append("")

    lines += ["## Skill modules", "",
              "These attack how an answer is written rather than what it is about, so they",
              "have no home in any specification. That is the point: they apply to every",
              "section on every board, which makes them the most reusable content on the",
              "channel.", ""]
    for code, name in SKILL_MODULES:
        lines.append(f"- **{code} — {name}** — all sections, all boards")
    lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
