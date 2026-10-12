"""
Unit tests for TurnaroundScorer: zero lookahead bias with 45/90 day filing lags,
4-pillar proxy framework (Rev inflection, EBIT recovery, Solvency, Valuation).
"""
from datetime import date
import pytest

from src.screening.turnaround_scorer import TurnaroundScorer, PITFundamentalStore
from src.models.schemas import PITFinancialStatement


def test_zero_lookahead_filing_date_cutoff():
    """
    Verifies that a quarterly report filed on 2003-05-13 is strictly NOT visible
    when evaluating on 2003-05-10, guaranteeing zero lookahead bias.
    """
    store = PITFundamentalStore.from_seed_file()
    
    # Check AAPL statements visible before and after May 13, 2003
    pre_filing = store.get_statements_observable_at("AAPL", "2003-05-10")
    post_filing = store.get_statements_observable_at("AAPL", "2003-05-15")

    # On May 10, only Q4 2002 (filed Dec 2002) and Q1 2003 (filed Feb 2003) exist
    assert len(pre_filing) == 2
    # On May 15, Q2 2003 is filed and observable
    assert len(post_filing) == 3
    assert post_filing[-1].fiscal_period_end == date(2003, 3, 29)
    assert post_filing[-1].filing_date == date(2003, 5, 13)


def test_turnaround_score_inflection_detection(turnaround_scorer):
    """
    Verifies that Apple's turnaround in early 2003 produces a marked increase
    in the composite turnaround score after the Q2 2003 inflection was filed.
    """
    score_pre, breakdown_pre = turnaround_scorer.score_candidate("AAPL", "2003-03-01")
    score_post, breakdown_post = turnaround_scorer.score_candidate("AAPL", "2003-06-01")

    # Post turnaround score should reflect higher revenue inflection and EBIT recovery
    assert score_post > score_pre
    assert breakdown_post["pillar1_rev_inflection"] > breakdown_pre["pillar1_rev_inflection"]
    assert breakdown_post["pillar2_opm_recovery"] > breakdown_pre["pillar2_opm_recovery"]


def test_solvency_pillar_penalizes_distressed_companies(turnaround_scorer):
    """
    Verifies that highly leveraged, cash-burning companies (e.g. LEH in 2008)
    receive low solvency scores.
    """
    score, breakdown = turnaround_scorer.score_candidate("LEH", "2008-08-01")
    assert breakdown["pillar3_solvency"] < 0.25
    assert score < 0.50


def test_conservative_neutral_fallback_when_no_data(turnaround_scorer):
    """Verifies that unknown tickers without loaded fundamentals get neutral-conservative scores."""
    score, breakdown = turnaround_scorer.score_candidate("UNKNOWN_TICKER", "2020-01-01")
    assert score == 0.50
    assert breakdown["statement_count"] == 0
