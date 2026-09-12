
from __future__ import annotations
import re
import numpy as np
import numpy.typing as npt
from typing import Dict, List, Optional, Tuple, TypedDict

FloatArray = npt.NDArray[np.float64]


class _CriterionDefRequired(TypedDict):
    field: str
    label: str


class CriterionDef(_CriterionDefRequired, total=False):
    description: str
    synonyms: List[str]
    cost: bool
    checkbox: bool
    category: str


class CriterionMatchResult(TypedDict):
    requested: str
    match: Optional[CriterionDef]


class SpecDict(TypedDict, total=False):
    os_type: Optional[str]
    display_size_in: float
    physical_buttons_count: int
    voice_control: bool
    ota_updates: bool
    carplay_support: bool
    android_auto_support: bool
    personalization_profiles: bool
    builtin_navigation: bool
    smart_home_compat: bool
    multimodal_input: bool
    multi_zone_displays: bool
    multi_bluetooth: bool
    charging_route_integration: bool
    startup_time_sec: float
    reaction_time_ms: float
    avg_steps_to_task: float
    ease_of_use_score: float
    ergonomics_score: float
    safety_distraction_score: float


class CriterionBreakdownItem(TypedDict):
    field: str
    label: str
    is_boolean: bool
    satisfied: bool
    value: Optional[float]


CRITERION_CATEGORIES = ["Свързаност и софтуер", "Управление и интерфейс", "Хардуер и функции"]

CRITERIA_REGISTRY: List[CriterionDef] = [
    {"field": "carplay_support", "label": "Поддръжка на Apple CarPlay",
     "description": "Безжична или кабелна връзка с iPhone за навигация, музика и съобщения през екрана на колата.",
     "synonyms": ["apple carplay", "carplay", "car play"], "checkbox": True, "category": "Свързаност и софтуер"},
    {"field": "android_auto_support", "label": "Поддръжка на Android Auto",
     "description": "Огледално свързване с Android телефон за навигация, музика и приложения на централния екран.",
     "synonyms": ["android auto", "андроид авто"], "checkbox": True, "category": "Свързаност и софтуер"},
    {"field": "ota_updates", "label": "OTA (Over-The-Air) актуализации",
     "description": "Софтуерът на системата се обновява безжично, без да е нужно посещение в сервиз.",
     "synonyms": ["ota", "over-the-air", "актуализации", "обновявания"], "checkbox": True, "category": "Свързаност и софтуер"},
    {"field": "smart_home_compat", "label": "Съвместимост с \"умен дом\" / гласови асистенти",
     "description": "Връзка с гласови асистенти извън колата (Alexa, Google Assistant) - напр. управление на устройства у дома.",
     "synonyms": ["умен дом", "alexa", "google assistant", "smart home"], "checkbox": True, "category": "Свързаност и софтуер"},
    {"field": "multi_bluetooth", "label": "Поддръжка на множество Bluetooth устройства едновременно",
     "description": "Две устройства могат да бъдат свързани едновременно по Bluetooth (напр. два сдвоени телефона).",
     "synonyms": ["bluetooth", "два телефона", "множество bluetooth"], "checkbox": True, "category": "Свързаност и софтуер"},
    {"field": "voice_control", "label": "Гласово управление",
     "description": "Управление чрез гласови команди на естествен език, без да е нужно да докосваш екрана.",
     "synonyms": ["voice control", "глас", "гласови команди"], "checkbox": True, "category": "Управление и интерфейс"},
    {"field": "physical_buttons_count", "label": "Физически бутони/копчета за често използвани функции",
     "description": "Реални бутони/копчета за климатик, звук и др. - по-малко навигиране през менюта на екрана.",
     "synonyms": ["физически бутони", "копчета", "buttons", "климатик", "звук"], "checkbox": True, "category": "Управление и интерфейс"},
    {"field": "multimodal_input", "label": "Мултимодален вход",
     "description": "Комбинация от сензорен екран, физически контроли и/или жестове - повече от един начин за управление.",
     "synonyms": ["мултимодален", "жестове", "gesture", "multimodal"], "checkbox": True, "category": "Управление и интерфейс"},
    {"field": "personalization_profiles", "label": "Персонализирани потребителски профили",
     "description": "Системата запомня настройки (седалка, климатик, любими станции) поотделно за различни водачи.",
     "synonyms": ["потребителски профили", "профили", "personalization"], "checkbox": True, "category": "Управление и интерфейс"},
    {"field": "builtin_navigation", "label": "Вградена навигация в реално време",
     "description": "Навигация с карти, вградена в колата - работи и без свързан телефон.",
     "synonyms": ["навигация", "navigation", "gps"], "checkbox": True, "category": "Хардуер и функции"},
    {"field": "multi_zone_displays", "label": "Множество зони/дисплеи",
     "description": "Отделни екрани за пътника отпред или за пътниците на задната седалка.",
     "synonyms": ["зони", "дисплеи за задни седалки", "rear display", "multi-zone", "пътник"], "checkbox": True, "category": "Хардуер и функции"},
    {"field": "charging_route_integration", "label": "Интеграция със зареждане",
     "description": "Планиране на маршрут със спирки за зареждане (route planning с charging stops) и предварително подгряване на батерията преди пристигане на зарядна станция - специфична за електромобилите функция.",
     "synonyms": ["зареждане", "charging", "route planning", "подгряване на батерията",
                  "battery preconditioning", "charging stops", "зарядни станции"],
     "checkbox": True, "category": "Хардуер и функции"},

    {"field": "display_size_in", "label": "Размер на дисплея",
     "description": "Диагонал на централния екран в инчове - по-голям обикновено означава по-добра четимост.",
     "synonyms": ["дисплей", "инча", "display size", "екран"], "checkbox": False},
    {"field": "startup_time_sec", "label": "Време за стартиране на системата",
     "description": "Колко бързо инфотейнмънтът е готов за употреба след запалване на колата.",
     "synonyms": ["стартиране", "boot time", "startup"], "cost": True, "checkbox": False},
    {"field": "reaction_time_ms", "label": "Време за реакция",
     "description": "Колко бързо интерфейсът реагира на докосване или команда.",
     "synonyms": ["реакция", "latency", "reaction time"], "cost": True, "checkbox": False},
    {"field": "avg_steps_to_task", "label": "Стъпки за изпълнение на задача",
     "description": "Средно колко стъпки/докосвания са нужни за честа задача, напр. смяна на температурата.",
     "synonyms": ["стъпки", "steps"], "cost": True, "checkbox": False},
    {"field": "ease_of_use_score", "label": "Лекота на употреба",
     "description": "Обща субективна оценка колко лесна и интуитивна е системата за употреба.",
     "synonyms": ["лекота", "ease of use"], "checkbox": False},
    {"field": "ergonomics_score", "label": "Ергономичност",
     "description": "Доколко удобно е разположението на екрана и контролите спрямо водача.",
     "synonyms": ["ергономичност", "ergonomics"], "checkbox": False},
    {"field": "safety_distraction_score", "label": "Безопасност / ниско отвличане на вниманието",
     "description": "Доколко системата НЕ отвлича вниманието на водача по време на шофиране - по-високо е по-безопасно.",
     "synonyms": ["безопасност", "отвличане на вниманието", "safety"], "checkbox": False},
]

CRITERIA_BY_FIELD: Dict[str, CriterionDef] = {c["field"]: c for c in CRITERIA_REGISTRY}

ALL_CRITERIA: List[str] = [c["field"] for c in CRITERIA_REGISTRY]

COST_CRITERIA = {c["field"] for c in CRITERIA_REGISTRY if c.get("cost")}


def _normalize_text(text: str) -> str:
    return re.sub(r"[^a-zA-Zа-яА-Я0-9]+", " ", text.lower()).strip()


def _word_boundary_contains(haystack: str, needle: str) -> bool:
    return re.search(rf"\b{re.escape(needle)}\b", haystack) is not None


def resolve_custom_criterion(text: Optional[str]) -> Optional[CriterionDef]:
    norm = _normalize_text(text) if text else ""
    if not norm:
        return None
    for crit in CRITERIA_REGISTRY:
        candidates = [crit["label"], *crit.get("synonyms", [])]
        for cand in candidates:
            cand_norm = _normalize_text(cand)
            if len(cand_norm) < 3:
                continue
            if norm == cand_norm or norm in cand_norm or _word_boundary_contains(norm, cand_norm):
                return crit
    return None


def resolve_custom_criteria(text: Optional[str]) -> List[CriterionMatchResult]:
    if not text:
        return []
    terms = [t.strip() for t in re.split(r"[,;]", text) if t.strip()]
    return [{"requested": term, "match": resolve_custom_criterion(term)} for term in terms]


def build_decision_matrix(specs: List[SpecDict]) -> Tuple[FloatArray, List[str]]:
    matrix = np.zeros((len(specs), len(ALL_CRITERIA)), dtype=float)
    for i, spec in enumerate(specs):
        for j, crit in enumerate(ALL_CRITERIA):
            value = spec.get(crit, 0)
            if isinstance(value, bool):
                value = 1.0 if value else 0.0
            matrix[i, j] = float(value)
    return matrix, ALL_CRITERIA


MAX_CRITERION_WEIGHT = 10.0


def weights_from_input(selected_fields: List[str], raw_weights: Optional[Dict[str, float]] = None) -> FloatArray:
    seen: List[str] = []
    for field in selected_fields:
        if field in CRITERIA_BY_FIELD and field not in seen:
            seen.append(field)
    if not seen:
        raise ValueError("Няма избрани валидни критерии.")

    raw_weights = raw_weights or {}
    raw_values: Dict[str, float] = {}
    for field in seen:
        try:
            value = float(raw_weights[field])
        except (KeyError, TypeError, ValueError):
            value = 1.0
        raw_values[field] = min(value, MAX_CRITERION_WEIGHT) if value > 0 else 1.0

    total = sum(raw_values.values())
    weights = np.zeros(len(ALL_CRITERIA))
    for field in seen:
        weights[ALL_CRITERIA.index(field)] = raw_values[field] / total
    return weights


def _minmax_normalize(matrix: FloatArray, criteria: List[str]) -> FloatArray:
    norm = np.zeros_like(matrix, dtype=float)
    for j, crit in enumerate(criteria):
        col = matrix[:, j]
        col_min, col_max = col.min(), col.max()
        span = col_max - col_min
        if span == 0:
            norm[:, j] = 1.0
            continue
        if crit in COST_CRITERIA:
            norm[:, j] = (col_max - col) / span
        else:
            norm[:, j] = (col - col_min) / span
    return norm


def wsm_rank(matrix: FloatArray, criteria: List[str], weights: FloatArray) -> FloatArray:
    norm = _minmax_normalize(matrix, criteria)
    scores = norm @ weights
    return scores


_RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12,
                  6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}


def build_pairwise_matrix_from_weights(weights_by_name: Dict[str, float]) -> Tuple[FloatArray, List[str]]:
    names = list(weights_by_name.keys())
    n = len(names)
    pcm = np.ones((n, n))
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            ratio = weights_by_name[names[i]] / weights_by_name[names[j]] if weights_by_name[names[j]] > 0 else 1.0
            saaty = np.clip(ratio, 1 / 9, 9)
            pcm[i, j] = saaty
    return pcm, names


def ahp_weights(pairwise_matrix: FloatArray) -> Tuple[FloatArray, float]:
    n = pairwise_matrix.shape[0]
    eigvals, eigvecs = np.linalg.eig(pairwise_matrix)
    max_idx = int(np.argmax(eigvals.real))
    lambda_max = eigvals.real[max_idx]
    principal_vector = np.abs(eigvecs[:, max_idx].real)
    weights = principal_vector / principal_vector.sum()

    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = _RANDOM_INDEX.get(n, 1.49)
    cr = ci / ri if ri != 0 else 0.0
    return weights, cr


def ahp_rank(matrix: FloatArray, criteria: List[str], selected_fields: List[str]
             ) -> Tuple[FloatArray, float]:
    seen: List[str] = []
    for field in selected_fields:
        if field in CRITERIA_BY_FIELD and field not in seen:
            seen.append(field)
    if not seen:
        raise ValueError("Няма избрани валидни критерии.")

    equal = {field: 1.0 for field in seen}
    pcm, field_names = build_pairwise_matrix_from_weights(equal)
    sub_ahp_weights, cr = ahp_weights(pcm)
    resolved = dict(zip(field_names, sub_ahp_weights))

    weights_vector = np.zeros(len(ALL_CRITERIA))
    for field, w in resolved.items():
        weights_vector[ALL_CRITERIA.index(field)] = w

    norm = _minmax_normalize(matrix, criteria)
    scores = norm @ weights_vector
    return scores, cr


def topsis_rank(matrix: FloatArray, criteria: List[str], weights: FloatArray) -> FloatArray:
    denom = np.sqrt((matrix ** 2).sum(axis=0))
    denom[denom == 0] = 1
    r = matrix / denom

    v = r * weights

    ideal_best = np.zeros(v.shape[1])
    ideal_worst = np.zeros(v.shape[1])
    for j, crit in enumerate(criteria):
        if crit in COST_CRITERIA:
            ideal_best[j] = v[:, j].min()
            ideal_worst[j] = v[:, j].max()
        else:
            ideal_best[j] = v[:, j].max()
            ideal_worst[j] = v[:, j].min()

    dist_best = np.sqrt(((v - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((v - ideal_worst) ** 2).sum(axis=1))

    denom_c = dist_best + dist_worst
    denom_c[denom_c == 0] = 1
    closeness = dist_worst / denom_c
    return closeness


def criteria_breakdown(spec: SpecDict, selected_fields: List[str]) -> List[CriterionBreakdownItem]:
    breakdown: List[CriterionBreakdownItem] = []
    for crit in CRITERIA_REGISTRY:
        field = crit["field"]
        if field not in selected_fields:
            continue
        raw = spec.get(field)
        is_boolean = isinstance(raw, bool)
        numeric_value = None if raw is None or is_boolean else float(raw)
        breakdown.append({
            "field": field,
            "label": crit["label"],
            "is_boolean": is_boolean,
            "satisfied": bool(raw) if is_boolean else True,
            "value": numeric_value,
        })
    return breakdown
