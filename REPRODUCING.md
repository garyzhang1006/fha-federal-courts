# Reproducing every number in the paper

The paper is *FHA-443: An Evidence-Anchored Corpus and Extractor for Fair
Housing Act Doctrine in U.S. District-Court Opinions*. Every quantitative claim
in it reproduces offline from this repository; no API call is made, because the
LLM labels are frozen in `data/validation/`.

```bash
make reproduce          # pipeline + validation + LLM scoring + prevalence + sweep
python3 scripts/make_paper_tables.py   # emit paper tables and check every claim
```

`make_paper_tables.py` exits non-zero if any repository output disagrees with a
number the paper states, and prints the disagreement.

## Claim-by-claim map

| Paper location | Claim | Command | Output |
|---|---|---|---|
| Abstract, §3 | 937 candidates, 757 canonical, 751 full text, 417 substantive | `python3 scripts/run_pipeline.py` | pipeline JSON (`identification` block); `data/raw/bulk_fha_cases.jsonl` (757 rows) + `data/validation/excluded_non_nos443.jsonl` (180 rows) |
| §4.4, Table 1 | Regex vs human P/R/F1/kappa per construct; micro 0.767 | `python3 scripts/score_goldset.py` | stdout table |
| §4.4 | Framework acc. 0.774; holding cues 0.71/0.59/0.64; 37 decisive 0.81; second-pass kappas 0.90/0.86/0.73 | `python3 scripts/score_goldset.py` | stdout |
| Appendix D (negation) | Shifts of at most 2.40 pp | `python3 scripts/validation_robustness.py` | stdout |
| §4.5, Table 2 | Regex vs LLM per construct; micro 0.767 to 0.872; framework 0.774 to 0.914; 98.8% unanimity over 1,215 decisions | `python3 scripts/score_llm_baseline.py` | `outputs/paper/validation/llm_vs_regex.csv` |
| §5.1 | Shares 46.1 / 22.4 / 13.2 / 17.1 / 7.9 on 76 substantive draws | `python3 scripts/analyze_prevalence.py` | `outputs/paper/validation/prevalence_random.csv` |
| §5.1 | Exact McNemar p = .0096 and p < .0001; accommodation-impact p = .21 | same | `outputs/paper/validation/paired_tests.csv` |
| §5.1 | Power 23.6% at n = 76; 80% power at 295 substantive (~583 draws); assurance 0.64 | same | stdout power block |
| §5.1 | Corrected shares 47.2 / 31.2 / 12.5 / 28.3 / 9.4 | same | `prevalence_random.csv`, corrected column |
| §5.2 | Impact 7.9% (Tenth) to 53.7% (Seventh); chi2 30.5 / 27.6, df 10, V 0.27 / 0.26 | `python3 scripts/circuit_split.py` | `outputs/paper/validation/circuit_prevalence.csv` |
| §5.3 | 53 of 417 directional cues; 19 of 53 plaintiff-favorable; Wilson [24.3, 49.3] | `python3 scripts/score_goldset.py` | stdout corpus win rate |
| §5.4, Appendix E | Same-type share 0.680 to 0.605 at tau 0.20; flat at tau 0.45 | `python3 scripts/run_schelling.py` | sweep output |
| §4.3 | Eight matched 2022 cells; TWFE not estimable | `python3 scripts/run_pipeline.py` | pipeline JSON `twfe.note` |
| §4.5 | Random draw seed 20260720; 729 requested passes, 728 returned | `python3 scripts/draw_random_sample.py`; `docs/LLM_BASELINE.md` | `data/validation/random_sample_index.json` |

## What is frozen and why

- `data/raw/bulk_fha_cases.jsonl` — the 757-cluster canonical snapshot. Frozen
  because CourtListener metadata changes and API quotas make live retrieval
  non-reproducible.
- `data/validation/gold_human_codings.json` — 93 primary + 30 second-pass human
  labels, coded blind to machine output.
- `data/validation/llm_labels_3pass.json` — all three Claude Opus 4.8 passes,
  verbatim. `llm_majority_votes.json` is derived; `score_llm_baseline.py`
  recomputes it and asserts the committed file matches.
- `data/validation/CODEBOOK.md` — the instructions both the human coders and
  the model received.

## Environment

Python 3.11+. `pip install -e ".[dev]"`. `make test` runs 31 offline
regression tests; all pass on a clean checkout.
