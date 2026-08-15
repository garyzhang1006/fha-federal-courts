# Reproducing the paper analyses

The paper is *FHA-443: An Evidence-Anchored Corpus and Extractor for Fair
Housing Act Doctrine in U.S. District-Court Opinions*. The 71-claim audit map,
every row of Tables 1--2, and all nine figures reproduce offline from frozen inputs. No API
call is made. The workflow rescored frozen LLM labels; it does not rerun model
inference because raw responses and the exact inference prompt are not released.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-build-isolation --no-deps -e .
make reproduce          # hashes + tests + analysis + claim audit + figures
make paper              # regenerate figures, compile PDF, check line rulers
```

`make paper` also needs `latexmk`, BibTeX, and the TeX Live LaTeX/font packages
listed in the CI workflow.

`make_paper_tables.py` exits non-zero if any declared claim is unchecked or if
an output disagrees. It writes `outputs/paper_tables/claim_audit.json` with each
expected value, actual value, tolerance, and status.

## Claim-by-claim map

| Paper location | Claim | Command | Output |
|---|---|---|---|
| Abstract, §3 | 937 candidates, 757 canonical, 751 full text, 417 substantive | `python3 scripts/run_pipeline.py` | `outputs/paper/pipeline_summary.json`; source row counts |
| §4.4, Table 1 | Regex vs human P/R/F1/kappa per construct; micro 0.767 | `python3 scripts/score_goldset.py` | `outputs/validation/goldset_precision_recall.csv` |
| §4.4 | Framework acc. 0.774; holding cues 0.71/0.59/0.64; 37 decisive 0.81; second-pass kappas 0.90/0.86/0.73 | same | `outputs/validation/goldset_metrics.json` |
| Appendix D (negation) | Shifts at most 2.40 pp; scoped micro 0.76/0.75/0.76 | `python3 scripts/validation_robustness.py` | `outputs/validation/negation_sensitivity.json` |
| §4.5, Table 2 | Regex vs LLM per construct; micro 0.767 to 0.872; framework 0.774 to 0.914; 98.8% unanimity over 1,215 decisions | `python3 scripts/score_llm_baseline.py` | `outputs/paper/validation/llm_vs_regex.csv` |
| §5.1 | Shares 46.1 / 22.4 / 13.2 / 17.1 / 7.9 on 76 substantive draws | `python3 scripts/analyze_prevalence.py` | `outputs/paper/validation/prevalence_random.csv` |
| §5.1 | Exact McNemar p = .0096 and p < .0001; accommodation-impact p = .21 | same | `outputs/paper/validation/paired_tests.csv` |
| §5.1 | Power 23.6% at n = 76; 80% power at 295 substantive (~583 draws); assurance 0.64 | same | `outputs/paper/validation/prevalence_summary.json` |
| §5.1 | Corrected shares 47.3 / 31.2 / 12.5 / 28.3 / 9.4 | same | `prevalence_random.csv`, corrected column |
| §5.2 | Impact 7.9% (Tenth) to 53.7% (Seventh); chi2 30.5 / 27.6, df 10, V 0.27 / 0.26 | `python3 scripts/circuit_split.py` | `circuit_prevalence.csv`; `circuit_split.json` |
| §5.3 | 53 of 417 directional cues; 19 of 53 plaintiff-favorable; Wilson [24.3, 49.3] | `python3 scripts/score_goldset.py` | `outputs/validation/goldset_metrics.json` |
| §5.4, Appendix E | Same-type share 0.778 to 0.723 at tau 0.20; near-flat at higher thresholds | `python3 scripts/run_schelling.py` | `outputs/schelling_scenarios.json` |
| §4.3 | Eight matched 2022 cells; TWFE not estimable | `python3 scripts/run_pipeline.py` | pipeline JSON `twfe.note` |
| §4.5 | Random draw seed 20260720; 729 requested passes, 728 returned | `python3 scripts/draw_random_sample.py`; `docs/LLM_BASELINE.md` | `data/validation/random_sample_index.json` |

## What is frozen and why

- `data/raw/bulk_fha_cases.jsonl` — the 757-cluster canonical snapshot. Frozen
  because CourtListener metadata changes and API quotas make live retrieval
  non-reproducible.
- `data/processed/paper_corpus.jsonl` — the 751-opinion full-text snapshot used by
  the offline analysis.
- `data/validation/gold_human_codings.json` — 120 primary labels, 93 of which
  overlap the frozen corpus, plus 30 second-pass labels.
- `data/validation/llm_labels_3pass.json` — all three Claude Opus 4.8 passes,
  reduced to classification fields. `llm_majority_votes.json` is derived; `score_llm_baseline.py`
  recomputes it and asserts the committed file matches.
- `data/validation/CODEBOOK.md` — the instructions both the human coders and
  the model received.

## Integrity and environment

`data/manifest.json` records exact byte sizes and SHA-256 hashes for all nine
frozen inputs. `scripts/check_inputs.py` runs before analysis and fails on a
missing or changed file. Use Python 3.11 with `requirements-lock.txt`; CI runs
the complete workflow from a clean checkout.
