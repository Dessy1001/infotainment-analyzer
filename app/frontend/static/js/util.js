
export function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
    }[ch]));
}

export function buildRankQueryString(payload) {
    const params = new URLSearchParams();
    params.set("method", payload.method || "wsm");

    (payload.criteria?.features || []).forEach((f) => params.append("feat", f));
    if (payload.criteria?.custom_criterion) {
        params.set("custom", payload.criteria.custom_criterion);
    }

    Object.entries(payload.criteria?.feature_weights || {}).forEach(([field, weight]) => {
        params.append("w", `${field}:${weight}`);
    });

    const filters = payload.filters || {};
    if (filters.require_physical_buttons) params.set("buttons", "1");
    if (filters.require_android_auto) params.set("android", "1");
    if (filters.require_carplay) params.set("carplay", "1");
    if (filters.require_voice_control) params.set("voice", "1");
    if (filters.require_ota_updates) params.set("ota", "1");
    if (filters.min_display_size_in) params.set("display", String(filters.min_display_size_in));
    (filters.manufacturers || []).forEach((m) => params.append("brand", m));
    (filters.car_model_ids || []).forEach((id) => params.append("model", String(id)));

    return params.toString();
}

export function hasRankParams(searchParams) {
    return searchParams.has("method") || searchParams.getAll("feat").length > 0 || searchParams.has("custom");
}

export function parseRankQueryString(searchParams) {
    const display = searchParams.get("display");
    const modelIds = searchParams.getAll("model")
        .map(Number)
        .filter((n) => Number.isFinite(n));

    const featureWeights = {};
    searchParams.getAll("w").forEach((entry) => {
        const sep = entry.indexOf(":");
        if (sep === -1) return;
        const field = entry.slice(0, sep);
        const weight = Number(entry.slice(sep + 1));
        if (field && Number.isFinite(weight)) featureWeights[field] = weight;
    });

    return {
        method: searchParams.get("method") || "wsm",
        criteria: {
            features: searchParams.getAll("feat"),
            custom_criterion: searchParams.get("custom") || null,
            feature_weights: featureWeights,
        },
        filters: {
            require_physical_buttons: searchParams.get("buttons") === "1",
            require_android_auto: searchParams.get("android") === "1",
            require_carplay: searchParams.get("carplay") === "1",
            require_voice_control: searchParams.get("voice") === "1",
            require_ota_updates: searchParams.get("ota") === "1",
            min_display_size_in: display ? Number(display) : null,
            manufacturers: searchParams.getAll("brand"),
            car_model_ids: modelIds,
        },
    };
}
