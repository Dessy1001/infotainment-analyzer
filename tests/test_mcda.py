"""Unit tests for the pure-Python MCDA logic in app/backend/mcda.py.

No database or HTTP involved - these exercise the ranking math and the
criterion name-matching directly.
"""

from typing import List

import numpy as np
import pytest

from app.backend import mcda
from app.backend.mcda import SpecDict


# ---------------------------------------------------------------------------
# resolve_custom_criterion / resolve_custom_criteria
# ---------------------------------------------------------------------------

class TestResolveCustomCriterion:
    def test_matches_exact_label(self):
        match = mcda.resolve_custom_criterion("Поддръжка на Apple CarPlay")
        assert match is not None
        assert match["field"] == "carplay_support"

    def test_matches_synonym_case_insensitive(self):
        match = mcda.resolve_custom_criterion("CARPLAY")
        assert match is not None
        assert match["field"] == "carplay_support"

    def test_matches_bulgarian_synonym(self):
        match = mcda.resolve_custom_criterion("гласови команди")
        assert match is not None
        assert match["field"] == "voice_control"

    def test_no_match_for_unrelated_text(self):
        assert mcda.resolve_custom_criterion("напълно измислен критерий xyz") is None

    def test_none_and_empty_input(self):
        assert mcda.resolve_custom_criterion(None) is None
        assert mcda.resolve_custom_criterion("") is None
        assert mcda.resolve_custom_criterion("   ") is None

    def test_matches_via_substring_of_a_longer_synonym(self):
        # resolve_custom_criterion matches whenever the normalized input is a
        # substring of a candidate synonym (not just whole-word), so even a
        # short fragment of a synonym counts as a match - e.g. "google" is
        # contained in the "google assistant" synonym for smart_home_compat.
        match = mcda.resolve_custom_criterion("google")
        assert match is not None
        assert match["field"] == "smart_home_compat"


class TestResolveCustomCriteria:
    def test_splits_on_comma_and_semicolon(self):
        results = mcda.resolve_custom_criteria("carplay, android auto; bluetooth")
        assert [r["requested"] for r in results] == ["carplay", "android auto", "bluetooth"]
        assert all(r["match"] is not None for r in results)

    def test_empty_and_none_return_empty_list(self):
        assert mcda.resolve_custom_criteria(None) == []
        assert mcda.resolve_custom_criteria("") == []

    def test_blank_terms_are_dropped(self):
        results = mcda.resolve_custom_criteria("carplay,, ;  ")
        assert [r["requested"] for r in results] == ["carplay"]


# ---------------------------------------------------------------------------
# build_decision_matrix
# ---------------------------------------------------------------------------

def test_build_decision_matrix_converts_booleans_and_orders_columns():
    specs: List[SpecDict] = [
        {"carplay_support": True, "display_size_in": 12.0},
        {"carplay_support": False, "display_size_in": 10.0},
    ]
    matrix, criteria = mcda.build_decision_matrix(specs)

    assert criteria == mcda.ALL_CRITERIA
    assert matrix.shape == (2, len(mcda.ALL_CRITERIA))

    carplay_col = criteria.index("carplay_support")
    display_col = criteria.index("display_size_in")
    assert matrix[0, carplay_col] == 1.0
    assert matrix[1, carplay_col] == 0.0
    assert matrix[0, display_col] == 12.0
    assert matrix[1, display_col] == 10.0


def test_build_decision_matrix_defaults_missing_fields_to_zero():
    specs: List[SpecDict] = [{}]
    matrix = mcda.build_decision_matrix(specs)[0]
    assert np.all(matrix == 0.0)


# ---------------------------------------------------------------------------
# weights_from_input
# ---------------------------------------------------------------------------

class TestWeightsFromInput:
    def test_equal_weights_when_none_given(self):
        weights = mcda.weights_from_input(["carplay_support", "voice_control"])
        idx_carplay = mcda.ALL_CRITERIA.index("carplay_support")
        idx_voice = mcda.ALL_CRITERIA.index("voice_control")
        assert weights[idx_carplay] == pytest.approx(0.5)
        assert weights[idx_voice] == pytest.approx(0.5)
        assert weights.sum() == pytest.approx(1.0)

    def test_weights_normalized_to_sum_one(self):
        weights = mcda.weights_from_input(
            ["carplay_support", "voice_control"],
            {"carplay_support": 3.0, "voice_control": 1.0},
        )
        idx_carplay = mcda.ALL_CRITERIA.index("carplay_support")
        idx_voice = mcda.ALL_CRITERIA.index("voice_control")
        assert weights[idx_carplay] == pytest.approx(0.75)
        assert weights[idx_voice] == pytest.approx(0.25)

    def test_unknown_fields_are_ignored(self):
        weights = mcda.weights_from_input(["carplay_support", "not_a_real_field"])
        assert weights.sum() == pytest.approx(1.0)
        assert weights[mcda.ALL_CRITERIA.index("carplay_support")] == pytest.approx(1.0)

    def test_duplicate_fields_counted_once(self):
        weights = mcda.weights_from_input(["carplay_support", "carplay_support", "voice_control"])
        idx_carplay = mcda.ALL_CRITERIA.index("carplay_support")
        idx_voice = mcda.ALL_CRITERIA.index("voice_control")
        assert weights[idx_carplay] == pytest.approx(0.5)
        assert weights[idx_voice] == pytest.approx(0.5)

    def test_non_positive_or_invalid_weight_falls_back_to_one(self):
        # "not-a-number" is deliberately the wrong type here - weights_from_input
        # catches non-numeric values and falls back to 1.0, so this exercises
        # that path even though it violates the declared Dict[str, float] type.
        bad_raw_weights: dict[str, object] = {"carplay_support": -5.0, "voice_control": "not-a-number"}
        weights = mcda.weights_from_input(
            ["carplay_support", "voice_control"],
            bad_raw_weights,  # type: ignore[arg-type]
        )
        idx_carplay = mcda.ALL_CRITERIA.index("carplay_support")
        idx_voice = mcda.ALL_CRITERIA.index("voice_control")
        assert weights[idx_carplay] == pytest.approx(0.5)
        assert weights[idx_voice] == pytest.approx(0.5)

    def test_weight_capped_at_max(self):
        weights = mcda.weights_from_input(
            ["carplay_support", "voice_control"],
            {"carplay_support": 1000.0, "voice_control": 1.0},
        )
        idx_carplay = mcda.ALL_CRITERIA.index("carplay_support")
        expected = mcda.MAX_CRITERION_WEIGHT / (mcda.MAX_CRITERION_WEIGHT + 1.0)
        assert weights[idx_carplay] == pytest.approx(expected)

    def test_raises_when_no_valid_fields(self):
        with pytest.raises(ValueError):
            mcda.weights_from_input([])
        with pytest.raises(ValueError):
            mcda.weights_from_input(["not_a_real_field"])


# ---------------------------------------------------------------------------
# wsm_rank / _minmax_normalize
# ---------------------------------------------------------------------------

def test_wsm_rank_prefers_higher_benefit_and_lower_cost():
    # Two cars, two criteria: display_size_in (benefit) and startup_time_sec (cost).
    criteria = ["display_size_in", "startup_time_sec"]
    matrix = np.array([
        [15.0, 3.0],   # car A: bigger screen, faster startup -> should win
        [8.0, 12.0],   # car B: smaller screen, slower startup
    ])
    weights = np.array([0.5, 0.5])
    scores = mcda.wsm_rank(matrix, criteria, weights)
    assert scores[0] > scores[1]


def test_wsm_rank_constant_column_scores_as_full_marks():
    # When every row has the same value for a criterion, min-max span is 0;
    # the implementation treats that as maximally satisfied for all rows.
    criteria = ["display_size_in"]
    matrix = np.array([[10.0], [10.0]])
    weights = np.array([1.0])
    scores = mcda.wsm_rank(matrix, criteria, weights)
    assert scores == pytest.approx([1.0, 1.0])


def test_wsm_rank_scores_bounded_zero_to_one_for_single_weighted_criterion():
    criteria = ["display_size_in"]
    matrix = np.array([[5.0], [10.0], [15.0]])
    weights = np.array([1.0])
    scores = mcda.wsm_rank(matrix, criteria, weights)
    assert scores == pytest.approx([0.0, 0.5, 1.0])


# ---------------------------------------------------------------------------
# topsis_rank
# ---------------------------------------------------------------------------

def test_topsis_rank_prefers_higher_benefit_and_lower_cost():
    criteria = ["display_size_in", "startup_time_sec"]
    matrix = np.array([
        [15.0, 3.0],
        [8.0, 12.0],
    ])
    weights = np.array([0.5, 0.5])
    scores = mcda.topsis_rank(matrix, criteria, weights)
    assert scores[0] > scores[1]
    assert np.all((scores >= 0.0) & (scores <= 1.0))


# ---------------------------------------------------------------------------
# AHP: build_pairwise_matrix_from_weights / ahp_weights / ahp_rank
# ---------------------------------------------------------------------------

class TestAHP:
    def test_pairwise_matrix_diagonal_is_one_and_reciprocal(self):
        pcm, names = mcda.build_pairwise_matrix_from_weights({"a": 2.0, "b": 1.0})
        assert names == ["a", "b"]
        assert np.all(np.diag(pcm) == 1.0)
        i, j = names.index("a"), names.index("b")
        assert pcm[i, j] == pytest.approx(2.0)
        assert pcm[j, i] == pytest.approx(0.5)

    def test_ahp_weights_equal_input_gives_equal_output_and_zero_cr(self):
        pcm, _ = mcda.build_pairwise_matrix_from_weights({"a": 1.0, "b": 1.0, "c": 1.0})
        weights, cr = mcda.ahp_weights(pcm)
        assert weights.sum() == pytest.approx(1.0)
        assert weights == pytest.approx([1 / 3, 1 / 3, 1 / 3], abs=1e-6)
        assert cr == pytest.approx(0.0, abs=1e-6)

    def test_ahp_rank_returns_scores_and_consistency_ratio(self):
        # ahp_rank normalizes against the *full* ALL_CRITERIA-width matrix
        # (as build_decision_matrix produces), unlike wsm_rank/topsis_rank
        # which are given whatever columns the caller passes in.
        specs: List[SpecDict] = [
            {"display_size_in": 15.0, "startup_time_sec": 3.0},
            {"display_size_in": 8.0, "startup_time_sec": 12.0},
        ]
        matrix, criteria = mcda.build_decision_matrix(specs)
        scores, cr = mcda.ahp_rank(matrix, criteria, ["display_size_in", "startup_time_sec"])
        assert scores[0] > scores[1]
        assert cr == pytest.approx(0.0, abs=1e-6)

    def test_ahp_rank_raises_when_no_valid_fields(self):
        matrix = np.zeros((2, 2))
        with pytest.raises(ValueError):
            mcda.ahp_rank(matrix, ["display_size_in", "startup_time_sec"], [])


# ---------------------------------------------------------------------------
# criteria_breakdown
# ---------------------------------------------------------------------------

def test_criteria_breakdown_reports_boolean_and_numeric_fields():
    spec: SpecDict = {"carplay_support": True, "android_auto_support": False, "display_size_in": 12.5}
    breakdown = mcda.criteria_breakdown(spec, ["carplay_support", "android_auto_support", "display_size_in"])
    by_field = {b["field"]: b for b in breakdown}

    assert by_field["carplay_support"]["is_boolean"] is True
    assert by_field["carplay_support"]["satisfied"] is True
    assert by_field["carplay_support"]["value"] is None

    assert by_field["android_auto_support"]["is_boolean"] is True
    assert by_field["android_auto_support"]["satisfied"] is False

    assert by_field["display_size_in"]["is_boolean"] is False
    assert by_field["display_size_in"]["satisfied"] is True
    assert by_field["display_size_in"]["value"] == pytest.approx(12.5)


def test_criteria_breakdown_only_includes_selected_fields():
    spec: SpecDict = {"carplay_support": True, "voice_control": True}
    breakdown = mcda.criteria_breakdown(spec, ["carplay_support"])
    assert [b["field"] for b in breakdown] == ["carplay_support"]
