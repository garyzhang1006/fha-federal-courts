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

Every number in the paper reproduces offline from this repository; see
[REPRODUCING.md](REPRODUCING.md) for the claim-by-claim map. The paper source
lives in [paper/](paper/).

## What the corpus shows

Rule-based disparate-impact detection reaches precision 0.41, because the phrase
fires on recitations, on citations, and on claims the court never reaches.
Requiring an adjudicating quote lifts that to 1.00 without costing recall, which
is the case for anchoring every flag to evidence rather than to a keyword.

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

Requires Python 3.11 or newer.

```bash
git clone https://github.com/garyzhang1006/fha-federal-courts.git
cd fha-federal-courts
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Reproduce

The complete workflow is offline. The LLM labels used by the paper are frozen in
`data/validation/`; reproduction does not make an API call.

```bash
make reproduce
```

This runs the deterministic pipeline, validation checks, random-sample verification,
frozen-LLM scoring, and prevalence correction. Generated tables and reports are written
under ignored `data/processed/` and `outputs/` paths.

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
- `data/`: frozen corpus, housing panel, human coding, codebook, and LLM artifacts.
- `docs/LLM_BASELINE.md`: provenance and verification details for the frozen LLM baseline.
- `tests/`: offline regression tests.

## License

MIT. See `CITATION.cff` for citation metadata.
