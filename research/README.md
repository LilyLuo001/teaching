# What students actually lose marks on — an evidence-coded study of examiner reports

This directory holds a content analysis of **92 official examiner reports** covering
A-Level and AP Economics: CAIE 9708, Edexcel 9EC0, AQA 7136, OCR H460, and AP
Macro/Micro Chief Reader Reports. Roughly 520,000 words of examiner prose.

The purpose is to replace folklore about "common mistakes" with something countable.

## The metric, stated plainly

Mistakes are ranked by **the number of separate sentences in official examiner
reports that describe them**.

This is **not** the percentage of students who make the mistake. Exam boards do not
publish per-error failure rates, so that number does not exist and has not been
estimated anywhere in this study. Counting independent examiner mentions is the only
quantity here that is both real and traceable to a source document.

The one source of genuine difficulty percentages is AP's scoring-statistics releases,
which give mean scores per FRQ part. Those are reported separately and unmodified in
`public/ap_scoring_statistics.csv`.

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1. PDF → text with page markers | `scripts/extract_text.py` | `corpus/*.txt` |
| 2. Pull out criticism sentences | `scripts/build_sentence_bank.py` | `sentence_bank.csv` |
| 3. Code sentences to a mistake taxonomy | `scripts/code_mistakes.py` | `coded_mistakes.csv`, `unmatched.csv` |
| 4. Pull out named concept confusions | `scripts/extract_confusions.py` | `confusion_pairs.json` |
| 5. Build the workbook | `scripts/build_excel.py` | `mistake_ranking.xlsx`, `public/*.csv` |

Every classification rule is a plain regex in the scripts above. They can be read,
disagreed with, and re-run.

## Reading the workbook

`mistake_ranking.xlsx` has six sheets:

1. **Ranked Mistakes** — the ranking, each row with a verbatim quote and citation
2. **Concept Confusion Pairs** — specific concept A / concept B confusions
3. **Mistake × Board** — the same counts broken out per board
4. **AP Scoring Statistics** — real mean scores per FRQ part, hardest first
5. **Evidence** — all 1,079 coded sentences with board, series, paper, page
6. **Method and Limitations**

Sheet 1 is the summary; sheet 5 is the audit trail. Any count in sheet 1 can be
reconstructed by filtering sheet 5.

## Limitations, stated up front

- **Coverage is uneven.** CAIE contributes the most statements because a 2015–2025 run
  was obtainable. AQA and OCR publish only a short public window, so their counts are
  structurally lower. Compare within a board before comparing across boards.
- **Verbosity bias.** UK boards write far more discursive reports than College Board,
  so AP is under-represented in sentence counts. Sheet 4 is the corrective.
- **Uncoded residual.** 1,723 extracted sentences matched no taxonomy rule. Most are
  context-specific remarks about a particular question rather than general mistakes.
  They are kept in `unmatched.csv` rather than silently dropped.
- **Confusion pairs are high-precision, low-recall.** Examiners usually say "candidates
  were confused" without naming both concepts. Sheet 2 catches only the cases where
  both are named, so low counts there mean low reporting, not low incidence.

## Source coverage, and why it stops where it does

Held locally: 831 PDFs — 303 CAIE question papers, 301 CAIE mark schemes, 24 CAIE
examiner reports (2015–2025), plus AP, Edexcel, AQA and OCR material, and the current
specification for all five boards.

Nine CAIE examiner series could not be obtained, and the reasons are worth recording so
nobody re-searches for them:

| Series | Why it is missing |
|---|---|
| m15 | The March series for 9708 did not begin until 2016 — this report never existed |
| s20, s21 | June exams were cancelled or heavily disrupted by Covid in these years |
| w18 | Not on any freely available mirror |
| m24, s24, w24, s25, w25 | Recent series; Cambridge restricts these to registered centres |

The recent gap closes with a Cambridge centre login, which is the clean long-term route
in any case. The Covid-year gap does not close, because the assessments did not happen.

This does not weaken the ranking. The corpus still spans 2015–2025 with 92 reports
across five boards, and the two dominant mistakes appear in every year and on every
board — so no single missing series changes the ordering.

## A note on what is committed

This repository is public. The exam boards' own material — past papers, mark schemes,
examiner reports — remains their copyright and is **not** committed: not the PDFs, not
the extracted text, and not the derived files that quote examiner prose at length.
Those stay local and are reproducible by running the pipeline above against your own
copies of the source documents.

What is committed is the original analysis: the scripts, and counts-only exports in
`public/`.
