
import { escapeHtml, hasRankParams, parseRankQueryString } from "./util.js";
import { postRank } from "./api.js";
import { renderResults } from "./render.js";
import { initInfoModal } from "./modal.js";

initInfoModal();

const statusEl = document.getElementById("results-status");

async function loadFromQueryString() {
    const params = new URLSearchParams(location.search);
    if (!hasRankParams(params)) {
        statusEl.innerHTML = `Тази страница показва резултат, споделен чрез линк, но в адреса няма критерии за класиране. <a href="/">Отиди към формата</a>, за да направиш ново класиране.`;
        return;
    }

    statusEl.textContent = "Зареждане на резултатите…";
    const payload = parseRankQueryString(params);

    payload.limit = 0;

    try {
        const result = await postRank(payload);
        statusEl.textContent = "";

        const unresolved = (result.custom_criterion_results || []).filter((r) => !r.matched_label);
        if (unresolved.length) {
            statusEl.textContent = `Забележка: „${unresolved.map((r) => r.requested).join('“, „')}“ не съвпадна с известен критерий и беше игнориран(о).`;
        }

        renderResults(result.results, result.consistency_note, result.active_hard_filters, result.total_matches);
    } catch (err) {
        statusEl.innerHTML = `${escapeHtml(err.message)} <a href="/">Отиди към формата</a>, за да опиташ отново.`;
    }
}

loadFromQueryString();
