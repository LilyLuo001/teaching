#!/usr/bin/env python3
"""Tag each coded criticism sentence with the syllabus topic it concerns.

Two evidence levels, kept distinct rather than blended:

  "sentence"  the topic is named in the criticism sentence itself (high precision)
  "page"      the topic is not named in the sentence, so it is inferred from the
              rest of that page of the examiner report (examiner reports are
              organised question by question, so the page is a fair proxy)

Sentences with neither are left untagged rather than assigned a guess. The split is
reported so downstream use can discount the weaker level.
"""
import csv
import pathlib
import re
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
CORPUS = ROOT / "research" / "corpus"
CODED = ROOT / "research" / "coded_mistakes.csv"
OUT = ROOT / "research" / "topic_tags.csv"

# (topic, section, regex). Cross-board A-Level / AP syllabus topics.
TOPICS = [
    ("Scarcity, opportunity cost and the PPC", "Micro",
     r"opportunity cost|production possibilit|\bppc\b|\bppf\b|scarcit|"
     r"factors? of production|basic economic problem"),
    ("Demand, supply and the price mechanism", "Micro",
     r"price mechanism|market equilibrium|equilibrium price|excess (demand|supply)|"
     r"shifts? (in|of) (the )?(demand|supply) curve|movement along|"
     r"demand and supply|supply and demand|rationing|signalling|incentive function"),
    ("Elasticities (PED, PES, YED, XED)", "Micro",
     r"elasticit|\bped\b|\bpes\b|\byed\b|\bxed\b|price elastic|income elastic|"
     r"cross elastic|inelastic"),
    ("Consumer choice and utility", "Micro",
     r"marginal utility|total utility|diminishing marginal utility|indifference curve|"
     r"budget line|budget constraint|income and substitution effect|substitution effect|"
     r"consumer equilibrium|behavioural econom|bounded rational|nudge"),
    ("Costs, revenue, profit and returns to scale", "Micro",
     r"cost curve|average (total |variable |fixed )?cost|marginal cost|fixed cost|"
     r"variable cost|total revenue|marginal revenue|average revenue|normal profit|"
     r"supernormal profit|abnormal profit|economies of scale|diseconomies|"
     r"returns to scale|diminishing returns|short run and long run cost|shut.?down"),
    ("Market structures", "Micro",
     r"monopol|oligopol|perfect competition|perfectly competitive|"
     r"monopolistic competition|market structure|contestab|barriers to entry|"
     r"price discriminat|kinked demand|collusion|cartel|game theory|prisoner"),
    ("Labour market", "Micro",
     r"labour market|market for labour|demand for labour|supply of labour|\bwage|"
     r"trade union|minimum wage|monopsony|marginal revenue product|\bmrp\b|"
     r"wage differential|labour force participation"),
    ("Market failure and externalities", "Micro",
     r"market failure|externalit|public good|merit good|demerit good|free.?rider|"
     r"non.?excludab|non.?rival|information (failure|asymmetr)|asymmetric information|"
     r"moral hazard|adverse selection|social (cost|benefit)|private (cost|benefit)|"
     r"tragedy of the commons|common access"),
    ("Government intervention in markets", "Micro",
     r"indirect tax|specific tax|ad valorem|subsid|price ceiling|price floor|"
     r"maximum price|minimum price|price control|buffer stock|regulation|"
     r"tradable permit|pollution permit|carbon tax|nationalis|privatis|"
     r"government failure|state provision"),
    ("Efficiency and welfare", "Micro",
     r"allocative efficien|productive efficien|dynamic efficien|\bx.?efficien|"
     r"pareto|consumer surplus|producer surplus|economic welfare|deadweight|"
     r"welfare loss|welfare gain"),
    ("Income distribution, poverty and equity", "Micro",
     r"income distribution|wealth distribution|inequalit|\bgini\b|lorenz|"
     r"poverty|absolute poverty|relative poverty|redistribut|equity|"
     r"progressive tax|regressive tax|transfer payment"),
    ("National income accounting and GDP", "Macro",
     r"\bgdp\b|\bgnp\b|\bgni\b|national income|nominal and real|real gdp|"
     r"circular flow|injections?|leakages?|withdrawal|"
     r"purchasing power parit|\bppp\b|standard of living|\bhdi\b"),
    ("AD/AS and the multiplier", "Macro",
     r"aggregate demand|aggregate supply|\bad\b curve|\bas\b curve|\blras\b|\bsras\b|"
     r"multiplier|accelerator|marginal propensity|output gap|"
     r"keynesian|classical (range|model)|equilibrium national income"),
    ("Economic growth and the business cycle", "Macro",
     r"economic growth|business cycle|trade cycle|recession|boom|slump|"
     r"actual and potential growth|potential output|sustainable growth"),
    ("Inflation and deflation", "Macro",
     r"inflation|deflation|disinflation|\bcpi\b|\brpi\b|price level|"
     r"cost.?push|demand.?pull|hyperinflation|indexation"),
    ("Unemployment", "Macro",
     r"unemploy|employment rate|frictional|structural unemploy|cyclical unemploy|"
     r"seasonal unemploy|natural rate|\bnairu\b|phillips curve|underemploy"),
    ("Fiscal policy", "Macro",
     r"fiscal polic|budget deficit|budget surplus|government (spending|expenditure)|"
     r"national debt|public sector borrowing|automatic stabilis|crowding out|"
     r"direct tax|taxation polic|austerity"),
    ("Monetary policy, money and banking", "Macro",
     r"monetary polic|interest rate|central bank|money supply|"
     r"quantitative easing|\bqe\b|commercial bank|credit creation|liquidity|"
     r"money market|reserve requirement|discount rate|open market operation|"
     r"functions of money|store of value|medium of exchange|unit of account"),
    ("Supply-side policy", "Macro",
     r"supply.?side|deregulation|labour market flexib|productivity growth|"
     r"education and training polic|infrastructure investment"),
    ("International trade and protectionism", "Macro",
     r"comparative advantage|absolute advantage|specialisation and trade|"
     r"free trade|protectionis|tariff|\bquota|dumping|trade barrier|"
     r"terms of trade|trade creation|trade diversion|customs union|"
     r"world trade organi|\bwto\b|globalisation"),
    ("Exchange rates", "Macro",
     r"exchange rate|deprecia|apprecia|devalu|revalu|floating rate|fixed rate|"
     r"currency|\bforex\b|marshall.?lerner|j.?curve"),
    ("Balance of payments", "Macro",
     r"balance of payments|current account|capital account|financial account|"
     r"trade deficit|trade surplus|balance of trade|\bnet exports\b"),
    ("Development economics", "Macro",
     r"developing (countr|econom)|less developed|economic development|"
     r"foreign (aid|direct investment)|\bfdi\b|dual economy|informal sector|"
     r"sustainable development|debt relief"),
    ("Macro objectives and policy conflicts", "Macro",
     r"policy conflict|trade.?off between|macroeconomic objective|"
     r"conflict between (objectives|policies)|policy objective"),
]
TOPICS = [(t, s, re.compile(r, re.I)) for t, s, r in TOPICS]


def page_topics():
    """topic hits per (source file, page), from the full report text."""
    out = {}
    for f in sorted(CORPUS.glob("*.txt")):
        raw = f.read_text(encoding="utf-8", errors="ignore")
        page = 0
        for block in re.split(r"<<<PAGE (\d+)>>>", raw):
            if block.isdigit():
                page = int(block)
                continue
            hits = Counter()
            for topic, _, rx in TOPICS:
                n = len(rx.findall(block))
                if n:
                    hits[topic] = n
            if hits:
                out[(f.name, str(page))] = hits
    return out


def main():
    coded = list(csv.DictReader(open(CODED, encoding="utf-8")))
    pt = page_topics()

    rows = []
    for r in coded:
        own = [t for t, _, rx in TOPICS if rx.search(r["sentence"])]
        if own:
            level, topics = "sentence", own
        else:
            hits = pt.get((r["source"], r["page"]))
            # Only accept a page inference when the page has a clear leading topic.
            if hits:
                top = hits.most_common()
                lead = [t for t, n in top if n == top[0][1]]
                level, topics = ("page", lead) if len(lead) <= 2 else ("", [])
            else:
                level, topics = "", []
        for t in topics or [""]:
            sect = next((s for tt, s, _ in TOPICS if tt == t), "")
            rows.append(dict(id=r["id"], mistake=r["mistake"], family=r["family"],
                             topic=t, section=sect, evidence=level,
                             board=r["board"], series=r["series"], paper=r["paper"],
                             page=r["page"], source=r["source"],
                             sentence=r["sentence"]))

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "mistake", "family", "topic", "section",
                                           "evidence", "board", "series", "paper",
                                           "page", "source", "sentence"])
        w.writeheader()
        w.writerows(rows)

    lv = Counter(r["evidence"] for r in rows)
    tagged = {r["id"] for r in rows if r["topic"]}
    print(f"{len(rows)} rows -> {OUT}")
    print(f"  coded sentences      : {len({r['id'] for r in coded})}")
    print(f"  with a topic         : {len(tagged)}")
    print(f"  sentence-level tags  : {lv['sentence']}")
    print(f"  page-inferred tags   : {lv['page']}")
    print(f"  untagged             : {lv['']}")
    print()
    tc = Counter(r["topic"] for r in rows if r["topic"])
    for t, n in tc.most_common():
        print(f"  {n:4d}  {t}")


if __name__ == "__main__":
    main()
