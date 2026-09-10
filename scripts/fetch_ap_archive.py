#!/usr/bin/env python3
"""Fetch AP Macro/Micro Economics exam material from AP Central (officially free).

College Board never releases full multiple-choice sections, so the useful public
artefacts are:
  frq  - free-response questions
  sg   - scoring guidelines
  apc  - sample student responses + scoring commentary  <- richest source of
         evidence on what candidates actually get wrong
  crr  - chief reader report (examiner-style overview)
  ced  - course and exam description

Missing files 301-redirect to an HTML hub page, so %PDF validation is required.
"""
import pathlib
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE = "https://apcentral.collegeboard.org/media/pdf"
SUBJECTS = ["macroeconomics", "microeconomics"]
YEARS = range(15, 26)


def names():
    for s in SUBJECTS:
        yield f"ap-{s}-course-and-exam-description.pdf"
        for yy in YEARS:
            y = f"ap{yy:02d}"
            yield f"{y}-frq-{s}.pdf"
            yield f"{y}-sg-{s}.pdf"
            yield f"{y}-chief-reader-report-{s}.pdf"
            yield f"{y}-crr-{s}.pdf"
            for st in (1, 2):
                yield f"{y}-frq-{s}-set-{st}.pdf"
                yield f"{y}-sg-{s}-set-{st}.pdf"
                for q in (1, 2, 3):
                    yield f"{y}-apc-{s}-q{q}-set-{st}.pdf"
            for q in (1, 2, 3):
                yield f"{y}-apc-{s}-q{q}.pdf"


def fetch(name, dest: pathlib.Path):
    out = dest / name
    if out.exists() and out.stat().st_size > 1000:
        return "skip"
    subprocess.run(["curl", "-s", "-L", "--max-time", "120", "-A", UA,
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
    dest.mkdir(parents=True, exist_ok=True)
    todo = sorted(set(names()))
    print(f"attempting {len(todo)} AP files...", flush=True)
    with ThreadPoolExecutor(max_workers=12) as pool:
        res = list(pool.map(lambda n: fetch(n, dest), todo))
    print("\n" + ", ".join(f"{k}={v}" for k, v in sorted(Counter(res).items())))


if __name__ == "__main__":
    main()
