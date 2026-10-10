#!/usr/bin/env python3
"""Extract the lecture slides into the per-slide text the quiz is built on.

The five source PDFs are PowerPoint exports: the text layer is sparse and the
real content sits in images, so what matters here is getting every caption onto
the right numbered slide. Needs `pdftotext` (poppler) on PATH.

The PDFs are not stored in this repository. Pass them explicitly:

    python3 extract_slides.py \\
        Aldieri_1_Inf_AO_15-10-25.pdf \\
        Aldieri_2_Inf_AO_22-10-25.pdf \\
        Aldieri_3_Inf_AO_30-10-25.pdf \\
        Aldieri_4_Inf_AO_05-11-25.pdf \\
        Aldieri_5_Inf_AO_11-11-25.pdf

Writes extract/deck<N>.slides.json (slide number + cleaned text) and
extract/deck<N>.md (the same, readable). The committed copies of those files are
the source of record for the questions; this script only documents how they were
produced.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "extract")

# The running header repeated on every slide of every deck.
DROP = {"BIOCHIMICA", "Aldieri Elisabetta"}

DECK_META = {
    1: {"date": "2025-10-15", "title": "Chimica generale e propedeutica biochimica"},
    2: {"date": "2025-10-22", "title": "Metabolismo energetico e metabolismo dei carboidrati"},
    3: {"date": "2025-10-30", "title": "Metabolismo dei lipidi"},
    4: {"date": "2025-11-05", "title": "Metabolismo del colesterolo e delle proteine"},
    5: {"date": "2025-11-11", "title": "Proteine plasmatiche, enzimi, vitamine ed elettroliti"},
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pdfs", nargs=5, help="the five lecture PDFs, in course order")
    args = ap.parse_args()

    if shutil.which("pdftotext") is None:
        print("FAIL: pdftotext not found on PATH (install poppler)", file=sys.stderr)
        return 1

    os.makedirs(OUT, exist_ok=True)
    manifest = []
    for deck, pdf in enumerate(args.pdfs, 1):
        raw = subprocess.run(
            ["pdftotext", "-layout", pdf, "-"],
            check=True, capture_output=True, text=True,
        ).stdout

        slides = []
        for n, page in enumerate(raw.split("\f"), 1):
            lines = []
            for line in page.split("\n"):
                s = re.sub(r"\s+", " ", line).strip()
                if not s or s in DROP:
                    continue
                lines.append(s)
            slides.append({"n": n, "text": "\n".join(lines).strip()})

        meta = DECK_META[deck]
        with open(os.path.join(OUT, f"deck{deck}.slides.json"), "w", encoding="utf-8") as fh:
            json.dump({"deck": deck, "date": meta["date"], "title": meta["title"],
                       "slides": slides}, fh, ensure_ascii=False, indent=1)
        with open(os.path.join(OUT, f"deck{deck}.md"), "w", encoding="utf-8") as fh:
            fh.write(f"# Deck {deck} — {meta['title']} ({meta['date']})\n\n")
            for s in slides:
                fh.write(f"### Slide {s['n']}\n{s['text']}\n\n")

        words = sum(len(s["text"].split()) for s in slides)
        empty = sum(1 for s in slides if not s["text"])
        manifest.append({"deck": deck, "date": meta["date"], "title": meta["title"],
                         "slides": len(slides), "empty_slides": empty, "words": words})
        print(f"deck {deck}: {len(slides):3d} slides, {empty:3d} without text, {words:5d} words")

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)
    print(f"wrote {len(manifest)} decks to {os.path.relpath(OUT, HERE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
