# FHA-443

Corpus, extractor, and frozen validation artifacts for the paper *FHA-443: An
Evidence-Anchored Corpus and Extractor for Fair Housing Act Doctrine in U.S.
District-Court Opinions* (under review, NLLP 2026).

FHA-443 holds 937 candidate records, 757 canonicalized Nature of Suit 443
district-court opinion clusters, 751 with full text, and 417 rule-positive
substantive clusters. The extractor labels five doctrinal constructs and the
proof framework with a character-offset evidence snippet behind every flag, and
a frozen three-pass Claude Opus 4.8 baseline provides the comparison reported
in the paper.

Mapped quantitative claims, every row of Tables 1--2, and all nine figures reproduce offline;
see [REPRODUCING.md](REPRODUCING.md) for the audit map. Model inference itself
is not rerun because the release contains frozen labels rather than raw model
responses or the exact inference prompt. The paper source lives in [paper/](paper/).

## What the corpus shows

Rule-based disparate-impact detection reaches precision 0.41, because the phrase
fires on recitations, on citations, and on claims the court never reaches.
The frozen LLM labels lift that to 1.00 without costing recall. The released
label artifact does not retain claim-level evidence quotations, so this result
supports the comparison but not an audit of the model's stated rationale.

| Measure | Regex | Frozen LLM |
|---|---:|---:|
| Micro F1 over five constructs | 0.767 | 0.872 |
| Proof-framework accuracy | 0.774 | 0.914 |

Refusal and steering defeat both extractors, at F1 0.67 and 0.61. Once labels are
corrected, disparate treatment leads the docket at 46.1 percent against 13.2
percent for disparate impact (exact McNemar p < .0001), and circuits range from 8
to 54 percent in impact language, so any cross-circuit index needs a case-mix
adjustment before it means anything.

## Setup

Use Python 3.11, recorded in `.python-version`, with the locked dependencies:

```bash
git clone https://github.com/garyzhang1006/fha-federal-courts.git
cd fha-federal-courts
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
```

## Reproduce

The complete workflow is offline. The LLM labels used by the paper are frozen in
`data/validation/`; reproduction does not make an API call.

```bash
make reproduce
```

This verifies frozen-input hashes, runs the test suite and deterministic analysis,
checks the declared paper claims, and regenerates all nine figures. Generated tables,
figures, and reports are written under ignored `data/processed/` and `outputs/` paths.

Building the PDF also requires `latexmk`, BibTeX, and the LaTeX/font packages
used by the ACL style. On Ubuntu, CI installs `texlive-latex-extra`,
`texlive-fonts-recommended`, and `texlive-fonts-extra`. Build with:

```bash
make paper
```

To run individual checks:

```bash
make test
python3 scripts/draw_random_sample.py
python3 scripts/score_llm_baseline.py
python3 scripts/analyze_prevalence.py
```

`draw_random_sample.py --write` overwrites the committed sample index and should only be
used when the input frame is intentionally changed.

## Repository map

- `src/fha/`: extraction, FEII, housing feasibility inputs, the LLM baseline, the cross-circuit doctrinal-split test, and the Schelling gatekeeping model. A released doctrinal-embedding module is included but not used in the sorting analysis.
- `scripts/`: reproducible entry points used by `make reproduce`.
- `data/`: frozen full-text corpus, housing panel, human coding, codebook, LLM artifacts,
  and SHA-256 manifest.
- `docs/LLM_BASELINE.md`: provenance and verification details for the frozen LLM baseline.
- `tests/`: offline regression tests.

## License

MIT. See `CITATION.cff` for citation metadata.
