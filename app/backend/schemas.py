
from pydantic import BaseModel, ConfigDict, Field
from typing import Dict, List, Optional, Literal


class HardFilters(BaseModel):
    require_physical_buttons: bool = False
    require_android_auto: bool = False
    require_carplay: bool = False
    require_voice_control: bool = False
    require_ota_updates: bool = False
    min_display_size_in: Optional[float] = None
    manufacturers: List[str] = Field(default_factory=list)
    car_model_ids: List[int] = Field(default_factory=list)


class SelectedCriteria(BaseModel):
    features: List[str] = Field(default_factory=list)
    custom_criterion: Optional[str] = None
    feature_weights: Dict[str, float] = Field(default_factory=dict)


class RankRequest(BaseModel):
    method: Literal["wsm", "ahp", "topsis"] = "wsm"
    criteria: SelectedCriteria = SelectedCriteria()
    filters: HardFilters = HardFilters()
    limit: Optional[int] = None


class CriterionMatch(BaseModel):
    field: str
    label: str
    is_boolean: bool
    satisfied: bool
    value: Optional[float] = None


class RankedResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    car_model_id: int
    manufacturer: str
    model_name: str
    model_year: int
    score: float
    rank: int
    matched_criteria: List[CriterionMatch]


class CustomCriterionResult(BaseModel):
    requested: str
    matched_field: Optional[str] = None
    matched_label: Optional[str] = None


class RankResponse(BaseModel):
    results: List[RankedResult]
    custom_criterion_results: List[CustomCriterionResult] = Field(default_factory=list)
    consistency_note: Optional[str] = None
    active_hard_filters: List[str] = Field(default_factory=list)
    total_matches: int = 0
