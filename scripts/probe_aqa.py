#!/usr/bin/env python3
"""Probe AQA filestore for A-level Economics (7136) assessment material.

Discovery only: records HTTP status + content-type for each candidate URL so we
know exactly what AQA publishes openly, rather than assuming coverage.
"""
import csv
import itertools
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"

PAPERS = ["71361", "71362", "71363"]
DOCTYPES = ["QP", "MS", "WRE"]
SERIES = [
    # (year_dir, series_dir, suffix)
    *[(y, "june", f"JUN{str(y)[2:]}") for y in range(2016, 2027)],
    *[(y, "november", f"NOV{str(y)[2:]}") for y in (2020, 2021)],
    *[(y, "autumn", f"NOV{str(y)[2:]}") for y in (2020, 2021)],
]


def head(url: str):
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code} %{content_type} %{size_download}",
             "-L", "--max-time", "20", "-A", UA, url],
            capture_output=True, text=True, timeout=40,
        ).stdout.split()
        return out[0], out[1] if len(out) > 1 else "", out[2] if len(out) > 2 else "0"
    except Exception as exc:  # network flake
        return "ERR", str(exc)[:40], "0"


def probe_one(spec):
    (yr, series, sfx), paper, dt = spec
    url = (f"https://filestore.aqa.org.uk/sample-papers-and-mark-schemes/"
           f"{yr}/{series}/AQA-{paper}-{dt}-{sfx}.PDF")
    code, ctype, size = head(url)
    ok = code == "200" and "pdf" in ctype
    if ok:
        print(f"HIT  {yr} {series} {paper} {dt}  {int(size)//1024}KB", flush=True)
    return dict(year=yr, series=series, paper=paper, doctype=dt,
                url=url, code=code, ctype=ctype, size=size, ok=ok)


def main():
    specs = list(itertools.product(SERIES, PAPERS, DOCTYPES))
    with ThreadPoolExecutor(max_workers=16) as pool:
        rows = list(pool.map(probe_one, specs))

    with open(sys.argv[1], "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    hits = sum(r["ok"] for r in rows)
    print(f"\n{hits} hits / {len(rows)} probed -> {sys.argv[1]}")


if __name__ == "__main__":
    main()
