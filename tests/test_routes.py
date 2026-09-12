"""Integration tests for the FastAPI routes in app/backend/routes.py.

These hit the app through TestClient and a real (SQLite, see conftest.py)
database session, exercising request validation, hard filters, all three
ranking methods, and custom-criterion resolution end to end.
"""

from app.backend import mcda


# ---------------------------------------------------------------------------
# Static/reference endpoints
# ---------------------------------------------------------------------------

def test_index_page_returns_200_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert response.headers["cache-control"] == "no-store"


def test_results_page_returns_200_html(client):
    response = client.get("/results")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_list_criteria_matches_registry(client):
    response = client.get("/api/criteria")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(mcda.CRITERIA_REGISTRY)
    fields = {c["field"] for c in body}
    assert fields == set(mcda.ALL_CRITERIA)
    carplay = next(c for c in body if c["field"] == "carplay_support")
    assert carplay["checkbox"] is True
    assert "carplay" in carplay["synonyms"]


# ---------------------------------------------------------------------------
# /api/models
# ---------------------------------------------------------------------------

def test_list_models_empty_db(client):
    response = client.get("/api/models")
    assert response.status_code == 200
    assert response.json() == []


def test_list_models_returns_seeded_cars_with_spec(client, seed_two_cars):
    response = client.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    names = {m["model"] for m in body}
    assert names == {"FastModel", "SlowModel"}
    fast = next(m for m in body if m["model"] == "FastModel")
    assert fast["manufacturer"] == "TestMake"
    assert fast["spec"]["carplay_support"] is False
    assert fast["spec"]["display_size_in"] == 15.0


def test_list_models_includes_car_without_spec_as_null(client, seed_car_without_spec):
    response = client.get("/api/models")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["spec"] is None


# ---------------------------------------------------------------------------
# POST /rank - validation
# ---------------------------------------------------------------------------

def test_rank_requires_at_least_one_criterion(client, seed_two_cars):
    response = client.post("/rank", json={"method": "wsm", "criteria": {"features": []}})
    assert response.status_code == 400


def test_rank_unmatched_custom_criterion_with_no_features_is_400(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": [], "custom_criterion": "totally made up thing xyz"},
    })
    assert response.status_code == 400


def test_rank_rejects_unknown_method(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "not_a_real_method",
        "criteria": {"features": ["carplay_support"]},
    })
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /rank - ranking behavior
# ---------------------------------------------------------------------------

def test_rank_wsm_orders_fast_car_first(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score", "startup_time_sec", "display_size_in"]},
    })
    assert response.status_code == 200
    body = response.json()
    assert body["total_matches"] == 2
    assert [r["model_name"] for r in body["results"]] == ["FastModel", "SlowModel"]
    assert body["results"][0]["rank"] == 1
    assert body["results"][0]["score"] >= body["results"][1]["score"]


def test_rank_topsis_orders_fast_car_first(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "topsis",
        "criteria": {"features": ["ease_of_use_score", "startup_time_sec", "display_size_in"]},
    })
    assert response.status_code == 200
    body = response.json()
    assert [r["model_name"] for r in body["results"]] == ["FastModel", "SlowModel"]


def test_rank_ahp_includes_consistency_note(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "ahp",
        "criteria": {"features": ["ease_of_use_score", "startup_time_sec"]},
    })
    assert response.status_code == 200
    body = response.json()
    assert body["consistency_note"] is not None
    assert "Consistency Ratio" in body["consistency_note"]
    assert [r["model_name"] for r in body["results"]] == ["FastModel", "SlowModel"]


def test_rank_no_cars_in_db_returns_empty_results(client):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["carplay_support"]},
    })
    assert response.status_code == 200
    body = response.json()
    assert body["results"] == []


def test_rank_ignores_cars_without_infotainment_spec(client, seed_two_cars, seed_car_without_spec):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
    })
    assert response.status_code == 200
    body = response.json()
    assert body["total_matches"] == 2
    assert all(r["model_name"] != "NoSpecModel" for r in body["results"])


def test_rank_matched_criteria_breakdown_reflects_boolean_fields(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["carplay_support"]},
    })
    body = response.json()
    fast = next(r for r in body["results"] if r["model_name"] == "FastModel")
    slow = next(r for r in body["results"] if r["model_name"] == "SlowModel")
    assert fast["matched_criteria"][0]["satisfied"] is False
    assert slow["matched_criteria"][0]["satisfied"] is True


# ---------------------------------------------------------------------------
# POST /rank - hard filters
# ---------------------------------------------------------------------------

def test_rank_hard_filter_require_carplay_excludes_non_matching(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
        "filters": {"require_carplay": True},
    })
    assert response.status_code == 200
    body = response.json()
    assert [r["model_name"] for r in body["results"]] == ["SlowModel"]
    assert "CarPlay" in body["active_hard_filters"]


def test_rank_hard_filter_min_display_size(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
        "filters": {"min_display_size_in": 10.0},
    })
    body = response.json()
    assert [r["model_name"] for r in body["results"]] == ["FastModel"]


def test_rank_hard_filter_by_manufacturer(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
        "filters": {"manufacturers": ["NonExistentMake"]},
    })
    body = response.json()
    assert body["results"] == []


def test_rank_hard_filters_can_exclude_everything(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
        "filters": {"require_physical_buttons": True, "require_carplay": True, "min_display_size_in": 14.0},
    })
    body = response.json()
    # SlowModel has buttons+carplay but a small (8") screen; FastModel has a
    # big screen but no buttons/carplay - no car satisfies all three at once.
    assert body["results"] == []


# ---------------------------------------------------------------------------
# POST /rank - custom criteria
# ---------------------------------------------------------------------------

def test_rank_custom_criterion_resolves_and_is_applied(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": [], "custom_criterion": "bluetooth"},
    })
    assert response.status_code == 200
    body = response.json()
    assert len(body["custom_criterion_results"]) == 1
    assert body["custom_criterion_results"][0]["matched_field"] == "multi_bluetooth"
    assert len(body["results"]) == 2


def test_rank_custom_criterion_no_match_reported(client, seed_two_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"], "custom_criterion": "totally made up thing xyz"},
    })
    assert response.status_code == 200
    body = response.json()
    assert body["custom_criterion_results"][0]["matched_field"] is None
    assert body["custom_criterion_results"][0]["matched_label"] is None


# ---------------------------------------------------------------------------
# POST /rank - limit / result cap
# ---------------------------------------------------------------------------

def test_rank_default_limit_caps_results_at_ten(client, seed_many_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
    })
    body = response.json()
    assert body["total_matches"] == 12
    assert len(body["results"]) == 10
    # Highest ease_of_use_score (Model11) should be first.
    assert body["results"][0]["model_name"] == "Model11"


def test_rank_limit_zero_returns_all_matches(client, seed_many_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
        "limit": 0,
    })
    body = response.json()
    assert len(body["results"]) == 12


def test_rank_explicit_limit_is_respected(client, seed_many_cars):
    response = client.post("/rank", json={
        "method": "wsm",
        "criteria": {"features": ["ease_of_use_score"]},
        "limit": 3,
    })
    body = response.json()
    assert len(body["results"]) == 3
    assert body["total_matches"] == 12
