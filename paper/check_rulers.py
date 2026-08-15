"""Measure, on every page, whether a review line number collides with body text.

Eyeballing a contact sheet missed this twice: at 100 dpi a three-digit gray
number sitting a millimetre inside a column looks like part of the margin. So
the check is geometric instead. acl.sty asks geometry for a4paper with 2.5cm
margins and sets \\columnsep to 0.6cm, which fixes the four bands below; a line
number is legal only inside the left margin, the gutter, or the right margin,
and it must not overlap the bounding box of any body glyph run.
"""
import re
import sys

import fitz

CM = 72.0 / 2.54
PAGE_W = 21.0 * CM          # a4
MARGIN = 2.5 * CM
GUTTER = 0.6 * CM
COL_W = (PAGE_W - 2 * MARGIN - GUTTER) / 2

COL1 = (MARGIN, MARGIN + COL_W)
COL2 = (MARGIN + COL_W + GUTTER, PAGE_W - MARGIN)
LEGAL = [(0, MARGIN), (COL1[1], COL2[0]), (COL2[1], PAGE_W)]

NUM = re.compile(r"^\d{3}$")


def is_number(span):
    font = span["font"]
    return bool(NUM.match(span["text"].strip())
                and ("Helvetica" in font or "SanL" in font or "phv" in font))


def overlap(a, b):
    return (min(a[2], b[2]) - max(a[0], b[0]) > 0.5
            and min(a[3], b[3]) - max(a[1], b[1]) > 0.5)


def main(path):
    doc = fitz.open(path)
    bad = 0
    total = 0
    for pno, page in enumerate(doc, 1):
        nums, body = [], []
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    (nums if is_number(span) else body).append(span)
        total += len(nums)
        # The failure that produced the reported mess was not a number sitting
        # on a word. It was both columns' rulers landing in the same 0.6cm
        # gutter and interleaving, so ruler-on-ruler is checked as well.
        for i, n in enumerate(nums):
            for m in nums[i + 1:]:
                if overlap(n["bbox"], m["bbox"]):
                    bad += 1
                    print("p%-3d %s and %s share space at x=%.1f"
                          % (pno, n["text"], m["text"], n["bbox"][0]))
        for n in nums:
            x0, _, x1, _ = n["bbox"]
            in_band = any(lo - 0.5 <= x0 and x1 <= hi + 0.5 for lo, hi in LEGAL)
            hit = [b for b in body if overlap(n["bbox"], b["bbox"])]
            if not in_band or hit:
                bad += 1
                why = "outside margin/gutter" if not in_band else "overlaps text"
                print("p%-3d %-4s x=[%6.1f,%6.1f]  %s  %s" % (
                    pno, n["text"], x0, x1, why,
                    repr(hit[0]["text"][:40]) if hit else ""))
    print()
    print("pages %d   line numbers %d   offending %d" % (doc.page_count, total, bad))
    print("bands: margin<%.1f  gutter %.1f-%.1f  margin>%.1f"
          % (MARGIN, COL1[1], COL2[0], COL2[1]))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
