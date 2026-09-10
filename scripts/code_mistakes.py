#!/usr/bin/env python3
"""Code each examiner-criticism statement into a mistake taxonomy.

Method (deliberately auditable rather than impressionistic):
  1. Drop noise — section headers, administrative boilerplate, and sentences that
     are actually praise rather than criticism.
  2. Apply an explicit, published rule dictionary. Rules are regexes visible in this
     file, so any ranking they produce can be re-derived or challenged.
  3. Multi-label: one sentence may evidence several distinct mistakes, and each is
     counted, because a sentence like "no diagram and no evaluation" is genuine
     evidence of both.

Outputs research/coded_mistakes.csv (one row per sentence-label pair).
"""
import csv
import pathlib
import re
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
BANK = ROOT / "research" / "sentence_bank.csv"
OUT = ROOT / "research" / "coded_mistakes.csv"

# --- 1. noise -------------------------------------------------------------
NOISE = [
    re.compile(r"^\W*(what common student misconceptions|common misconceptions/knowledge gaps)", re.I),
    re.compile(r"^\W*(have students|encourage students|teachers should|it is recommended)", re.I),
    re.compile(r"examiners.{0,3} report\s+\d+\s+©", re.I),
    re.compile(r"^\W*(exemplar|copyright|©|version|further copies|page \d)", re.I),
    re.compile(r"principal examiner report for teachers", re.I),
    # praise / neutral admin masquerading as criticism
    re.compile(r"(was|were) (generally |mostly |very )?well answered(\.|,| and| with)", re.I),
    re.compile(r"no (obvious overlap|issue|problem)|did not (cause|seem to) (an? )?(issue|struggle)", re.I),
    re.compile(r"(vast majority|most).{0,40}(did not struggle|wrote answers of appropriate)", re.I),
    re.compile(r"usually provided good answers|were relatively successful|mostly well answered", re.I),
    re.compile(r"cannot be held responsible for any errors", re.I),
    re.compile(r"the reports? will also explain aspects which caused difficulty", re.I),
    re.compile(r"^\W*(few candidates failed to|most candidates did precisely this)", re.I),
    re.compile(r"reports? (is|are) intended to (help|provide)", re.I),
]

# --- 2. taxonomy ----------------------------------------------------------
# (label, family, regex)
RULES = [
    # ---- diagram technique -------------------------------------------------
    ("Diagram omitted where required", "Diagram",
     r"(no diagram|without a diagram|did not (use|draw|include) a diagram|absence of a diagram|"
     r"failed to (draw|use|include) a diagram|diagrams? (were|was) (not|rarely) (used|drawn|attempted))"),
    ("Diagram drawn but mislabelled / unlabelled", "Diagram",
     r"(mislabel\w*|unlabel\w*|incorrectly labell?ed|labell?ed .{0,30}incorrectly|"
     r"missing labels|labels? (were|was) (missing|incorrect|absent)|axes .{0,25}(not|incorrectly)|"
     r"(no|without) labels?)"),
    ("Wrong curve shifted / shift vs movement along", "Diagram",
     r"(shift\w* the (wrong|incorrect)|wrong curve|incorrect curve|"
     r"(movement along|shift).{0,60}(rather than|instead of).{0,30}(shift|movement along)|"
     r"did not shift|failed to shift|shifted .{0,25}(rather than|instead of)|"
     r"(rather than|instead of) .{0,30}(a )?(movement|shift))"),
    ("Wrong diagram type chosen", "Diagram",
     r"((standard|normal) (monopoly|tariff|supply and demand) diagram|"
     r"(used|drew) a .{0,25}diagram (which|that) (restricted|was not|did not)|"
     r"inappropriate diagram|wrong diagram|not an appropriate diagram)"),
    ("Diagram drawn but not explained / not referred to", "Diagram",
     r"(diagrams?.{0,60}(not (referred|explained|used|integrated)|were not explained)|"
     r"did not (explain|refer to) (the|their) diagram|diagram.{0,30}not linked|"
     r"left the diagram to speak for itself)"),
    ("Curve/area positioned or shaded incorrectly", "Diagram",
     r"(shad\w+ (the )?area|incorrectly shad\w+|"
     r"(line|curve).{0,30}(below|above|left|right).{0,20}rather than|"
     r"locating and label\w+|not clearly show the two price|"
     r"multiple minimum points|incorrect relationship between)"),

    # ---- evaluation & judgement -------------------------------------------
    ("Evaluation absent or minimal", "Evaluation",
     r"(no evaluation|little evaluation|lacked evaluation|did not evaluate|"
     r"absence of evaluation|evaluation was (absent|missing|limited|lacking)|"
     r"failed to evaluate|without any evaluation|not (offer|provide) .{0,20}evaluation|"
     r"lack(ed|ing)? (of )?judg?ement|no judg?ement|did not (go on to )?assess|"
     r"failed to assess|did not consider whether|"
     r"only a minority .{0,30}evaluation|did not constitute evaluative|"
     r"not always focus on|never really got to)"),
    ("Evaluation superficial / generic / unconvincing", "Evaluation",
     r"(evaluation.{0,50}(superficial|generic|unconvincing|weak|vague|brief|token)|"
     r"(superficial|generic|unconvincing).{0,40}evaluation|"
     r"evaluation points tended to be|superficial, rather bland|throwaway comments)"),
    ("Conclusion missing or unsupported by the analysis", "Evaluation",
     r"(no conclusion|without a conclusion|lacked a conclusion|"
     r"conclusion.{0,60}(unsupported|not supported|brief|without .{0,20}justification|merely repeated)|"
     r"summative conclusion|failed to (include|offer|reach) a .{0,25}(conclusion|recommendation|judgement)|"
     r"recommendation without any supporting|omission of this concluding|"
     r"did not reach a conclusion|failed to reach a conclusion|"
     r"did not offer a conclusion)"),
    ("One-sided answer / only one view considered", "Evaluation",
     r"(one[- ]sided|only considered one|did not consider (the )?(other|both|negative|alternative)|"
     r"both sides.{0,40}(rarely|not|seldom)|failed to consider (the )?(other|alternative|counter))"),

    # ---- reasoning quality -------------------------------------------------
    ("Assertion without explanation / undeveloped chain of reasoning", "Reasoning",
     r"(assert\w+|merely stat\w+|simply stat\w+|stating .{0,30}without explain|"
     r"without (any |an )?explanation|did not explain|failed to explain|"
     r"not (fully )?develop\w*|undeveloped|lacked development|"
     r"brief or incorrect chains? of reasoning|chains? of reasoning.{0,30}(brief|incomplete|weak)|"
     r"explaining points rather than simply stating|"
     r"did not (fully )?develop the|relatively few .{0,25}went on to develop|"
     r"lack(ed|ing) (of )?(precision|rigour|rigor)|not .{0,20}sufficiently rigorous)"),
    ("Description instead of analysis", "Reasoning",
     r"(descriptive rather than|mere(ly)? describ\w*|described rather than|"
     r"paraphrased the (content|stimulus)|repeated the question|copied from the extract|"
     r"list(ed|ing)? .{0,30}(rather than|without)|produced a list)"),
    ("Mechanism not linked to outcome", "Reasoning",
     r"(did not (make the )?connect\w*|failed to (make the )?(link|connection)|"
     r"not connect\w*|no (clear )?link (was )?(made|established)|"
     r"did not link|link.{0,30}(was|were) (not|rarely) made)"),

    # ---- question focus ----------------------------------------------------
    ("Did not answer the question actually set", "Focus",
     r"(did not (focus|address|answer) the question|not focus\w* on the question|"
     r"drifted from the question|answer(ed)? a (different|preferred) question|"
     r"alter it to a question|did not respond to the question set|"
     r"answers need to focus on the question|out of context|irrelevant|"
     r"did not fully address the question|shifted or missed the focus|"
     r"ignored the question|failure to read the (text|question) carefully|"
     r"had ignored the question|missed the focus)"),
    ("Command word ignored (cause vs impact, advantage vs problem)", "Focus",
     r"((focus\w*|discussed?) .{0,25}(cause|causes).{0,25}rather than.{0,25}(impact|effect)|"
     r"rather than .{0,30}(impacts?|effects?|problems?|advantages?|benefits?)|"
     r"(confused|mistook) .{0,30}(benefit|advantage) .{0,20}(with|for) .{0,20}(problem|disadvantage)|"
     r"did not (clearly )?identify two)"),
    ("Stimulus material / extract data not used", "Application",
     r"((little|no|very little) use of the (stimulus|extract|data|figure)|"
     r"failed to make any use of|did not use the (extract|data|figure|stimulus)|"
     r"not use(d)? .{0,20}(extract|stimulus)|"
     r"need to use own knowledge|did not spot the need)"),
    ("Answer generic / not applied to the given context", "Application",
     r"(generic (response|answer|point|mark)|generic\b.{0,40}(context|reasoning)|"
     r"(little|no) relevant reasoning appropriate to the context|"
     r"did not relate to|not applied to the context|lacked (context|application)|"
     r"application .{0,30}(was|were) (weak|limited|absent)|"
     r"lack of (application|context)|did not relate .{0,30}to the data|"
     r"failed to recognise context|held back by a lack of application|"
     r"real world|in general but never|textbook answers|did not select relevant economic principles|used these policies in a generic way)"),

    # ---- knowledge precision ----------------------------------------------
    ("Two concepts confused with each other", "Knowledge",
     r"(confus\w+|muddl\w+|mistook|mixed up|interchangeab\w+|"
     r"did not know the difference|difference between .{0,50}(not|poorly) understood)"),
    ("Definition / terminology imprecise or vague", "Knowledge",
     r"(imprecise|vague (knowledge|understanding|definition|answer)|"
     r"loose(ly)? defined|definition.{0,30}(weak|poor|incorrect|imprecise)|"
     r"terminology.{0,30}(imprecise|weak|incorrect)|limited understanding)"),
    ("Theory recalled but misapplied", "Knowledge",
     r"(understood the (relevant )?theory but|knew the .{0,25}but|"
     r"despite knowing|correct method with the wrong|"
     r"theory .{0,30}(misapplied|not applied))"),

    # ---- quantitative ------------------------------------------------------
    ("Calculation error / formula misuse", "Quantitative",
     r"(calculation (slip|error|mistake)|unable to make this calculation|"
     r"could not (do|perform|make) the calculation|formula.{0,30}(wrong|incorrect|did not)|"
     r"who knew their .{0,15}formula and who did not|calculated the (change|wrong)|"
     r"percentage points|did not indicate if their calculations|"
     r"performed the calculation but did not state|did not show the work)"),
    ("Units, % sign, rounding or decimal places lost", "Quantitative",
     r"(omitted (the )?.{0,10}(£|\$|%|million)|incorrect units|wrong units|"
     r"rounding error|incorrectly rounded|decimal places|"
     r"did not have the % sign|units, such as|neglected to include the units|absolute rather than percentage|forget to multiply by 100|transposed incorrectly)"),
    ("Data misread from table or figure", "Quantitative",
     r"(read the data inaccurately|misread the (data|table|figure|graph)|"
     r"confused the two lines|read .{0,20}(table|figure|graph) (incorrectly|inaccurately)|"
     r"referring to 86 rather than)"),

    # ---- exam technique ----------------------------------------------------
    ("Answer length mismanaged for the mark tariff", "Technique",
     r"(wrote (far )?too much|more than was needed|excessive length|"
     r"reduced time available|too long for the marks|wrote at length)"),
    ("Question part left blank or barely attempted", "Technique",
     r"(left blank|no response|not attempted|barely attempted|did not attempt|"
     r"often ignored or given little attention|omitted the question|"
     r"put off and did not attempt)"),
    ("Not all parts / aspects of the question covered", "Technique",
     r"(did not consider all|not consider every aspect|only (covered|considered) one|"
     r"did not consider (both|all)|dwelt on one or two aspects|"
     r"failed to (cover|address) (all|both)|considered only|omitted one o[rf] more|without any consideration of|ignored the .{0,25}entirely)"),
    ("Rote or pre-learned answer reproduced", "Technique",
     r"(learned response|pre[- ]?(learned|prepared)|\brote\b|formulaic|"
     r"repeat their response for part|answer to a similar question)"),
    ("Irrelevant material included beyond the question's scope", "Focus",
     r"(even though (this|it) was not required|not required in the question|"
     r"wrote about .{0,40}even though|in isolation from|"
     r"discussed .{0,30}in depth but gained no marks|wrote at (great )?length)"),

    # ---- multiple choice (CAIE Papers 1 and 3) -----------------------------
    ("Multiple-choice distractor chosen over correct option", "MCQ",
     r"(chose (option|key|answer) [A-D]|option [A-D] was (chosen|selected)|"
     r"incorrectly chose|wrongly chose|per ?cent .{0,25}chose|"
     r"distractor|opted for option)"),

    # ---- knowledge gaps (distinct from confusion) --------------------------
    ("Key concept not recognised or not grasped at all", "Knowledge",
     r"(failed to (recognise|recognize|grasp|appreciate|realise|realize)|"
     r"did not (recognise|recognize|grasp|appreciate|realise|realize|understand what)|"
     r"seemed unaware|were unaware|unaware of|no (firm )?(grasp|understanding) of|"
     r"did not have a firm grasp|little understanding of|showed no understanding)"),
    ("Related terms not distinguished from one another", "Knowledge",
     r"(fail\w* to distinguish|did not distinguish|unable to .{0,15}distinguish|"
     r"no distinction|without .{0,20}distinction|making a distinction|"
     r"did not differentiate|fail\w* to differentiate|"
     r"did not define each term separately|not the same as)"),
    ("Incorrect statement of a standard relationship", "Knowledge",
     r"(incorrectly stat\w+|stated .{0,30}incorrectly|this was incorrect because|"
     r"wrongly stat\w+|incorrectly (defined|described|identified|answered))"),
]

COMPILED = [(lab, fam, re.compile(rx, re.I)) for lab, fam, rx in RULES]


def main():
    rows = list(csv.DictReader(open(BANK, encoding="utf-8")))
    out, noise, unmatched = [], 0, []
    for r in rows:
        s = r["sentence"]
        if any(p.search(s) for p in NOISE):
            noise += 1
            continue
        labels = [(lab, fam) for lab, fam, rx in COMPILED if rx.search(s)]
        if not labels:
            unmatched.append(r)
            continue
        for lab, fam in labels:
            out.append({**r, "family": fam, "mistake": lab})

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]) + ["family", "mistake"])
        w.writeheader()
        w.writerows(out)

    up = ROOT / "research" / "unmatched.csv"
    with open(up, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(unmatched)

    print(f"input sentences      {len(rows)}")
    print(f"dropped as noise     {noise}")
    print(f"unmatched (residual) {len(unmatched)}  -> {up.name}")
    print(f"coded sentence-labels{len(out)}  -> {OUT.name}")
    print(f"distinct sentences coded {len({r['id'] for r in out})}")
    print("\ntop labels:")
    for lab, n in Counter(r["mistake"] for r in out).most_common(30):
        print(f"  {n:5d}  {lab}")


if __name__ == "__main__":
    main()
