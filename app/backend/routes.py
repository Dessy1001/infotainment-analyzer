
import os
from typing import List, Optional, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from . import mcda
from .database import get_db
from .schemas import (
    CriterionMatch, CustomCriterionResult, HardFilters,
    RankRequest, RankedResult, RankResponse,
)
from ..models import CarModel, InfotainmentSpec

router = APIRouter()
templates = Jinja2Templates(directory="app/frontend/templates")

STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "static")


class CriterionListItem(TypedDict):
    field: str
    label: str
    description: str
    checkbox: bool
    synonyms: List[str]
    category: Optional[str]


class ModelListItem(TypedDict):
    id: int
    manufacturer: str
    model: str
    year: int
    powertrain: str
    spec: Optional[mcda.SpecDict]


def _asset_version() -> int:
    paths = [os.path.join(STATIC_DIR, "style.css")]
    js_dir = os.path.join(STATIC_DIR, "js")
    try:
        paths += [os.path.join(js_dir, f) for f in os.listdir(js_dir) if f.endswith(".js")]
    except OSError:
        pass
    mtimes = []
    for p in paths:
        try:
            mtimes.append(os.path.getmtime(p))
        except OSError:
            pass
    return int(max(mtimes)) if mtimes else 0


def _spec_to_dict(spec: InfotainmentSpec) -> mcda.SpecDict:
    return {
        "os_type": spec.os_type.value if spec.os_type else None,
        "display_size_in": spec.display_size_in,
        "physical_buttons_count": spec.physical_buttons_count,
        "voice_control": spec.voice_control,
        "ota_updates": spec.ota_updates,
        "carplay_support": spec.carplay_support,
        "android_auto_support": spec.android_auto_support,
        "personalization_profiles": spec.personalization_profiles,
        "builtin_navigation": spec.builtin_navigation,
        "smart_home_compat": spec.smart_home_compat,
        "multimodal_input": spec.multimodal_input,
        "multi_zone_displays": spec.multi_zone_displays,
        "multi_bluetooth": spec.multi_bluetooth,
        "charging_route_integration": spec.charging_route_integration,
        "startup_time_sec": spec.startup_time_sec,
        "reaction_time_ms": spec.reaction_time_ms,
        "avg_steps_to_task": spec.avg_steps_to_task,
        "ease_of_use_score": spec.ease_of_use_score,
        "ergonomics_score": spec.ergonomics_score,
        "safety_distraction_score": spec.safety_distraction_score,
    }


def _apply_hard_filters(cars: list[CarModel], filters: HardFilters) -> list[CarModel]:
    result: list[CarModel] = []
    for car in cars:
        s = car.infotainment
        if s is None:
            continue
        if filters.manufacturers and car.manufacturer.name not in filters.manufacturers:
            continue
        if filters.car_model_ids and car.id not in filters.car_model_ids:
            continue
        if filters.require_physical_buttons and s.physical_buttons_count < 1:
            continue
        if filters.require_android_auto and not s.android_auto_support:
            continue
        if filters.require_carplay and not s.carplay_support:
            continue
        if filters.require_voice_control and not s.voice_control:
            continue
        if filters.require_ota_updates and not s.ota_updates:
            continue
        if filters.min_display_size_in and s.display_size_in < filters.min_display_size_in:
            continue
        result.append(car)
    return result


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    version = _asset_version()
    response = templates.TemplateResponse(request, "index.html", {
        "css_version": version,
        "js_version": version,
    })
    response.headers["Cache-Control"] = "no-store"
    return response


@router.get("/api/criteria")
def list_criteria() -> List[CriterionListItem]:
    return [
        {
            "field": c["field"],
            "label": c["label"],
            "description": c.get("description", ""),
            "checkbox": bool(c.get("checkbox")),
            "synonyms": c.get("synonyms", []),
            "category": c.get("category"),
        }
        for c in mcda.CRITERIA_REGISTRY
    ]


@router.get("/api/models")
def list_models(db: Session = Depends(get_db)) -> List[ModelListItem]:
    cars = db.query(CarModel).options(joinedload(CarModel.infotainment),
                                       joinedload(CarModel.manufacturer)).all()
    return [
        {
            "id": c.id,
            "manufacturer": c.manufacturer.name,
            "model": c.name,
            "year": c.model_year,
            "powertrain": c.powertrain,
            "spec": _spec_to_dict(c.infotainment) if c.infotainment else None,
        }
        for c in cars
    ]


MAX_RESULTS = 10


def _active_hard_filter_labels(filters: HardFilters) -> list[str]:
    labels: list[str] = []
    if filters.require_physical_buttons:
        labels.append("Физически бутони")
    if filters.require_android_auto:
        labels.append("Android Auto")
    if filters.require_carplay:
        labels.append("CarPlay")
    if filters.require_voice_control:
        labels.append("Гласово управление")
    if filters.require_ota_updates:
        labels.append("OTA актуализации")
    if filters.min_display_size_in:
        labels.append(f"Дисплей ≥ {filters.min_display_size_in}\"")
    return labels


@router.post("/rank", response_model=RankResponse)
def rank_models(payload: RankRequest, db: Session = Depends(get_db)) -> RankResponse:
    cars = db.query(CarModel).options(joinedload(CarModel.infotainment),
                                       joinedload(CarModel.manufacturer)).all()
    cars = [c for c in cars if c.infotainment is not None]
    cars = _apply_hard_filters(cars, payload.filters)
    active_hard_filters = _active_hard_filter_labels(payload.filters)

    custom_results = mcda.resolve_custom_criteria(payload.criteria.custom_criterion)
    custom_criterion_results: List[CustomCriterionResult] = []
    for res in custom_results:
        match = res["match"]
        custom_criterion_results.append(CustomCriterionResult(
            requested=res["requested"],
            matched_field=match["field"] if match else None,
            matched_label=match["label"] if match else None,
        ))

    selected_fields = list(payload.criteria.features)
    for res in custom_results:
        match = res["match"]
        if match and match["field"] not in selected_fields:
            selected_fields.append(match["field"])

    if not selected_fields:
        raise HTTPException(
            status_code=400,
            detail="Избери поне един критерий (чекбокс) или въведи такъв, който съществува в базата.",
        )

    if not cars:
        return RankResponse(
            results=[],
            custom_criterion_results=custom_criterion_results,
            active_hard_filters=active_hard_filters,
        )

    specs: List[mcda.SpecDict] = []
    for c in cars:
        assert c.infotainment is not None
        specs.append(_spec_to_dict(c.infotainment))
    matrix, criteria = mcda.build_decision_matrix(specs)

    consistency_note: Optional[str] = None
    if payload.method == "wsm":
        weights_vector = mcda.weights_from_input(selected_fields, payload.criteria.feature_weights)
        scores = mcda.wsm_rank(matrix, criteria, weights_vector)
    elif payload.method == "topsis":
        weights_vector = mcda.weights_from_input(selected_fields, payload.criteria.feature_weights)
        scores = mcda.topsis_rank(matrix, criteria, weights_vector)
    elif payload.method == "ahp":
        scores, cr = mcda.ahp_rank(matrix, criteria, selected_fields)
        consistency_note = f"AHP Consistency Ratio = {cr:.3f}"
    else:
        raise ValueError(f"Непознат метод: {payload.method}")

    order = sorted(range(len(cars)), key=lambda i: scores[i], reverse=True)
    total_matches = len(order)
    if payload.limit is None:
        max_results = MAX_RESULTS
    elif payload.limit <= 0:
        max_results = total_matches
    else:
        max_results = payload.limit
    order = order[:max_results]

    results: List[RankedResult] = []
    for rank, idx in enumerate(order, start=1):
        car = cars[idx]
        breakdown = mcda.criteria_breakdown(specs[idx], selected_fields)
        results.append(RankedResult(
            car_model_id=car.id,
            manufacturer=car.manufacturer.name,
            model_name=car.name,
            model_year=car.model_year,
            score=round(float(scores[idx]), 4),
            rank=rank,
            matched_criteria=[CriterionMatch(**b) for b in breakdown],
        ))
    return RankResponse(
        results=results,
        custom_criterion_results=custom_criterion_results,
        consistency_note=consistency_note,
        active_hard_filters=active_hard_filters,
        total_matches=total_matches,
    )


@router.get("/results", response_class=HTMLResponse)
def results_page(request: Request):
    version = _asset_version()
    response = templates.TemplateResponse(request, "results.html", {
        "css_version": version,
        "js_version": version,
    })
    response.headers["Cache-Control"] = "no-store"
    return response
