#!/usr/bin/env python3
"""Download every verified-OK row from a coverage CSV into a destination dir.

Usage: fetch_from_coverage.py <coverage.csv> <dest_dir>
Skips files already present, verifies the %PDF magic header, and reports failures.
"""
import csv
import pathlib
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"


def fetch(row, dest: pathlib.Path):
    url = row["url"]
    out = dest / url.rsplit("/", 1)[-1]
    if out.exists() and out.stat().st_size > 1000:
        return ("skip", out.name)
    subprocess.run(["curl", "-s", "-L", "--max-time", "120", "-A", UA, "-o", str(out), url],
                   capture_output=True, timeout=180)
    if not out.exists() or out.stat().st_size < 1000:
        return ("fail", out.name)
    with open(out, "rb") as fh:
        if fh.read(5) != b"%PDF-":
            out.unlink(missing_ok=True)
            return ("notpdf", out.name)
    return ("ok", out.name)


def main():
    csv_path, dest_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    dest_dir.mkdir(parents=True, exist_ok=True)
    rows = [r for r in csv.DictReader(open(csv_path)) if r["ok"] == "True"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda r: fetch(r, dest_dir), rows))
    tally = {}
    for status, name in results:
        tally[status] = tally.get(status, 0) + 1
        if status not in ("ok", "skip"):
            print(f"  {status}: {name}")
    print(f"{dest_dir}: " + ", ".join(f"{k}={v}" for k, v in sorted(tally.items())))


if __name__ == "__main__":
    main()
