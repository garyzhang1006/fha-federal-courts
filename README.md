# FHA-443

Corpus, extractor, and frozen validation artifacts for the paper *FHA-443: An
Evidence-Anchored Corpus and Extractor for Fair Housing Act Doctrine in U.S.
District-Court Opinions* (under review, NLLP 2026).

FHA-443 holds 937 candidate records, 757 canonicalized Nature of Suit 443
district-court opinion clusters, 751 with full text, and 417 rule-positive
substantive clusters. The extractor labels five doctrinal constructs and the
proof framework, attaching character offsets and snippets to its matches, and
a frozen three-pass Claude Opus 5 baseline provides the comparison reported
in the paper. A stored span exposes a match for inspection; it does not by
itself separate a recitation from an adjudication.

Mapped quantitative claims and every row of Tables 1--2 reproduce offline;
see [REPRODUCING.md](REPRODUCING.md) for the audit map. Model inference itself
is not rerun because the release contains frozen labels rather than raw model
responses or the exact inference prompt.

## What the corpus shows

Rule-based disparate-impact detection reaches precision 0.41, because the phrase
fires on recitations, on citations, and on claims the court never reaches.
The frozen LLM labels lift that to 1.00 without costing recall. The released
label artifact does not retain claim-level evidence quotations, so this result
supports the comparison but not an audit of the model's stated rationale.

| Measure | Regex | Frozen LLM |
|---|---:|---:|
| Micro F1 over five constructs | 0.767 | 0.884 |
| Proof-framework accuracy | 0.774 | 0.935 |

Refusal and steering are the weakest construct for both extractors, at F1 0.67 and 0.69. Once labels are
corrected, disparate treatment leads the docket at 46.1 percent against 13.2
percent for disparate impact (exact McNemar p < .0001), and circuits range from 8
to 54 percent in impact language, so any cross-circuit index needs a case-mix
adjustment before it means anything.

## Setup

Use Python 3.11, recorded in `.python-version`, with the locked dependencies:

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-build-isolation --no-deps -e .
python -m pip check
```

## Reproduce

The complete workflow is offline. The LLM labels used by the paper are frozen in
`data/validation/`; reproduction does not make an API call. That directory also
carries the open-weight comparison labels, produced by relabelling the same
93-case human overlap with qwen3:32b at full opinion length, and
`scripts/run_local_llm.py` is the harness that produced them.

```bash
make reproduce
```

This verifies frozen-input hashes, runs the test suite and deterministic analysis and
checks the declared paper claims. Generated tables and reports are written under ignored `data/processed/` and `outputs/` paths.

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
- `data/`: frozen full-text corpus, housing panel, human coding, codebook, LLM
  artifacts including the open-weight comparison labels, and SHA-256 manifest.
- `docs/LLM_BASELINE.md`: provenance and verification details for the frozen LLM baseline.
- `tests/`: offline regression tests.

## Citation

See `CITATION.cff`.
