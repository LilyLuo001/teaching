#!/usr/bin/env python3
"""Fetch the CAIE 9708 archive (10 years) by constructing canonical filenames.

CAIE names files deterministically: 9708_<session><yy>_<doc>[_<variant>].pdf
where session is s (June), w (November) or m (March), and doc is one of
er (examiner report), gt (grade thresholds), ms (mark scheme), qp (question paper).

The mirror returns HTTP 200 with an HTML error page for files it does not have,
so every response is validated against the %PDF magic bytes before being kept.
"""
import pathlib
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE = "https://pastpapers.papacambridge.com/directories/CAIE/CAIE-pastpapers/upload"
REFERER = "https://pastpapers.papacambridge.com/"

YEARS = range(15, 26)          # 2015 .. 2025
SESSIONS = ["s", "w", "m"]
PAPERS = [1, 2, 3, 4]
VARIANTS = [1, 2, 3]


def names(kinds):
    for yy in YEARS:
        for s in SESSIONS:
            stem = f"9708_{s}{yy:02d}"
            if "er" in kinds:
                yield f"{stem}_er.pdf"
            if "gt" in kinds:
                yield f"{stem}_gt.pdf"
            for p in PAPERS:
                for v in VARIANTS:
                    if "ms" in kinds:
                        yield f"{stem}_ms_{p}{v}.pdf"
                    if "qp" in kinds:
                        yield f"{stem}_qp_{p}{v}.pdf"


def fetch(name, dest: pathlib.Path):
    out = dest / name
    if out.exists() and out.stat().st_size > 1000:
        return "skip"
    subprocess.run(["curl", "-s", "-L", "--max-time", "120", "-A", UA, "-e", REFERER,
                    "-o", str(out), f"{BASE}/{name}"], capture_output=True, timeout=180)
    if not out.exists():
        return "fail"
    if out.stat().st_size < 1000 or open(out, "rb").read(5) != b"%PDF-":
        out.unlink(missing_ok=True)
        return "absent"
    print(f"  got {name}  {out.stat().st_size//1024}KB", flush=True)
    return "ok"


def main():
    dest = pathlib.Path(sys.argv[1])
    kinds = sys.argv[2].split(",") if len(sys.argv) > 2 else ["er", "gt", "ms", "qp"]
    dest.mkdir(parents=True, exist_ok=True)
    todo = list(names(kinds))
    print(f"attempting {len(todo)} files ({','.join(kinds)})...", flush=True)
    with ThreadPoolExecutor(max_workers=12) as pool:
        res = list(pool.map(lambda n: fetch(n, dest), todo))
    print("\n" + ", ".join(f"{k}={v}" for k, v in sorted(Counter(res).items())))
    print(f"{len(list(dest.glob('*.pdf')))} PDFs now in {dest}")


if __name__ == "__main__":
    main()
