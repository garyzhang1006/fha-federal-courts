# Paper source

ACL-format LaTeX for the NLLP 2026 submission. Build:

```bash
latexmk -pdf -bibtex fha443.tex
```

`\usepackage[review]{acl}` produces the anonymized, line-numbered review
version; switch to `[final]` for camera-ready and restore the author block in
`\author`. Nothing else changes between the two. The repository URL is written
once as `\repowhere` and appears only when the paper is not anonymized, so the
blind copy cannot leak it and the camera-ready cannot omit it. Figures are the
released PNGs in `media/`.

## Line numbers

`acl.sty` loads `lineno` with the `switch` option, which alternates the ruler by
page parity. In a two-column body that puts both columns' rulers inside the
0.6cm gutter, where they interleave with each other and collide with the text.
The preamble forces left-side numbering at 0.13cm separation in 6.5pt digits, so
column one's ruler sits in the page margin and only column two's uses the
gutter.

`check_rulers.py` verifies that geometrically rather than by eye, which is what
catches the failure: at screen resolution a gray number a millimetre inside a
column reads as part of the margin.

```bash
python3 check_rulers.py fha443.pdf
```

It exits non-zero if any line number falls outside the margin and gutter bands,
overlaps a glyph run, or overlaps another line number.
