#!/usr/bin/env python3
"""Build the Loopboard data payloads: run the pipeline and write
public/data/*.json (repo-root public dir) plus keep a copy under data/.

Usage: python3 scripts/build_loopboard.py [--out DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from recruiting.pipeline import run_pipeline, write_payloads  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "web" / "public" / "data"))
    args = ap.parse_args()

    payloads = run_pipeline()
    written = write_payloads(payloads, args.out)
    meta = payloads["meta"]
    shortlist = payloads["shortlist"]
    print(f"scored {meta['resumes_scored']} resumes -> top {len(shortlist)} shortlisted")
    print(f"top score: {shortlist[0]['score']} ({shortlist[0]['id']}, {shortlist[0]['category']})")
    print(f"wrote {len(written)} files to {args.out}: {', '.join(written)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
