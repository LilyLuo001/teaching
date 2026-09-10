#!/usr/bin/env python3
"""Probe Pearson's exam-materials CDN for Edexcel Economics examiner reports.

Pearson filenames embed the publication date, which we cannot know a priori, so
we sweep the plausible results-week windows and keep only verified 200/PDF hits.
Two filename conventions exist: 9EC0_01_pef_YYYYMMDD (pre-2020) and
9ec0-01-pef-YYYYMMDD (2020 onwards).
"""
import csv
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE = "https://qualifications.pearson.com/content/dam/pdf/A-Level/Economics/2015/Exam-materials"

CODES = ["9EC0"]
PAPERS = ["01", "02", "03"]
DOCS = ["pef"]          # principal examiner feedback == examiners' report


def windows():
    """(year, month, day) candidates: summer results week + autumn series."""
    for y in range(2017, 2026):
        for d in range(9, 27):
            yield y, 8, d          # summer series, mid-August
        for d in range(1, 32):
            yield y, 3, d          # spring publication of autumn series
    for y in (2020, 2021):
        for d in range(1, 32):
            yield y, 12, d         # Oct/Nov series published December


def candidates():
    seen = set()
    for y, m, d in windows():
        stamp = f"{y}{m:02d}{d:02d}"
        for code in CODES:
            for p in PAPERS:
                for doc in DOCS:
                    for name in (f"{code}_{p}_{doc}_{stamp}.pdf",
                                 f"{code.lower()}-{p}-{doc}-{stamp}.pdf"):
                        if name not in seen:
                            seen.add(name)
                            yield name


def head(name):
    url = f"{BASE}/{name}"
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{content_type} %{size_download}",
             "-L", "--max-time", "20", "-A", UA, url],
            capture_output=True, text=True, timeout=40).stdout.split()
        code, ctype, size = out[0], out[1] if len(out) > 1 else "", out[2] if len(out) > 2 else "0"
    except Exception:
        return None
    if code == "200" and "pdf" in ctype:
        print(f"HIT {name}  {int(size)//1024}KB", flush=True)
        return dict(url=url, name=name, code=code, ctype=ctype, size=size, ok=True)
    return None


def main():
    cands = list(candidates())
    print(f"probing {len(cands)} candidates...", flush=True)
    with ThreadPoolExecutor(max_workers=24) as pool:
        rows = [r for r in pool.map(head, cands) if r]
    with open(sys.argv[1], "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["url", "name", "code", "ctype", "size", "ok"])
        w.writeheader()
        w.writerows(rows)
    print(f"\n{len(rows)} hits -> {sys.argv[1]}")


if __name__ == "__main__":
    main()
