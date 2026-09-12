
import { escapeHtml } from "./util.js";
import { state } from "./state.js";

let infoModalBackdrop, infoModalTitle, infoModalBody;

export function showInfoModal(title, bodyHtml) {
    infoModalTitle.textContent = title;
    infoModalBody.innerHTML = bodyHtml;
    infoModalBackdrop.hidden = false;
}

function closeInfoModal() {
    infoModalBackdrop.hidden = true;
}

export function initInfoModal() {
    infoModalBackdrop = document.getElementById("info-modal-backdrop");
    infoModalTitle = document.getElementById("info-modal-title");
    infoModalBody = document.getElementById("info-modal-body");

    document.getElementById("info-modal-close").addEventListener("click", closeInfoModal);
    infoModalBackdrop.addEventListener("click", (e) => {
        if (e.target === infoModalBackdrop) closeInfoModal();
    });
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape" && !infoModalBackdrop.hidden) closeInfoModal();
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".info-btn");
        if (!btn || btn.id === "custom-criterion-info") return;
        e.preventDefault();
        showInfoModal(btn.dataset.title, `<p>${escapeHtml(btn.dataset.text)}</p>`);
    });

    document.addEventListener("click", (e) => {
        const btn = e.target.closest(".details-btn");
        if (!btn) return;
        const result = state.lastResults[Number(btn.dataset.index)];
        if (!result) return;

        const rows = result.matched_criteria.map((m) => {
            const mark = m.satisfied ? "✓" : "×";
            const markClass = m.satisfied ? "feedback-ok" : "feedback-warn";
            const detail = m.is_boolean ? "" : ` — ${escapeHtml(m.value)}`;
            return `<li><span class="${markClass}">${mark}</span> ${escapeHtml(m.label)}${detail}</li>`;
        }).join("");

        let hardFiltersHtml = "";
        if (state.lastActiveHardFilters.length) {
            const hardRows = state.lastActiveHardFilters
                .map((label) => `<li><span class="feedback-ok">✓</span> ${escapeHtml(label)}</li>`)
                .join("");
            hardFiltersHtml = `<p class="subheading">Покрити задължителни изисквания</p><ul class="info-list details-list">${hardRows}</ul>`;
        }

        showInfoModal(
            `${result.manufacturer} ${result.model_name} (${result.model_year})`,
            `<p class="subheading">Избрани критерии</p><ul class="info-list details-list">${rows}</ul>${hardFiltersHtml}`
        );
    });
}
