"""Build paper audit tables and verify every mapped quantitative claim.

The paper contains prose as well as tables, so this script checks a named claim
map rather than trying to scrape numbers from TeX. It fails if a declared claim
is not checked, which prevents the old false-positive ``ALL CHECKS PASS`` state.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VAL = ROOT / "outputs" / "paper" / "validation"
ROBUST = ROOT / "outputs" / "validation"
OUT = ROOT / "outputs" / "paper_tables"

PAPER = {
    "corpus.candidates": 937,
    "corpus.canonical": 757,
    "corpus.full_text": 751,
    "corpus.substantive": 417,
    "gold.overlap": 93,
    "gold.second_pass": 30,
    "gold.framework_accuracy": 0.774,
    "gold.holding_precision": 0.712,
    "gold.holding_recall": 0.587,
    "gold.holding_f1": 0.643,
    "gold.decisive_n": 37,
    "gold.decisive_accuracy": 0.811,
    "gold.claims_kappa_second": 0.899,
    "gold.framework_kappa_second": 0.864,
    "gold.winner_kappa_second": 0.726,
    "gold.corpus_outcome_n": 53,
    "gold.corpus_outcome_rate": 0.358,
    "gold.corpus_outcome_ci_lo": 0.243,
    "gold.corpus_outcome_ci_hi": 0.493,
    "llm.n_passes": 3,
    "llm.overlap": 93,
    "llm.self_consistency": 0.9827,
    "llm.claim_decisions": 1215,
    "llm.framework_regex": 0.774,
    "llm.framework_llm": 0.935,
    "llm.requested_passes": 729,
    "llm.returned_passes": 729,
    "random.seed": 20260720,
    "random.frame": 658,
    "random.drawn": 150,
    "random.substantive": 76,
    "prev.treatment": 0.461,
    "prev.accommodation": 0.211,
    "prev.impact": 0.132,
    "prev.refusal": 0.171,
    "prev.zoning": 0.079,
    "corrected.treatment": 0.473,
    "corrected.accommodation": 0.312,
    "corrected.impact": 0.125,
    "corrected.refusal": 0.283,
    "corrected.zoning": 0.094,
    "mcnemar.treat_vs_accomm": 0.0066090,
    "mcnemar.treat_vs_impact": 0.000005,
    "mcnemar.accomm_vs_impact": 0.2862790,
    "power.at_n76": 0.183,
    "power.n_for_80": 383,
    "power.draws_for_80": 756,
    "power.assurance": 0.633,
    "power.discordant": 22,
    "twfe.n": 8,
    "negation.max_shift": 0.024,
    "negation.micro_precision": 0.760274,
    "negation.micro_recall": 0.750000,
    "negation.micro_f1": 0.755102,
    "circuit.impact_min": 0.079,
    "circuit.impact_max": 0.537,
    "circuit.treatment_min": 0.107,
    "circuit.treatment_max": 0.610,
    "circuit.impact_chi2": 30.5,
    "circuit.impact_p": 0.0007,
    "circuit.impact_v": 0.27,
    "circuit.treatment_chi2": 27.6,
    "circuit.treatment_p": 0.0021,
    "schelling.replications": 40,
    "schelling.seed": 20260715,
    "schelling.low_access": 0.778,
    "schelling.low_wide": 0.723,
    "schelling.mid_access": 0.852,
    "schelling.mid_wide": 0.851,
    "schelling.high_access": 0.916,
    "schelling.high_wide": 0.918,
}

GOLD_CLAIMS = {
    "claim_disparate_treatment": (0.907, 0.722, 0.804, 0.596),
    "claim_disparate_impact": (0.407, 0.917, 0.564, 0.469),
    "claim_refusal_rent_sell": (0.731, 0.613, 0.667, 0.521),
    "claim_reasonable_accommodation": (0.829, 0.944, 0.883, 0.801),
    "claim_zoning_exclusionary": (0.800, 0.800, 0.800, 0.762),
    "claims_micro": (0.757, 0.777, 0.767, 0.656),
}

LLM_CLAIMS = {
    "claim_disparate_treatment": (0.867, 0.963, 0.912, 0.108),
    "claim_disparate_impact": (1.000, 0.917, 0.957, 0.393),
    "claim_refusal_rent_sell": (0.792, 0.613, 0.691, 0.024),
    "claim_reasonable_accommodation": (1.000, 0.917, 0.957, 0.074),
    "claim_zoning_exclusionary": (0.833, 1.000, 0.909, 0.109),
    "claims_micro": (0.890, 0.878, 0.884, 0.117),
}

LABELS = {
    "claim_disparate_treatment": "Disparate treatment",
    "claim_disparate_impact": "Disparate impact",
    "claim_refusal_rent_sell": "Refusal or steering",
    "claim_reasonable_accommodation": "Reasonable accommodation",
    "claim_zoning_exclusionary": "Exclusionary zoning",
    "claims_micro": "Micro average",
}

TEX_LABELS = {
    "claim_disparate_treatment": r"Disp.\ treatment",
    "claim_disparate_impact": r"Disp.\ impact",
    "claim_refusal_rent_sell": "Refusal/steering",
    "claim_reasonable_accommodation": r"Reas.\ accomm.",
    "claim_zoning_exclusionary": r"Excl.\ zoning",
    "claims_micro": "Micro average",
}


def compact_metric(value):
    if math.isclose(value, 1.0, abs_tol=.0005):
        return "1.00"
    text = f"{value:.3f}"
    return text[1:] if text.startswith("0.") else text


def read_json(path):
    try:
        return json.load(path.open())
    except FileNotFoundError:
        raise SystemExit(f"required output missing: {path}; run `make reproduce` first")


def read_csv(path):
    try:
        return list(csv.DictReader(path.open()))
    except FileNotFoundError:
        raise SystemExit(f"required output missing: {path}; run `make reproduce` first")


def count_jsonl(path):
    return sum(1 for line in path.open() if line.strip())


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    checked = set()
    audit = []
    failures = 0

    def expect(key, got, tol=0.0):
        nonlocal failures
        if key not in PAPER:
            raise RuntimeError(f"undeclared paper claim: {key}")
        expected = PAPER[key]
        ok = math.isclose(float(got), float(expected), rel_tol=0.0, abs_tol=tol)
        checked.add(key)
        failures += int(not ok)
        audit.append({"claim": key, "expected": expected, "actual": got,
                      "tolerance": tol, "passed": ok})
        print(f"{'PASS' if ok else 'FAIL'} {key}: paper={expected} repo={got}")

    pipeline = read_json(ROOT / "outputs/paper/pipeline_summary.json")
    canonical = count_jsonl(ROOT / "data/raw/bulk_fha_cases.jsonl")
    expect("corpus.canonical", canonical)
    expect("corpus.candidates", canonical +
           count_jsonl(ROOT / "data/validation/excluded_non_nos443.jsonl"))
    expect("corpus.full_text", count_jsonl(ROOT / "data/processed/paper_corpus.jsonl"))
    expect("corpus.substantive", pipeline["identification"]["n_rule_positive"])
    expect("twfe.n", pipeline["twfe"]["n"])

    gold = read_json(ROBUST / "goldset_metrics.json")
    expect("gold.overlap", gold["n_cases"])
    expect("gold.second_pass", gold["inter_annotator"]["n_double_coded"])
    expect("gold.framework_accuracy", gold["framework_accuracy"], .0005)
    holding = gold["holding_detection"]
    expect("gold.holding_precision", holding["precision"], .0005)
    expect("gold.holding_recall", holding["recall"], .0005)
    expect("gold.holding_f1", holding["f1"], .0005)
    decisive = gold["winner_on_machine_holdings"]
    expect("gold.decisive_n", decisive["n_both_decisive"])
    expect("gold.decisive_accuracy", decisive["binary_accuracy"], .0005)
    second = gold["inter_annotator"]
    expect("gold.claims_kappa_second", second["claims_kappa"], .0005)
    expect("gold.framework_kappa_second", second["framework_kappa"], .0005)
    expect("gold.winner_kappa_second", second["winner_kappa_4way"], .0005)
    outcome = gold["corpus_win_rate"]
    expect("gold.corpus_outcome_n", outcome["n"])
    expect("gold.corpus_outcome_rate", outcome["rate"], .0005)
    expect("gold.corpus_outcome_ci_lo", outcome["wilson95"][0], .0005)
    expect("gold.corpus_outcome_ci_hi", outcome["wilson95"][1], .0005)

    gold_rows = {row["variable"]: row for row in read_csv(
        ROBUST / "goldset_precision_recall.csv")}
    lines = ["| Construct | Precision | Recall | F1 | Kappa |", "|---|---:|---:|---:|---:|"]
    tex_lines = []
    for name, expected in GOLD_CLAIMS.items():
        if name == "claims_micro":
            tex_lines.append(r"\midrule")
        row = gold_rows[name]
        actual = tuple(float(row[key]) for key in ("precision", "recall", "f1", "kappa"))
        if any(not math.isclose(a, e, abs_tol=.0005) for a, e in zip(actual, expected)):
            failures += 1
            print(f"FAIL table1.{name}: paper={expected} repo={actual}")
        lines.append(f"| {LABELS[name]} | {actual[0]:.3f} | {actual[1]:.3f} | "
                     f"{actual[2]:.3f} | {actual[3]:.3f} |")
        tex_lines.append(
            f"{TEX_LABELS[name]} & {actual[0]:.3f} & {actual[1]:.3f} & "
            f"{actual[2]:.3f} & {actual[3]:.2f} " + r"\\"
        )
    (OUT / "table1_gold.md").write_text("\n".join(lines) + "\n")
    tex_lines.append(r"\bottomrule")
    (OUT / "table1_gold_rows.tex").write_text("\n".join(tex_lines) + "\n")

    llm = read_json(VAL / "llm_baseline_summary.json")
    expect("llm.n_passes", llm["n_passes"])
    expect("llm.overlap", llm["n_cases"])
    expect("llm.self_consistency", llm["self_consistency"]["fraction"], .00005)
    expect("llm.claim_decisions", llm["self_consistency"]["n_decisions"])
    expect("llm.framework_regex", llm["framework_accuracy_regex"], .0005)
    expect("llm.framework_llm", llm["framework_accuracy_llm"], .0005)
    raw_llm = read_json(ROOT / "data/validation/llm_labels_3pass.json")
    expect("llm.requested_passes", (93 + 150) * raw_llm["n_passes"])
    expect("llm.returned_passes", len(raw_llm["labels"]))

    llm_rows = {row["variable"]: row for row in read_csv(VAL / "llm_vs_regex.csv")}
    lines = ["| Construct | Regex P/R/F1 | LLM P/R/F1 | dF1 |", "|---|---|---|---:|"]
    tex_lines = []
    for name, expected in LLM_CLAIMS.items():
        if name == "claims_micro":
            tex_lines.append(r"\midrule")
        row = llm_rows[name]
        regex_actual = tuple(float(row[key]) for key in
                             ("regex_precision", "regex_recall", "regex_f1"))
        regex_expected = GOLD_CLAIMS[name][:3]
        actual = tuple(float(row[key]) for key in
                       ("llm_precision", "llm_recall", "llm_f1", "delta_f1"))
        if (any(not math.isclose(a, e, abs_tol=.0005)
                for a, e in zip(regex_actual, regex_expected)) or
                any(not math.isclose(a, e, abs_tol=.0005)
                    for a, e in zip(actual, expected))):
            failures += 1
            print(f"FAIL table2.{name}: regex={regex_actual} llm={actual}")
        lines.append("| " + LABELS[name] + " | "
                     + "/".join(f"{float(row[k]):.3f}" for k in
                                 ("regex_precision", "regex_recall", "regex_f1"))
                     + " | " + "/".join(f"{float(row[k]):.3f}" for k in
                                         ("llm_precision", "llm_recall", "llm_f1"))
                     + f" | {float(row['delta_f1']):+.3f} |")
        delta = float(row["delta_f1"])
        sign = "$+$" if delta >= 0 else "$-$"
        tex_lines.append(
            f"{TEX_LABELS[name]} & {'/'.join(compact_metric(v) for v in regex_actual)} & "
            f"{'/'.join(compact_metric(v) for v in actual[:3])} & "
            f"{sign}{compact_metric(abs(delta))} " + r"\\"
        )
    framework_regex = float(llm["framework_accuracy_regex"])
    framework_llm = float(llm["framework_accuracy_llm"])
    tex_lines.append(
        "Framework acc. & "
        f"\\multicolumn{{1}}{{c}}{{{compact_metric(framework_regex)}}} & "
        f"\\multicolumn{{1}}{{c}}{{{compact_metric(framework_llm)}}} & "
        f"$+${compact_metric(framework_llm - framework_regex)} " + r"\\"
    )
    (OUT / "table2_llm_vs_regex.md").write_text("\n".join(lines) + "\n")
    tex_lines.append(r"\bottomrule")
    (OUT / "table2_llm_rows.tex").write_text("\n".join(tex_lines) + "\n")

    summary = read_json(VAL / "prevalence_summary.json")
    expect("random.seed", summary["seed"])
    expect("random.frame", summary["frame_size"])
    expect("random.drawn", summary["n_drawn"])
    expect("random.substantive", summary["n_substantive"])
    power = summary["power"]
    expect("power.at_n76", power["power_at_observed"], .0005)
    expect("power.n_for_80", power["p80"]["n_substantive"])
    expect("power.draws_for_80", power["p80"]["n_draws"])
    expect("power.assurance", power["assurance_at_80"], .005)
    expect("power.discordant", power["n10"] + power["n01"])

    prev = read_csv(VAL / "prevalence_random.csv")
    pmap = {row["construct"]: row for row in prev}
    names = [("disparate_treatment", "treatment"),
             ("reasonable_accommodation", "accommodation"),
             ("disparate_impact", "impact"), ("refusal_rent_sell", "refusal"),
             ("zoning_exclusionary", "zoning")]
    lines = ["| Construct | LLM share | Regex share | Corrected |", "|---|---:|---:|---:|"]
    for construct, short in names:
        row = pmap[construct]
        expect(f"prev.{short}", float(row["llm_share"]), .0005)
        expect(f"corrected.{short}", float(row["regex_share_417_corrected"]), .0005)
        lines.append(f"| {construct} | {float(row['llm_share']):.3f} | "
                     f"{float(row['regex_share_417']):.3f} | "
                     f"{float(row['regex_share_417_corrected']):.3f} |")
    (OUT / "prevalence.md").write_text("\n".join(lines) + "\n")

    paired = read_csv(VAL / "paired_tests.csv")
    for row in paired:
        pair = {row["claim_a"], row["claim_b"]}
        if pair == {"disparate_treatment", "reasonable_accommodation"}:
            expect("mcnemar.treat_vs_accomm", float(row["p_exact_mcnemar"]), .0000005)
        elif pair == {"disparate_treatment", "disparate_impact"}:
            expect("mcnemar.treat_vs_impact", float(row["p_exact_mcnemar"]), .0000005)
        elif pair == {"reasonable_accommodation", "disparate_impact"}:
            expect("mcnemar.accomm_vs_impact", float(row["p_exact_mcnemar"]), .0000005)

    negation = read_json(ROBUST / "negation_sensitivity.json")
    expect("negation.max_shift", max(abs(v) for v in negation["delta_claim_shares_pp"].values()))
    neg_gold = negation["gold_micro"]["negation"]
    expect("negation.micro_precision", neg_gold["precision"], .0000005)
    expect("negation.micro_recall", neg_gold["recall"], .0000005)
    expect("negation.micro_f1", neg_gold["f1"], .0000005)
    lines = ["| Indicator | Change (percentage points) |", "|---|---:|"]
    for name, value in sorted(negation["delta_claim_shares_pp"].items(),
                              key=lambda item: item[1], reverse=True):
        lines.append(f"| {name} | {100 * value:+.2f} |")
    (OUT / "negation.md").write_text("\n".join(lines) + "\n")

    circuits = read_csv(VAL / "circuit_prevalence.csv")
    impact = [float(row["disparate_impact"]) for row in circuits]
    treatment = [float(row["disparate_treatment"]) for row in circuits]
    expect("circuit.impact_min", min(impact), .0005)
    expect("circuit.impact_max", max(impact), .0005)
    expect("circuit.treatment_min", min(treatment), .0005)
    expect("circuit.treatment_max", max(treatment), .0005)
    split = read_json(VAL / "circuit_split.json")
    expect("circuit.impact_chi2", split["disparate_impact"]["chi2"], .05)
    expect("circuit.impact_p", split["disparate_impact"]["p"], .00005)
    expect("circuit.impact_v", split["disparate_impact"]["cramers_v"], .005)
    expect("circuit.treatment_chi2", split["disparate_treatment"]["chi2"], .05)
    expect("circuit.treatment_p", split["disparate_treatment"]["p"], .00005)
    fields = list(circuits[0])
    lines = ["| " + " | ".join(fields) + " |", "|" + "---|" * len(fields)]
    lines += ["| " + " | ".join(row[field] for field in fields) + " |" for row in circuits]
    (OUT / "circuits.md").write_text("\n".join(lines) + "\n")

    scenarios = read_json(ROOT / "outputs/schelling_scenarios.json")
    expect("schelling.replications", scenarios["meta"]["replications"])
    expect("schelling.seed", scenarios["meta"]["seed"])
    phase = {(row["tolerance"], row["access"]): row["segregation_mean"]
             for row in scenarios["phase_sweep"]}
    for tolerance, prefix in ((.2, "low"), (.3, "mid"), (.45, "high")):
        expect(f"schelling.{prefix}_access", phase[(tolerance, .15)], .0005)
        expect(f"schelling.{prefix}_wide", phase[(tolerance, .85)], .0005)

    missing = sorted(set(PAPER) - checked)
    if missing:
        failures += len(missing)
        print("FAIL unchecked declared claims: " + ", ".join(missing))
    (OUT / "claim_audit.json").write_text(json.dumps({
        "declared": len(PAPER), "checked": len(checked), "failures": failures,
        "claims": audit, "table_checks": len(GOLD_CLAIMS) + len(LLM_CLAIMS) + 1,
    }, indent=2) + "\n")
    print(f"\nchecked {len(checked)}/{len(PAPER)} declared claims and "
          f"{len(GOLD_CLAIMS) + len(LLM_CLAIMS) + 1} table rows")
    print(f"tables written to {OUT}")
    print("ALL CHECKS PASS" if failures == 0 else f"{failures} CHECKS FAILED")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
