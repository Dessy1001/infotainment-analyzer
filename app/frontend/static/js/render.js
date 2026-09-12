
import { escapeHtml } from "./util.js";
import { state } from "./state.js";

export function renderResults(results, consistencyNote, activeHardFilters, totalMatches) {
    const panel = document.getElementById("results-panel");
    panel.style.display = "block";
    void panel.offsetHeight;

    const notes = [consistencyNote];
    if (totalMatches > results.length) {
        notes.push(`Показани най-добрите ${results.length} от общо ${totalMatches} отговарящи модела.`);
    }
    document.getElementById("consistency-note").textContent = notes.filter(Boolean).join(" · ");

    state.lastResults = results;
    state.lastActiveHardFilters = activeHardFilters || [];
    const tbody = document.querySelector("#results-table tbody");
    tbody.innerHTML = "";

    if (results.length === 0) {
        tbody.innerHTML = "<tr><td colspan='7'>Няма модели, отговарящи на зададените филтри.</td></tr>";
        if (state.chartInstance) state.chartInstance.destroy();
        return;
    }

    results.forEach((r, index) => {

        const summary = state.lastActiveHardFilters.length
            ? escapeHtml(state.lastActiveHardFilters.join(", "))
            : "—";

        const row = document.createElement("tr");
        row.innerHTML = `
            <td>${r.rank}</td>
            <td>${escapeHtml(r.manufacturer)}</td>
            <td>${escapeHtml(r.model_name)}</td>
            <td>${r.model_year}</td>
            <td>${r.score.toFixed(3)}</td>
            <td>${summary}</td>
            <td><button type="button" class="details-btn" data-index="${index}">Детайли</button></td>
        `;
        tbody.appendChild(row);
    });

    const ctx = document.getElementById("results-chart");
    const labels = results.map((r) => `${r.manufacturer} ${r.model_name}`);
    const scores = results.map((r) => r.score);

    if (state.chartInstance) state.chartInstance.destroy();
    state.chartInstance = new Chart(ctx, {
        type: "bar",
        data: {
            labels,
            datasets: [{ label: "Резултат от класирането", data: scores, backgroundColor: "#38bdf8" }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: "y",
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
                y: { ticks: { color: "#e2e8f0" }, grid: { color: "#334155" } },
            },
        },
    });

    panel.scrollIntoView({ behavior: "smooth", block: "start" });
}
