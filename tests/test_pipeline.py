import sys
import json
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fha import reference as ref
from fha.classify import rule_is_fha
from fha.extract import extract_case, extract_outcomes
from fha import config, synth, feii, econometrics as ec
from fha.extract import extract_corpus


def test_court_to_circuit():
    assert ref.court_to_circuit("cand") == "9"
    assert ref.court_to_circuit("nysd") == "2"
    assert ref.court_to_circuit("ca5") == "5"
    assert ref.court_to_circuit("scotus") == "SCOTUS"
    assert ref.court_to_circuit("txctapp13") is None
    assert ref.court_level("ca9") == "appellate"
    assert ref.court_level("flsd") == "district"


def test_fha_citation_detection():
    assert ref.find_fha_citations("violation of 42 U.S.C. § 3604(a)") == ["3604"]
    assert "3617" in ref.find_fha_citations("see 42 U.S.C. 3617 and 3604")

    assert ref.mentions_fha("the FHA-insured mortgage was denied") is False
    assert ref.mentions_fha("brought under the Fair Housing Act") is True


def test_rule_is_fha():
    pos = {"text": "Plaintiff sues under the Fair Housing Act, 42 U.S.C. 3604, "
                   "alleging disparate impact and refusal to rent.",
           "nature_of_suit": "443"}
    neg = {"text": "This is a contract dispute about an FHA-insured loan.",
           "nature_of_suit": "190"}
    assert rule_is_fha(pos) is True
    assert rule_is_fha(neg) is False


def test_extract_case_claims_and_outcome():
    rec = {"cluster_id": 1, "circuit": "9", "court_level": "district", "year": 2016,
           "text": ("Plaintiff, who is handicapped, seeks a reasonable accommodation "
                    "under 42 U.S.C. 3604(f). Applying disparate impact analysis and "
                    "the 24 C.F.R. 100.500 burden-shifting framework, the Court grants "
                    "plaintiff's motion for summary judgment. Judgment is entered in "
                    "favor of the plaintiff. The Court orders permanent injunctive relief.")}
    row = extract_case(rec)
    assert row["claim_reasonable_accommodation"] == 1
    assert row["claim_disparate_impact"] == 1
    assert row["remedy_injunction"] == 1
    assert row["plaintiff_win"] == 1
    assert row["burden_framework"] == "hud_three_step"
    assert 0 <= row["doctrinal_strictness"] <= 1


def test_outcome_evidence_uses_full_opinion_offsets():
    cue = "Judgment is entered in favor of the plaintiff."
    text = cue + " neutral background" * 300
    result = extract_outcomes(text)
    evidence = json.loads(result["outcome_evidence"])["plaintiff"]
    assert result["outcome_cue"] == 1
    assert evidence
    assert evidence[0]["start"] == 0
    assert text[evidence[0]["start"]:evidence[0]["end"]] == evidence[0]["text"]


def test_twfe_recovers_true_beta():
    truth = synth.generate(n_cases=4000, seed=11)
    stored = json.loads((config.PROCESSED / "_synth_truth.json").read_text())
    assert stored["corpus"] == "data/raw/synthetic_corpus.jsonl"
    assert stored["housing_panel"] == "data/external/synthetic_housing_panel.csv"
    hp = pd.read_csv(truth["housing_panel"])
    recs = [json.loads(l) for l in open(truth["corpus"])]
    feat = extract_corpus(recs)
    pf = feii.aggregate(feat, unit="circuit")
    panel = ec.build_panel(pf, hp).rename(columns={"_latent_strictness": "latent"})
    res = ec.twfe(panel, y="dissimilarity_index", x="latent")
    assert res["coef"] == pytest.approx(truth["BETA_TRUE"], abs=0.05)
    assert res["p"] < 0.01


def test_feii_is_standardized():
    truth = synth.generate(n_cases=2000, seed=3)
    recs = [json.loads(l) for l in open(truth["corpus"])]
    pf = feii.aggregate(extract_corpus(recs), unit="circuit")
    assert abs(pf["FEII"].mean()) < 1e-6
    assert "outcome_cue_rate" in pf and "remedy_cue_intensity" in pf
