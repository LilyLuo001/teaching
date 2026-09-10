#!/usr/bin/env python3
"""Extract every examiner-criticism statement from the report corpus.

Output: research/sentence_bank.csv — one row per criticism sentence, each carrying
board / series / paper / page so any downstream ranking is auditable back to the
exact source document. Nothing here is interpreted yet; this is pure extraction.
"""
import csv
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "research" / "corpus"
OUT = ROOT / "research" / "sentence_bank.csv"

# Explicit statements of candidate weakness. Deliberately broad: precision is
# restored later by reading each hit, recall matters more at this stage.
CRIT = re.compile(r"""(
    fail(ed|ure)?\s+to | did\s+not | were\s+not\s+able | unable\s+to | could\s+not |
    confus\w+ | misunderstood | misunderstanding | misconception | misread |
    misinterpret\w* | mistaken\w* | incorrect\w* | wrongly | erroneous\w* |
    omitt?ed | omission | neglect\w+ | overlook\w+ | ignor(ed|ing) |
    struggl\w+ | found\s+(this|it)\s+difficult | least\s+well | poorly\s+answered |
    not\s+well\s+answered | weaker?\s+(responses|answers|candidates) |
    lost\s+marks | gained\s+no\s+marks | scored\s+poorly | limited\s+understanding |
    lack(ed|ing|\s+of)\s* | vague | superficial | assert\w+ | unsupported |
    rarely | seldom | few\s+(candidates|students|responses) |
    common\s+(error|mistake|misconception|problem) |
    descriptive\s+rather\s+than | mere(ly)?\s+describ\w* |
    mislabel\w* | unlabel\w* | no\s+diagram | without\s+a\s+diagram |
    axes\s+(were\s+)?(not|incorrectly) | did\s+not\s+shift | wrong\s+curve |
    no\s+evaluation | little\s+evaluation | lacked\s+evaluation | did\s+not\s+evaluate |
    no\s+conclusion | unsubstantiated | irrelevant | out\s+of\s+context |
    generic | rote | formulaic | repeated\s+the\s+question | copied\s+from\s+the\s+extract
)""", re.I | re.X)

# Sentences that merely praise, or are boilerplate, are dropped.
DROP = re.compile(r"^(copyright|further copies|version\s|aqa retains|"
                  r"general certificate|report on the examination\b.*\d{4}$|"
                  r"page \d+|mark scheme|\W*$)", re.I)

PAPER_HEAD = re.compile(r"\b(paper\s*[1-4]\b|question\s*\d+\w?|"
                        r"section\s*[ab]\b|component\s*\d+)", re.I)


def series_of(name: str, text: str):
    """Derive (board, series, paper) from filename, falling back to document text."""
    board = name.split("__")[0]
    stem = name.split("__", 1)[1].rsplit(".", 1)[0]

    if board == "caie-9708":
        m = re.search(r"9708_([smw])(\d{2})", stem)
        if m:
            season = {"s": "Jun", "w": "Nov", "m": "Mar"}[m.group(1)]
            return board, f"{season} 20{m.group(2)}", ""
        return board, "Jun 2024", ""
    if board == "edexcel-9ec0":
        m = re.search(r"9ec0[-_](\d{2})[-_]pef[-_](\d{4})", stem, re.I)
        if m:
            return board, f"Jun {m.group(2)}", f"Paper {int(m.group(1))}"
    if board == "aqa-7136":
        m = re.search(r"AQA-7136(\d)-WRE-([A-Z]{3})(\d{2})", stem, re.I)
        if m:
            return board, f"{m.group(2).title()} 20{m.group(3)}", f"Paper {m.group(1)}"
    if board == "ocr-h460":
        m = re.search(r"(Summer|June|Autumn)\s+(20\d\d)", text[:4000], re.I)
        series = f"{m.group(1).title()} {m.group(2)}" if m else ""
        sub = re.search(r"(macroeconomics|microeconomics|themes-in-economics)", stem, re.I)
        return board, series, (sub.group(1).replace("-", " ").title() if sub else "")
    if board == "ap-econ":
        m = re.search(r"ap(\d{2})", stem)
        sub = "Macro" if "macro" in stem.lower() else "Micro"
        st = re.search(r"set-(\d)", stem)
        return board, f"20{m.group(1)}" if m else "", f"{sub} Set {st.group(1)}" if st else sub
    return board, "", ""


def main():
    rows = []
    sid = 0
    for f in sorted(CORPUS.glob("*.txt")):
        raw = f.read_text(encoding="utf-8", errors="ignore")
        board, series, paper_default = series_of(f.name, raw)

        page = 0
        current_head = paper_default
        for block in re.split(r"<<<PAGE (\d+)>>>", raw):
            if block.isdigit():
                page = int(block)
                continue
            flat = re.sub(r"\s+", " ", block)
            for sent in re.split(r"(?<=[.!?])\s+", flat):
                sent = sent.strip()
                head = PAPER_HEAD.search(sent[:40])
                if head and len(sent) < 60:
                    current_head = head.group(0).title()
                    continue
                if not (45 <= len(sent) <= 700) or DROP.match(sent):
                    continue
                if not CRIT.search(sent):
                    continue
                sid += 1
                rows.append(dict(id=sid, board=board, series=series,
                                 paper=paper_default or current_head,
                                 locus=current_head, page=page,
                                 source=f.name, sentence=sent))

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "board", "series", "paper", "locus",
                                           "page", "source", "sentence"])
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    print(f"{len(rows)} criticism statements -> {OUT}")
    for b, n in Counter(r["board"] for r in rows).most_common():
        print(f"  {b:16s} {n:5d}")


if __name__ == "__main__":
    main()
