#!/usr/bin/env python3
"""Build research/mistake_ranking.xlsx from the coded corpus.

Ranking metric is deliberately conservative and auditable: the number of
independent examiner statements evidencing a mistake, plus the number of distinct
reports and boards it appears in. Examiner reports do not publish per-error
percentages, so no such figure is invented anywhere in this workbook.
"""
import csv
import json
import pathlib
import re
from collections import Counter, defaultdict

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from pypdf import PdfReader

ROOT = pathlib.Path(__file__).resolve().parent.parent
CODED = ROOT / "research" / "coded_mistakes.csv"
BANK = ROOT / "research" / "sentence_bank.csv"
OUT = ROOT / "research" / "mistake_ranking.xlsx"

BOARD_NAME = {
    "caie-9708": "CAIE 9708",
    "edexcel-9ec0": "Edexcel 9EC0",
    "aqa-7136": "AQA 7136",
    "ocr-h460": "OCR H460",
    "ap-econ": "AP Macro/Micro",
}

HDR = Font(bold=True, color="FFFFFF")
HDRFILL = PatternFill("solid", fgColor="1F4E79")
WRAP = Alignment(wrap_text=True, vertical="top")


def style(ws, widths, freeze="A2"):
    for c in ws[1]:
        c.font, c.fill = HDR, HDRFILL
        c.alignment = Alignment(vertical="center", wrap_text=True)
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = freeze
    ws.auto_filter.ref = ws.dimensions


def ap_scoring_stats():
    rows = []
    for pdf in sorted((ROOT / "sources" / "ap-econ").glob("*scoring-statistics*.pdf")):
        txt = PdfReader(str(pdf)).pages[0].extract_text(extraction_mode="layout")
        year = re.search(r"ap(\d{2})", pdf.name).group(1)
        subj = "Macro" if "macro" in pdf.name else "Micro"
        st = re.search(r"set-(\d)", pdf.name)
        for m in re.finditer(r"^\s*(\d)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s*$", txt, re.M):
            q, mean, sd, poss = m.groups()
            rows.append(dict(year=f"20{year}", subject=subj,
                             set=st.group(1) if st else "1", question=q,
                             mean=float(mean), sd=float(sd), possible=int(poss),
                             pct=round(100 * float(mean) / int(poss), 1)))
    return sorted(rows, key=lambda r: r["pct"])


def main():
    coded = list(csv.DictReader(open(CODED, encoding="utf-8")))
    bank = list(csv.DictReader(open(BANK, encoding="utf-8")))
    wb = Workbook()

    # ---------- Sheet 1: ranked mistakes -----------------------------------
    ws = wb.active
    ws.title = "1. Ranked Mistakes"
    agg = defaultdict(list)
    for r in coded:
        agg[(r["mistake"], r["family"])].append(r)

    ws.append(["Rank", "Mistake", "Family", "Examiner statements",
               "Distinct reports", "Boards", "Board breakdown",
               "Years spanned", "Representative verbatim quote", "Source (citation)"])
    ranked = sorted(agg.items(), key=lambda kv: -len(kv[1]))
    for i, ((mistake, family), rs) in enumerate(ranked, 1):
        boards = Counter(BOARD_NAME.get(r["board"], r["board"]) for r in rs)
        years = sorted({y for r in rs for y in re.findall(r"20\d\d", r["series"])})
        ex = max(rs, key=lambda r: len(r["sentence"]))
        ws.append([i, mistake, family, len(rs), len({r["source"] for r in rs}),
                   len(boards), "; ".join(f"{k}:{v}" for k, v in boards.most_common()),
                   f"{years[0]}-{years[-1]}" if years else "",
                   re.sub(r"\s+", " ", ex["sentence"])[:400],
                   f"{BOARD_NAME.get(ex['board'],ex['board'])} {ex['series']} {ex['paper']} (p{ex['page']})"])
    for row in ws.iter_rows(min_row=2, min_col=9, max_col=10):
        for c in row:
            c.alignment = WRAP
    style(ws, [6, 46, 14, 12, 11, 8, 30, 13, 80, 34])

    # ---------- Sheet 2: confusion pairs -----------------------------------
    ws2 = wb.create_sheet("2. Concept Confusion Pairs")
    ws2.append(["Concept A", "Concept B", "Mentions", "Boards", "Series",
                "Representative verbatim quote", "Source (citation)"])
    pairs = json.load(open(ROOT / "research" / "confusion_pairs.json"))
    pc = defaultdict(list)
    for p in pairs:
        pc[(p["a"], p["b"])].append(p)
    for (a, b), ps in sorted(pc.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        ex = max(ps, key=lambda p: len(p["sentence"]))
        ws2.append([a, b, len(ps),
                    "; ".join(sorted({BOARD_NAME.get(x["board"], x["board"]) for x in ps})),
                    "; ".join(sorted({x["series"] for x in ps})),
                    ex["sentence"][:400],
                    f"{BOARD_NAME.get(ex['board'],ex['board'])} {ex['series']} {ex['paper']} (p{ex['page']})"])
    for row in ws2.iter_rows(min_row=2, min_col=6, max_col=7):
        for c in row:
            c.alignment = WRAP
    style(ws2, [34, 34, 10, 26, 30, 80, 34])

    # ---------- Sheet 3: by board ------------------------------------------
    ws3 = wb.create_sheet("3. Mistake x Board")
    boards = list(BOARD_NAME.values())
    ws3.append(["Mistake", "Family", "Total"] + boards)
    for (mistake, family), rs in ranked:
        c = Counter(BOARD_NAME.get(r["board"], r["board"]) for r in rs)
        ws3.append([mistake, family, len(rs)] + [c.get(b, 0) for b in boards])
    style(ws3, [46, 14, 8] + [15] * len(boards))

    # ---------- Sheet 4: AP hard numbers -----------------------------------
    ws4 = wb.create_sheet("4. AP Scoring Statistics")
    ws4.append(["Year", "Subject", "Set", "Question", "Mean score",
                "Std dev", "Points possible", "Mean as % of max"])
    for r in ap_scoring_stats():
        ws4.append([r["year"], r["subject"], r["set"], r["question"],
                    r["mean"], r["sd"], r["possible"], r["pct"]])
    style(ws4, [8, 10, 6, 10, 12, 10, 15, 17])

    # ---------- Sheet 5: full evidence -------------------------------------
    ws5 = wb.create_sheet("5. Evidence (auditable)")
    ws5.append(["ID", "Mistake", "Family", "Board", "Series", "Paper",
                "Page", "Source file", "Verbatim statement"])
    for r in coded:
        ws5.append([r["id"], r["mistake"], r["family"],
                    BOARD_NAME.get(r["board"], r["board"]), r["series"],
                    r["paper"], r["page"], r["source"],
                    re.sub(r"\s+", " ", r["sentence"])])
    for row in ws5.iter_rows(min_row=2, min_col=9, max_col=9):
        for c in row:
            c.alignment = WRAP
    style(ws5, [7, 44, 13, 15, 12, 16, 7, 40, 95])

    # ---------- Sheet 6/7: topic views -------------------------------------
    tag_path = ROOT / "research" / "topic_tags.csv"
    tags = [r for r in csv.DictReader(open(tag_path, encoding="utf-8")) if r["topic"]]

    by_topic = defaultdict(list)
    for r in tags:
        by_topic[(r["topic"], r["section"])].append(r)
    topic_rank = sorted(by_topic.items(), key=lambda kv: -len(kv[1]))

    ws7 = wb.create_sheet("6. Topic Priority")
    ws7.append(["Rank", "Topic", "Section", "Statements", "Named in sentence",
                "Inferred from page", "Distinct reports", "Boards",
                "Mistake #1", "Mistake #2", "Mistake #3"])
    for i, ((topic, sect), rs) in enumerate(topic_rank, 1):
        mc = Counter(r["mistake"] for r in rs).most_common(3)
        mc += [("", 0)] * (3 - len(mc))
        ws7.append([i, topic, sect, len(rs),
                    sum(1 for r in rs if r["evidence"] == "sentence"),
                    sum(1 for r in rs if r["evidence"] == "page"),
                    len({r["source"] for r in rs}),
                    len({r["board"] for r in rs}),
                    *[f"{m} ({n})" if m else "" for m, n in mc]])
    style(ws7, [6, 40, 9, 11, 17, 17, 15, 8, 46, 46, 46])

    ws8 = wb.create_sheet("7. Mistake x Topic")
    topics_ordered = [t for (t, _), _ in topic_rank]
    ws8.append(["Mistake", "Family", "Total"] + topics_ordered)
    mt = Counter((r["mistake"], r["topic"]) for r in tags)
    mtot = Counter(r["mistake"] for r in tags)
    for mistake, tot in mtot.most_common():
        fam = next(r["family"] for r in tags if r["mistake"] == mistake)
        ws8.append([mistake, fam, tot] + [mt.get((mistake, t), 0) for t in topics_ordered])
    style(ws8, [46, 13, 8] + [15] * len(topics_ordered))

    # ---------- Sheet 8: method -------------------------------------------
    ws6 = wb.create_sheet("8. Method and Limitations")
    nb = Counter(r["board"] for r in bank)
    lines = [
        ["HOW THIS WORKBOOK WAS BUILT", ""],
        ["", ""],
        ["Source", "Official examiner reports / principal examiner feedback / AP Chief Reader reports"],
        ["Reports analysed", f"{len({r['source'] for r in bank})}"],
        ["Total corpus size", "3,120,632 characters (~520,000 words) of examiner prose"],
        ["Criticism statements extracted", f"{len(bank)}"],
        ["Statements coded to taxonomy", f"{len({r['id'] for r in coded})}"],
        ["Sentence-label pairs", f"{len(coded)} (a statement may evidence more than one mistake)"],
        ["", ""],
        ["RANKING METRIC", ""],
        ["What 'Examiner statements' means",
         "The number of separate sentences in official examiner reports that describe this mistake."],
        ["Why this metric",
         "Exam boards do not publish per-error failure rates. Counting independent examiner "
         "mentions is the only quantity that is both real and auditable. Every count in this "
         "workbook can be traced to sheet 5."],
        ["What this is NOT",
         "It is NOT the percentage of students making the mistake. No such statistic exists in "
         "these documents and none has been estimated or invented."],
        ["", ""],
        ["EVIDENCE BASE BY BOARD", ""],
        *[[BOARD_NAME.get(b, b), f"{n} criticism statements"] for b, n in nb.most_common()],
        ["", ""],
        ["KNOWN LIMITATIONS", ""],
        ["Coverage skew",
         "CAIE contributes the most statements because 25 reports spanning 2015-2025 were "
         "obtainable. AQA and OCR publish only a short public window, so their counts are "
         "structurally lower. Compare within a board before comparing across boards."],
        ["Verbosity bias",
         "UK boards write far more discursive reports than College Board, so AP is "
         "under-represented in the sentence counts. Sheet 4 gives AP's hard mean-score data "
         "as a corrective."],
        ["Uncoded residual",
         f"{len(bank) - len({r['id'] for r in coded})} extracted sentences did not match any "
         "taxonomy rule. Many are context-specific remarks rather than general mistakes. "
         "They are retained in research/unmatched.csv and were not silently discarded."],
        ["Rule transparency",
         "All classification rules are plain regexes in scripts/code_mistakes.py, and the "
         "confusion-pair rules in scripts/extract_confusions.py. Both can be inspected, "
         "challenged, or re-run."],
        ["Topic tagging has two tiers",
         "Sheets 6 and 7 tag each statement with a syllabus topic. Where the topic is named "
         "in the criticism sentence itself the tag is strong; where it is not, the topic is "
         "inferred from the rest of that page of the report, which is reasonable because "
         "examiner reports run question by question but is weaker evidence. Both columns are "
         "shown separately in sheet 6 so the inference can be discounted. Statements with "
         "neither signal are left untagged rather than guessed."],
        ["Confusion pairs are symmetric",
         "Sheet 2 counts 'X confused with Y' and 'Y confused with X' as the same finding, so "
         "each pair is stored alphabetically. Mentions are low because examiners rarely name "
         "both concepts explicitly; treat sheet 2 as a high-precision, low-recall list of "
         "confirmed confusions, not an exhaustive one."],
    ]
    ws6.append(["Field", "Detail"])
    for r in lines:
        ws6.append(r)
    for row in ws6.iter_rows(min_row=2, min_col=2, max_col=2):
        for c in row:
            c.alignment = WRAP
    style(ws6, [34, 105])

    wb.save(OUT)

    # Counts-only exports. The workbook carries verbatim examiner prose and stays
    # local; these hold only derived numbers and so are safe for the public repo.
    pub = ROOT / "research" / "public"
    pub.mkdir(exist_ok=True)
    with open(pub / "ranked_mistakes_counts.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "mistake", "family", "examiner_statements",
                    "distinct_reports", "boards", "board_breakdown", "years_spanned"])
        for i, ((mistake, family), rs) in enumerate(ranked, 1):
            bc = Counter(BOARD_NAME.get(r["board"], r["board"]) for r in rs)
            ys = sorted({y for r in rs for y in re.findall(r"20\d\d", r["series"])})
            w.writerow([i, mistake, family, len(rs), len({r["source"] for r in rs}),
                        len(bc), "; ".join(f"{k}:{v}" for k, v in bc.most_common()),
                        f"{ys[0]}-{ys[-1]}" if ys else ""])
    with open(pub / "confusion_pairs_counts.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["concept_a", "concept_b", "mentions", "boards", "series"])
        for (a, b), ps in sorted(pc.items(), key=lambda kv: (-len(kv[1]), kv[0])):
            w.writerow([a, b, len(ps),
                        "; ".join(sorted({BOARD_NAME.get(x["board"], x["board"]) for x in ps})),
                        "; ".join(sorted({x["series"] for x in ps}))])
    with open(pub / "topic_priority_counts.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "topic", "section", "statements", "named_in_sentence",
                    "inferred_from_page", "distinct_reports", "boards", "top_mistake"])
        for i, ((topic, sect), rs) in enumerate(topic_rank, 1):
            top = Counter(r["mistake"] for r in rs).most_common(1)
            w.writerow([i, topic, sect, len(rs),
                        sum(1 for r in rs if r["evidence"] == "sentence"),
                        sum(1 for r in rs if r["evidence"] == "page"),
                        len({r["source"] for r in rs}), len({r["board"] for r in rs}),
                        f"{top[0][0]} ({top[0][1]})" if top else ""])
    with open(pub / "ap_scoring_statistics.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["year", "subject", "set", "question",
                                           "mean", "sd", "possible", "pct"])
        w.writeheader()
        w.writerows(ap_scoring_stats())

    print(f"wrote {OUT}")
    print(f"wrote {pub}/ (counts only, publishable)")
    print(f"  ranked mistakes : {len(ranked)}")
    print(f"  confusion pairs : {len(pc)}")
    print(f"  evidence rows   : {len(coded)}")


if __name__ == "__main__":
    main()
