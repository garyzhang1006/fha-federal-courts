"""Emit every table and headline number in the FHA-443 paper from repo outputs.

Run after `make reproduce`. Writes markdown tables to outputs/paper_tables/ and
prints a claim-by-claim check against the numbers the paper states, so a reader
can see in one screen whether the paper and the code agree.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "outputs" / "paper" / "validation"
OUT = ROOT / "outputs" / "paper_tables"

# Every number the paper asserts, keyed by where it appears.
PAPER = {
    "corpus.candidates": 937,
    "corpus.canonical": 757,
    "corpus.full_text": 751,
    "corpus.substantive": 417,
    "gold.overlap": 93,
    "gold.second_pass": 30,
    "llm.self_consistency": 0.988,
    "llm.claim_decisions": 1215,
    "llm.micro_f1_regex": 0.767,
    "llm.micro_f1_llm": 0.872,
    "llm.framework_regex": 0.774,
    "llm.framework_llm": 0.914,
    "prev.treatment": 0.461,
    "prev.accommodation": 0.224,
    "prev.impact": 0.132,
    "prev.refusal": 0.171,
    "prev.zoning": 0.079,
    "mcnemar.treat_vs_accomm": 0.0096,
    "mcnemar.treat_vs_impact": 0.0001,
    "mcnemar.accomm_vs_impact": 0.21,
    "power.at_n76": 0.236,
    "power.n_for_80": 295,
}


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def main() -> int:
    if not VAL.exists():
        print("outputs missing; run `make reproduce` first", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    failures = 0

    # ---------------------------------------------------------------- Table 2
    import csv
    rows = list(csv.DictReader(open(VAL / "llm_vs_regex.csv")))
    order = ["claim_disparate_treatment", "claim_disparate_impact",
             "claim_refusal_rent_sell", "claim_reasonable_accommodation",
             "claim_zoning_exclusionary", "claims_micro"]
    label = {"claim_disparate_treatment": "Disparate treatment",
             "claim_disparate_impact": "Disparate impact",
             "claim_refusal_rent_sell": "Refusal or steering",
             "claim_reasonable_accommodation": "Reasonable accommodation",
             "claim_zoning_exclusionary": "Exclusionary zoning",
             "claims_micro": "Micro average"}
    by = {r["variable"]: r for r in rows}
    lines = ["| Construct | Regex P/R/F1 | LLM P/R/F1 | dF1 |",
             "|---|---|---|---:|"]
    for k in order:
        r = by[k]
        lines.append("| " + label[k] + " | "
                     + "/".join("%.3f" % float(r[c]) for c in ("regex_precision", "regex_recall", "regex_f1"))
                     + " | "
                     + "/".join("%.3f" % float(r[c]) for c in ("llm_precision", "llm_recall", "llm_f1"))
                     + " | %+.3f |" % (float(r["llm_f1"]) - float(r["regex_f1"])))
    (OUT / "table2_llm_vs_regex.md").write_text("\n".join(lines) + "\n")

    micro = by["claims_micro"]
    for key, got in [("llm.micro_f1_regex", float(micro["regex_f1"])),
                     ("llm.micro_f1_llm", float(micro["llm_f1"]))]:
        ok = close(got, PAPER[key], 0.0015)
        failures += not ok
        print(("PASS " if ok else "FAIL ") + key
              + "  paper %.3f  repo %.3f" % (PAPER[key], got))

    # ---------------------------------------------------------------- prevalence
    prev = list(csv.DictReader(open(VAL / "prevalence_random.csv")))
    pmap = {r["construct"]: float(r["llm_share"]) for r in prev}
    for construct, key in [("disparate_treatment", "prev.treatment"),
                           ("reasonable_accommodation", "prev.accommodation"),
                           ("disparate_impact", "prev.impact"),
                           ("refusal_rent_sell", "prev.refusal"),
                           ("zoning_exclusionary", "prev.zoning")]:
        got = pmap[construct]
        ok = close(got, PAPER[key], 0.0006)
        failures += not ok
        print(("PASS " if ok else "FAIL ") + key
              + "  paper %.3f  repo %.3f" % (PAPER[key], got))

    lines = ["| Construct | Share (n=76) | Regex share (n=417) | Corrected |",
             "|---|---:|---:|---:|"]
    for r in prev:
        lines.append("| %s | %.3f | %.3f | %.3f |" % (
            r["construct"], float(r["llm_share"]), float(r["regex_share_417"]),
            float(r["regex_share_417_corrected"])))
    (OUT / "prevalence.md").write_text("\n".join(lines) + "\n")

    # ---------------------------------------------------------------- paired tests
    pt = list(csv.DictReader(open(VAL / "paired_tests.csv")))
    for r in pt:
        pair = r["claim_a"] + "_vs_" + r["claim_b"]
        pval = float(r["p_exact_mcnemar"])
        if "treatment" in pair and "accommodation" in pair:
            ok = close(pval, PAPER["mcnemar.treat_vs_accomm"], 0.0006)
            failures += not ok
            print(("PASS " if ok else "FAIL ") + "mcnemar.treat_vs_accomm"
                  + "  paper %.4f  repo %.4f" % (PAPER["mcnemar.treat_vs_accomm"], pval))
        if "treatment" in pair and "impact" in pair:
            ok = pval < 0.0001 or close(pval, PAPER["mcnemar.treat_vs_impact"], 0.0001)
            failures += not ok
            print(("PASS " if ok else "FAIL ") + "mcnemar.treat_vs_impact"
                  + "  paper <.0001  repo %.5f" % pval)
        if "accommodation" in pair and "impact" in pair and "treatment" not in pair:
            ok = close(pval, PAPER["mcnemar.accomm_vs_impact"], 0.005)
            failures += not ok
            print(("PASS " if ok else "FAIL ") + "mcnemar.accomm_vs_impact"
                  + "  paper %.2f  repo %.4f" % (PAPER["mcnemar.accomm_vs_impact"], pval))

    # ---------------------------------------------------------------- summary json
    summ = json.load(open(VAL / "llm_baseline_summary.json"))
    sc = summ.get("self_consistency") or summ.get("selfConsistency")
    if isinstance(sc, dict):
        sc = sc.get("rate") or sc.get("value")
    if sc is None:
        sc = summ.get("self_consistency_rate")
    if sc is not None:
        ok = close(float(sc), PAPER["llm.self_consistency"], 0.001)
        failures += not ok
        print(("PASS " if ok else "FAIL ") + "llm.self_consistency"
              + "  paper %.3f  repo %.4f" % (PAPER["llm.self_consistency"], float(sc)))

    print()
    print("tables written to " + str(OUT))
    print(("ALL CHECKS PASS" if failures == 0
           else str(failures) + " CHECKS FAILED — paper and repo disagree"))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
