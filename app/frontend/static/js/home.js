
import { escapeHtml, buildRankQueryString } from "./util.js";
import { state } from "./state.js";
import { fetchCriteria, fetchModels, postRank } from "./api.js";
import { renderResults } from "./render.js";
import { initInfoModal, showInfoModal } from "./modal.js";

const WEIGHT_MAX = 10;

const METHOD_EXPLANATIONS = {
    wsm: `WSM (претеглена сума): резултатът е сумата от нормализираните стойности по всички избрани критерии. До всеки чекбокс по-долу можеш по избор да впишеш число от 1 до ${WEIGHT_MAX} в полето „тегло“ - по-голямо число означава по-голяма важност; празно поле = тегло 1 (нормална важност). Всички стойности се нормализират автоматично, така че не е нужно да сумират до нищо конкретно.`,
    topsis: `TOPSIS: класира моделите по това колко близо са до „идеалния“ хипотетичен вариант и колко далеч са от „най-лошия“ възможен. До всеки чекбокс по-долу можеш по избор да впишеш число от 1 до ${WEIGHT_MAX} в полето „тегло“ - по-голямо число означава по-голяма важност; празно поле = тегло 1 (нормална важност). Всички стойности се нормализират автоматично, така че не е нужно да сумират до нищо конкретно.`,
    ahp: "AHP (йерархичен анализ): изчислява тегла чрез сравнение по двойки между избраните критерии (третирани като равностойни по важност) и проверява доколко преценките са консистентни (Consistency Ratio). Тук няма ръчно въвеждане на тегла.",
};

function updateMethodExplanation() {
    const method = document.getElementById("method").value;
    document.getElementById("method-explanation").textContent = METHOD_EXPLANATIONS[method] || "";

    document.getElementById("feature-checkboxes").classList.toggle("weights-enabled", method !== "ahp");
}

function renderRetry(container, message, retryFn) {
    container.innerHTML = "";
    const p = document.createElement("p");
    p.className = "hint";
    p.textContent = message;
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "details-btn";
    btn.textContent = "Опитай отново";
    btn.addEventListener("click", retryFn);
    container.appendChild(p);
    container.appendChild(btn);
}

async function loadFeatureCheckboxes() {
    const container = document.getElementById("feature-checkboxes");
    container.innerHTML = "<p class='hint'>Зареждане на критериите…</p>";
    try {
        state.allCriteria = await fetchCriteria();
        container.innerHTML = "";

        const groups = new Map();
        state.allCriteria.filter((c) => c.checkbox).forEach((c) => {
            const key = c.category || "Други";
            if (!groups.has(key)) groups.set(key, []);
            groups.get(key).push(c);
        });

        groups.forEach((criteria, category) => {
            const fieldset = document.createElement("fieldset");
            fieldset.className = "criteria-group";
            const legend = document.createElement("legend");
            legend.textContent = category;
            fieldset.appendChild(legend);

            const grid = document.createElement("div");
            grid.className = "feature-grid";
            criteria.forEach((c) => {
                const label = document.createElement("label");
                label.className = "checkbox-row";
                label.innerHTML = `
                    <input type="checkbox" class="feature-checkbox" value="${escapeHtml(c.field)}">
                    <span class="checkbox-label-text">${escapeHtml(c.label)}</span>
                    <input type="text" class="criterion-weight" inputmode="decimal" placeholder="1" max="${WEIGHT_MAX}" title="Число от 1 до ${WEIGHT_MAX} (по избор)" data-field="${escapeHtml(c.field)}" aria-label="Тегло за „${escapeHtml(c.label)}“ (по избор, число от 1 до ${WEIGHT_MAX}, само WSM/TOPSIS)">
                    <button type="button" class="info-btn" data-title="${escapeHtml(c.label)}" data-text="${escapeHtml(c.description)}" aria-label="Какво означава „${escapeHtml(c.label)}“">ⓘ</button>
                `;
                grid.appendChild(label);
            });
            grid.querySelectorAll(".criterion-weight").forEach((input) => {

                input.addEventListener("change", () => {
                    const value = Number(input.value.trim().replace(",", "."));
                    if (Number.isFinite(value) && value > WEIGHT_MAX) input.value = String(WEIGHT_MAX);
                });
            });
            fieldset.appendChild(grid);
            container.appendChild(fieldset);
        });
    } catch (err) {
        renderRetry(container, "Грешка при зареждане на критериите.", loadFeatureCheckboxes);
    }
}

function getSelectedFeatures() {
    return Array.from(document.querySelectorAll(".feature-checkbox:checked")).map((cb) => cb.value);
}

function getFeatureWeights() {
    const weights = {};
    document.querySelectorAll(".criterion-weight").forEach((input) => {
        const raw = input.value.trim();
        if (!raw) return;
        const value = Number(raw);
        if (Number.isFinite(value) && value > 0) weights[input.dataset.field] = Math.min(value, WEIGHT_MAX);
    });
    return weights;
}

const BRAND_PREVIEW_COUNT = 10;
let brandsExpanded = false;

async function loadBrandModelCheckboxes() {
    const brandContainer = document.getElementById("brand-checkboxes");
    const modelContainer = document.getElementById("model-checkboxes");
    const toggleBtn = document.getElementById("brands-toggle-more");
    brandContainer.innerHTML = "<p class='hint'>Зареждане на марките…</p>";
    modelContainer.innerHTML = "";
    toggleBtn.hidden = true;
    try {
        state.allModels = await fetchModels();

        const brands = [...new Set(state.allModels.map((m) => m.manufacturer))].sort((a, b) => a.localeCompare(b));
        brandContainer.innerHTML = "";
        brandsExpanded = false;
        brands.forEach((brand, index) => {
            const label = document.createElement("label");
            label.className = "checkbox-row";
            if (index >= BRAND_PREVIEW_COUNT) label.dataset.extra = "true";
            label.innerHTML = `<input type="checkbox" class="brand-checkbox" value="${escapeHtml(brand)}"> ${escapeHtml(brand)}`;
            brandContainer.appendChild(label);
        });
        brandContainer.querySelectorAll(".brand-checkbox").forEach((cb) => {
            cb.addEventListener("change", renderModelCheckboxes);
        });

        const extraCount = Math.max(0, brands.length - BRAND_PREVIEW_COUNT);
        toggleBtn.hidden = extraCount === 0;
        updateBrandsToggleLabel(extraCount);

        applyBrandModelFilter();

        renderModelCheckboxes();
    } catch (err) {
        renderRetry(brandContainer, "Грешка при зареждане на марките.", loadBrandModelCheckboxes);
        modelContainer.innerHTML = "";
    }
}

function updateBrandsToggleLabel(extraCount) {
    const toggleBtn = document.getElementById("brands-toggle-more");
    toggleBtn.textContent = brandsExpanded ? "Покажи по-малко" : `Покажи още (${extraCount})`;
}

document.getElementById("brands-toggle-more").addEventListener("click", () => {
    brandsExpanded = !brandsExpanded;
    const extraCount = document.querySelectorAll("#brand-checkboxes .checkbox-row[data-extra]").length;
    updateBrandsToggleLabel(extraCount);
    applyBrandModelFilter();
});

function renderModelCheckboxes() {
    const modelContainer = document.getElementById("model-checkboxes");
    const selectActions = document.getElementById("model-select-actions");
    const checkedBrands = Array.from(document.querySelectorAll(".brand-checkbox:checked")).map((cb) => cb.value);
    const previouslyChecked = new Set(
        Array.from(document.querySelectorAll(".model-checkbox:checked")).map((cb) => cb.value)
    );

    modelContainer.innerHTML = "";

    if (checkedBrands.length === 0) {
        modelContainer.innerHTML = "<p class='hint'>Маркирай марка по-горе, за да видиш моделите ѝ.</p>";
        selectActions.hidden = true;
        return;
    }
    selectActions.hidden = false;

    const visible = state.allModels.filter((m) => checkedBrands.includes(m.manufacturer));
    visible.forEach((m) => {
        const label = document.createElement("label");
        label.className = "checkbox-row";
        const checked = previouslyChecked.has(String(m.id)) ? "checked" : "";
        label.innerHTML = `<input type="checkbox" class="model-checkbox" value="${m.id}" ${checked}> ${escapeHtml(m.manufacturer)} ${escapeHtml(m.model)} (${m.year})`;
        modelContainer.appendChild(label);
    });

    applyBrandModelFilter();
}

const BRAND_FILTER_ALIASES = { vw: "volkswagen" };

let brandModelFilterTerms = [];

function applyBrandModelFilter() {
    document.querySelectorAll("#brand-checkboxes .checkbox-row, #model-checkboxes .checkbox-row").forEach((row) => {
        const text = row.textContent.toLowerCase();
        const hiddenByFilter = brandModelFilterTerms.length > 0
            && !brandModelFilterTerms.some((term) => text.includes(term) || text.includes(BRAND_FILTER_ALIASES[term] || "\0"));

        const hiddenByCollapse = row.dataset.extra === "true" && !brandsExpanded && brandModelFilterTerms.length === 0;
        row.hidden = hiddenByFilter || hiddenByCollapse;
    });
}

document.getElementById("brand-model-filter").addEventListener("input", (e) => {
    brandModelFilterTerms = e.target.value
        .split(/[,;]/)
        .map((term) => term.trim().toLowerCase())
        .filter(Boolean);
    applyBrandModelFilter();
});

document.getElementById("models-select-all").addEventListener("click", () => {
    document.querySelectorAll("#model-checkboxes .checkbox-row:not([hidden]) .model-checkbox")
        .forEach((cb) => { cb.checked = true; });
});

document.getElementById("models-clear").addEventListener("click", () => {
    document.querySelectorAll("#model-checkboxes .checkbox-row:not([hidden]) .model-checkbox")
        .forEach((cb) => { cb.checked = false; });
});

function getSelectedManufacturers() {
    return Array.from(document.querySelectorAll(".brand-checkbox:checked")).map((cb) => cb.value);
}

function getSelectedModelIds() {
    return Array.from(document.querySelectorAll(".model-checkbox:checked")).map((cb) => Number(cb.value));
}

async function submitRanking() {
    const features = getSelectedFeatures();
    const customCriterionRaw = document.getElementById("custom-criterion").value.trim();
    const customCriterion = customCriterionRaw || null;

    const feedback = document.getElementById("custom-criterion-feedback");
    feedback.textContent = "";
    feedback.className = "feedback";

    if (features.length === 0 && !customCriterion) {
        alert("Избери поне един критерий (чекбокс) или въведи такъв в текстовото поле.");
        return;
    }

    const filters = {
        require_physical_buttons: document.getElementById("f-buttons").checked,
        require_android_auto: document.getElementById("f-android").checked,
        require_carplay: document.getElementById("f-carplay").checked,
        require_voice_control: document.getElementById("f-voice").checked,
        require_ota_updates: document.getElementById("f-ota").checked,
        min_display_size_in: Number(document.getElementById("f-display").value) || null,
        manufacturers: getSelectedManufacturers(),
        car_model_ids: getSelectedModelIds(),
    };

    const method = document.getElementById("method").value;

    const featureWeights = method !== "ahp" ? getFeatureWeights() : {};
    const payload = { method, criteria: { features, custom_criterion: customCriterion, feature_weights: featureWeights }, filters };

    const submitBtn = document.getElementById("submit-btn");
    const originalLabel = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = "Класиране…";

    let result;
    try {
        result = await postRank(payload);
    } catch (err) {
        alert(err.message);
        return;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalLabel;
    }

    const customCriterionResults = result.custom_criterion_results || [];
    if (customCriterionResults.length) {
        feedback.innerHTML = customCriterionResults.map((r) => {
            if (r.matched_label) {
                return `<span class="feedback-ok">✓ „${escapeHtml(r.requested)}“ съвпадна с „${escapeHtml(r.matched_label)}“ и е включен в класирането.</span>`;
            }
            return `<span class="feedback-warn">„${escapeHtml(r.requested)}“ не съвпадна с известен критерий и беше игнориран.</span>`;
        }).join("<br>");
    }

    renderResults(result.results, result.consistency_note, result.active_hard_filters, result.total_matches);
    setupShareLink(payload);
}

function legacyCopyToClipboard(text) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    let ok = false;
    try {
        ok = document.execCommand("copy");
    } catch (err) {
        ok = false;
    }
    document.body.removeChild(textarea);
    return ok;
}

function setupShareLink(payload) {
    const btn = document.getElementById("copy-results-link");
    const feedback = document.getElementById("copy-results-feedback");
    const url = `${location.origin}/results?${buildRankQueryString(payload)}`;

    feedback.textContent = "";
    feedback.className = "feedback";
    btn.onclick = async () => {
        try {
            await navigator.clipboard.writeText(url);
            feedback.textContent = "Линкът е копиран!";
            feedback.className = "feedback feedback-ok";
        } catch (err) {

            if (legacyCopyToClipboard(url)) {
                feedback.textContent = "Линкът е копиран!";
                feedback.className = "feedback feedback-ok";
            } else {
                feedback.textContent = url;
                feedback.className = "feedback";
            }
        }
    };
}

function scrollToApp() {
    document.getElementById("app").scrollIntoView({ behavior: "smooth" });
}

function scrollToHero() {
    document.getElementById("hero").scrollIntoView({ behavior: "smooth" });
}

document.getElementById("start-btn").addEventListener("click", scrollToApp);
document.getElementById("scroll-indicator").addEventListener("click", scrollToApp);

const backToTop = document.getElementById("back-to-top");
backToTop.addEventListener("click", scrollToHero);
window.addEventListener("scroll", () => {
    backToTop.classList.toggle("visible", window.scrollY > window.innerHeight * 0.6);
}, { passive: true });

document.getElementById("custom-criterion-info").addEventListener("click", () => {
    const examples = state.allCriteria.filter((c) => !c.checkbox);
    const items = examples.map((c) => {
        const tries = (c.synonyms || []).slice(0, 3).join("“, „");
        return `<li><strong>${escapeHtml(c.label)}</strong> — ${escapeHtml(c.description)}${tries ? `<br><span class="hint">опитай: „${escapeHtml(tries)}“</span>` : ""}</li>`;
    }).join("");
    showInfoModal(
        "Примери за критерии в текстовото поле",
        `<p class="hint">Тези критерии нямат чекбокс, но можеш да ги добавиш, като напишеш нещо подобно в полето „Друг критерий“:</p><ul class="info-list">${items}</ul>`
    );
});

initInfoModal();

document.getElementById("method").addEventListener("change", updateMethodExplanation);
updateMethodExplanation();

document.getElementById("submit-btn").addEventListener("click", submitRanking);

(async () => {
    await Promise.all([loadFeatureCheckboxes(), loadBrandModelCheckboxes()]);
})();
