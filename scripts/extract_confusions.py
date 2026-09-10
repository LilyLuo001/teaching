#!/usr/bin/env python3
"""Extract concept-confusion pairs (X mistaken for Y) from the sentence bank.

Confusion is symmetric, so each pair is stored alphabetically ordered: "equity vs
equality" and "equality vs equity" are the same finding and are counted once.
Every pair keeps the verbatim sentence and citation so sheet 2 of the workbook
stays auditable.
"""
import csv
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK = ROOT / "research" / "sentence_bank.csv"
OUT = ROOT / "research" / "confusion_pairs.json"

TERM = r"[A-Za-z][A-Za-z\-’'/ ]{2,44}"

PATTERNS = [
    re.compile(rf"confus\w+\s+({TERM}?)\s+(?:with|and|for)\s+({TERM}?)(?=[,.;]|\s+(?:in|when|which|and\s+the)\b|$)", re.I),
    re.compile(rf"confusion\s+(?:between|of)\s+({TERM}?)\s+and\s+({TERM}?)(?=[,.;]|$)", re.I),
    re.compile(rf"(?:not|never|rarely|failed\s+to)\s+distinguish\s+(?:between\s+)?({TERM}?)\s+(?:and|from)\s+({TERM}?)(?=[,.;]|$)", re.I),
    re.compile(rf"mistook\s+({TERM}?)\s+for\s+({TERM}?)(?=[,.;]|$)", re.I),
    re.compile(rf"({TERM}?)\s+was\s+(?:often\s+)?(?:confused|mistaken)\s+(?:with|for)\s+({TERM}?)(?=[,.;]|$)", re.I),
    re.compile(rf"(?:used|wrote|gave)\s+({TERM}?)\s+instead\s+of\s+({TERM}?)(?=[,.;]|$)", re.I),
]

# Leading filler that is not part of the concept name. "term(s)/word(s)" are only
# filler when not followed by "of" — "terms of trade" is itself a concept.
STRIP = re.compile(r"^(?:the|a|an|this|these|those|their|its|his|her|some|many|most|"
                   r"word|words|concept|concepts|idea|ideas|notion|regarding|"
                   r"relation|relationship|between|of|it\s+with|them\s+with|"
                   r"terms?(?!\s+of)|words?(?!\s+of))\s+", re.I)

# A side that contains any of these is a clause fragment, not a concept name.
NOT_A_CONCEPT = re.compile(
    r"\b(candidate|student|examiner|answer|response|question|paper|mark|marks|"
    r"they|them|there|which|that|what|who|whom|whose|this|these|those|"
    r"assumed|explained|described|stated|wrote|thought|seemed|appeared|"
    r"often|sometimes|however|therefore|instead|rather|although|because|"
    r"was|were|is|are|had|have|has|been|being|did|does|do|"
    r"figure|extract|diagram|table|line|lines|part|section|issue|point|"
    r"identif\w+|provid\w+|exist\w+|without|regarding|relation\w*|number|"
    r"one|two|three|four|five|many|few|several|other|others|both|each)\b", re.I)


def clean(side: str):
    s = re.sub(r"\s+", " ", side).strip().strip("’'\"-,.;: ").lower()
    # PDF extraction sometimes splits a final letter off a word ("revenu e").
    s = re.sub(r"(\w{3,}) ([a-z])$", r"\1\2", s)
    prev = None
    while prev != s:
        prev = s
        s = STRIP.sub("", s).strip()
        s = re.sub(r"\s+(and|or|with|to|in|for)$", "", s).strip()
    if not (3 <= len(s) <= 44):
        return None
    if len(s.split()) > 5:
        return None
    if NOT_A_CONCEPT.search(s):
        return None
    if not re.search(r"[a-z]{3}", s):
        return None
    return s


def main():
    rows = list(csv.DictReader(open(BANK, encoding="utf-8")))
    pairs = []
    seen = set()
    for r in rows:
        sent = re.sub(r"\s+", " ", r["sentence"])
        for pat in PATTERNS:
            for m in pat.finditer(sent):
                a, b = clean(m.group(1)), clean(m.group(2))
                if not a or not b or a == b:
                    continue
                a, b = sorted((a, b))
                key = (a, b, r["id"])
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(dict(a=a, b=b, board=r["board"], series=r["series"],
                                  paper=r["paper"], page=r["page"],
                                  source=r["source"], sentence=sent))

    json.dump(pairs, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    from collections import Counter
    c = Counter((p["a"], p["b"]) for p in pairs)
    print(f"{len(pairs)} confusion mentions, {len(c)} distinct pairs -> {OUT}")
    for (a, b), n in c.most_common(25):
        print(f"  {n:3d}  {a}  vs  {b}")


if __name__ == "__main__":
    main()
