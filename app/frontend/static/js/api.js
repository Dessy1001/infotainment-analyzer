
async function parseErrorDetail(response) {
    try {
        const body = await response.json();
        return body?.detail || null;
    } catch {
        return null;
    }
}

export async function fetchCriteria() {
    const response = await fetch("/api/criteria");
    if (!response.ok) {
        throw new Error((await parseErrorDetail(response)) || `Грешка при зареждане на критериите (${response.status}).`);
    }
    return response.json();
}

export async function fetchModels() {
    const response = await fetch("/api/models");
    if (!response.ok) {
        throw new Error((await parseErrorDetail(response)) || `Грешка при зареждане на моделите (${response.status}).`);
    }
    return response.json();
}

export async function postRank(payload) {
    const response = await fetch("/rank", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });
    if (!response.ok) {
        throw new Error((await parseErrorDetail(response)) || `Грешка при извикване на /rank (${response.status}).`);
    }
    return response.json();
}
