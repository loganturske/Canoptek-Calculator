(function () {
  const bootstrap = window.__CANOPTEK_BOOTSTRAP__ || { factions: [], stats: {}, defaultTrials: 5000 };
  const state = {
    datasheets: [],
    datasheetMap: new Map(),
    displayToId: new Map(),
    detailCache: new Map(),
    attackerId: null,
    defenderId: null,
    defenderMode: "datasheet",
  };

  const elements = {
    syncButton: document.getElementById("sync-button"),
    syncStatus: document.getElementById("sync-status"),
    datalist: document.getElementById("datasheet-options"),
    attackerInput: document.getElementById("attacker-input"),
    defenderInput: document.getElementById("defender-input"),
    weaponSelect: document.getElementById("weapon-select"),
    defenderModelSelect: document.getElementById("defender-model-select"),
    simulationForm: document.getElementById("simulation-form"),
    resultsPanel: document.getElementById("results-panel"),
    browserSearch: document.getElementById("browser-search"),
    browserFaction: document.getElementById("browser-faction"),
    browserList: document.getElementById("browser-list"),
    datasheetDetail: document.getElementById("datasheet-detail"),
    targetPanels: {
      datasheet: document.getElementById("datasheet-target-panel"),
      custom: document.getElementById("custom-target-panel"),
    },
    segments: Array.from(document.querySelectorAll(".segment")),
  };

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function formatDate(value) {
    if (!value) {
      return "Not available";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return String(value);
    }
    return date.toLocaleString();
  }

  function updateStats(stats) {
    document.getElementById("stat-factions").textContent = stats.faction_count ?? 0;
    document.getElementById("stat-datasheets").textContent = stats.datasheet_count ?? 0;
    document.getElementById("stat-weapons").textContent = stats.weapon_count ?? 0;
    document.getElementById("stat-files").textContent = stats.fixture_file_count ?? 0;
    document.getElementById("meta-fixtures").textContent = stats.fixtures_dir ?? "Unknown";
    document.getElementById("meta-last-update").textContent = formatDate(stats.last_update);
    document.getElementById("meta-last-download").textContent = formatDate(stats.last_downloaded_at);
  }

  function buildDisplayLabel(summary) {
    return `${summary.name} :: ${summary.faction_name} :: ${summary.id}`;
  }

  function hydrateDatasheetSelectors(datasheets) {
    state.datasheetMap.clear();
    state.displayToId.clear();
    elements.datalist.innerHTML = "";

    datasheets.forEach((summary) => {
      state.datasheetMap.set(summary.id, summary);
      const label = buildDisplayLabel(summary);
      state.displayToId.set(label, summary.id);
      const option = document.createElement("option");
      option.value = label;
      elements.datalist.appendChild(option);
    });
  }

  function setSyncStatus(message, isError = false) {
    elements.syncStatus.textContent = message;
    elements.syncStatus.style.color = isError ? "var(--danger)" : "";
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const body = response.headers.get("Content-Type")?.includes("application/json")
      ? await response.json()
      : await response.text();
    if (!response.ok) {
      const detail = typeof body === "string" ? body : body.detail || "Request failed.";
      throw new Error(detail);
    }
    return body;
  }

  async function loadDashboard() {
    const stats = await fetchJson("/api/dashboard");
    updateStats(stats);
  }

  async function loadCatalog() {
    const datasheets = await fetchJson("/api/datasheets?limit=2500");
    state.datasheets = datasheets;
    hydrateDatasheetSelectors(datasheets);
    renderBrowserList();
  }

  async function loadDetail(datasheetId) {
    if (state.detailCache.has(datasheetId)) {
      return state.detailCache.get(datasheetId);
    }

    const detail = await fetchJson(`/api/datasheets/${datasheetId}`);
    state.detailCache.set(datasheetId, detail);
    return detail;
  }

  function selectFromInput(inputElement) {
    const datasheetId = state.displayToId.get(inputElement.value);
    return datasheetId || null;
  }

  async function handleAttackerChange() {
    state.attackerId = selectFromInput(elements.attackerInput);
    if (!state.attackerId) {
      elements.weaponSelect.innerHTML = "<option value=''>Select a valid attacker</option>";
      return;
    }

    const detail = await loadDetail(state.attackerId);
    const options = detail.weapons.map((weapon) => {
      const disabled = weapon.is_simulatable ? "" : "disabled";
      const suffix = weapon.is_simulatable ? "" : " (unsupported)";
      return `<option value="${weapon.weapon_id}" ${disabled}>${escapeHtml(weapon.name)} [${escapeHtml(weapon.weapon_type || "Unknown")}]${suffix}</option>`;
    });
    elements.weaponSelect.innerHTML = options.length
      ? options.join("")
      : "<option value=''>No weapons available</option>";
  }

  async function handleDefenderChange() {
    state.defenderId = selectFromInput(elements.defenderInput);
    if (!state.defenderId) {
      elements.defenderModelSelect.innerHTML = "<option value=''>Select a valid defender</option>";
      return;
    }

    const detail = await loadDetail(state.defenderId);
    const options = detail.models.map((model) => {
      return `<option value="${model.model_id}">${escapeHtml(model.name)} (T${model.toughness ?? "?"} / ${model.save ?? "?"}+ / ${model.wounds ?? "?"}W)</option>`;
    });
    elements.defenderModelSelect.innerHTML = options.length
      ? options.join("")
      : "<option value=''>No model lines available</option>";
  }

  function renderBrowserList() {
    const searchTerm = (elements.browserSearch.value || "").trim().toLowerCase();
    const factionId = elements.browserFaction.value;
    const filtered = state.datasheets
      .filter((datasheet) => !factionId || datasheet.faction_id === factionId)
      .filter((datasheet) => datasheet.name.toLowerCase().includes(searchTerm))
      .slice(0, 150);

    if (!filtered.length) {
      elements.browserList.innerHTML = "<p class='empty-state'>No datasheets match that filter.</p>";
      return;
    }

    elements.browserList.innerHTML = `
      <div class="datasheet-list">
        ${filtered
          .map(
            (datasheet) => `
              <button class="datasheet-row" data-datasheet-id="${datasheet.id}">
                ${escapeHtml(datasheet.name)}
                <small>${escapeHtml(datasheet.faction_name)} · ${escapeHtml(datasheet.source_name)}${datasheet.role ? ` · ${escapeHtml(datasheet.role)}` : ""}</small>
              </button>
            `,
          )
          .join("")}
      </div>
    `;

    Array.from(elements.browserList.querySelectorAll("[data-datasheet-id]")).forEach((button) => {
      button.addEventListener("click", async () => {
        const detail = await loadDetail(button.dataset.datasheetId);
        renderDetail(detail);
      });
    });
  }

  function listBlock(title, items) {
    if (!items.length) {
      return "";
    }
    return `
      <section class="detail-block">
        <h3>${escapeHtml(title)}</h3>
        <ul>
          ${items.map((item) => `<li>${item}</li>`).join("")}
        </ul>
      </section>
    `;
  }

  function renderDetail(detail) {
    const abilityItems = detail.abilities.map((ability) => {
      const heading = [ability.name, ability.ability_type].filter(Boolean).join(" · ");
      return `<strong>${escapeHtml(heading)}</strong>${ability.parameter ? ` <code>${escapeHtml(ability.parameter)}</code>` : ""}${ability.description_html ? `<div>${ability.description_html}</div>` : ""}`;
    });
    const optionItems = detail.options.map((option) => {
      return `${option.button ? `<strong>${escapeHtml(option.button)}</strong> ` : ""}${option.description_html || ""}`;
    });
    const compositionItems = detail.unit_composition.map((entry) => escapeHtml(entry));
    const stratagemItems = detail.stratagems.map((rule) => {
      return `<strong>${escapeHtml(rule.name)}</strong>${rule.subtitle ? ` <span class="chip chip-supported">${escapeHtml(rule.subtitle)}</span>` : ""}${rule.cost !== null ? ` <code>${rule.cost} CP</code>` : ""}${rule.description_html ? `<div>${rule.description_html}</div>` : ""}`;
    });
    const enhancementItems = detail.enhancements.map((rule) => {
      return `<strong>${escapeHtml(rule.name)}</strong>${rule.cost !== null ? ` <code>${rule.cost} pts</code>` : ""}${rule.description_html ? `<div>${rule.description_html}</div>` : ""}`;
    });
    const detachmentAbilityItems = detail.detachment_abilities.map((rule) => {
      return `<strong>${escapeHtml(rule.name)}</strong>${rule.subtitle ? ` <span class="chip chip-supported">${escapeHtml(rule.subtitle)}</span>` : ""}${rule.description_html ? `<div>${rule.description_html}</div>` : ""}`;
    });

    elements.datasheetDetail.innerHTML = `
      <div class="detail-stack">
        <section class="detail-block">
          <p class="section-label">${escapeHtml(detail.faction_name)}</p>
          <h2>${escapeHtml(detail.name)}</h2>
          <p>${escapeHtml(detail.source_name)}${detail.role ? ` · ${escapeHtml(detail.role)}` : ""}</p>
          ${detail.legend_html ? `<div>${detail.legend_html}</div>` : ""}
          <ul class="inline-list">
            ${detail.keywords.map((keyword) => `<li class="chip chip-supported">${escapeHtml(keyword)}</li>`).join("")}
          </ul>
        </section>

        <div class="detail-columns">
          <section class="detail-block">
            <h3>Models</h3>
            <table class="data-table">
              <thead>
                <tr><th>Name</th><th>T</th><th>Sv</th><th>Inv</th><th>W</th></tr>
              </thead>
              <tbody>
                ${detail.models
                  .map(
                    (model) => `
                      <tr>
                        <td>${escapeHtml(model.name)}</td>
                        <td>${model.toughness ?? "-"}</td>
                        <td>${model.save ? `${model.save}+` : "-"}</td>
                        <td>${model.invulnerable_save ? `${model.invulnerable_save}+` : "-"}</td>
                        <td>${model.wounds ?? "-"}</td>
                      </tr>
                    `,
                  )
                  .join("")}
              </tbody>
            </table>
          </section>

          <section class="detail-block">
            <h3>Weapons</h3>
            <table class="data-table">
              <thead>
                <tr><th>Name</th><th>Range</th><th>A</th><th>Skill</th><th>S</th><th>AP</th><th>D</th></tr>
              </thead>
              <tbody>
                ${detail.weapons
                  .map(
                    (weapon) => `
                      <tr>
                        <td>
                          ${escapeHtml(weapon.name)}
                          ${weapon.rules.length ? `<div class="rule-list">${weapon.rules.map((rule) => `<span class="chip chip-supported">${escapeHtml(rule)}</span>`).join("")}</div>` : ""}
                          ${weapon.ignored_rules.length ? `<div class="rule-list">${weapon.ignored_rules.map((rule) => `<span class="chip chip-ignored">${escapeHtml(rule)}</span>`).join("")}</div>` : ""}
                        </td>
                        <td>${escapeHtml(weapon.range || "-")}</td>
                        <td>${escapeHtml(weapon.attacks || "-")}</td>
                        <td>${escapeHtml(weapon.skill || "-")}</td>
                        <td>${escapeHtml(weapon.strength || "-")}</td>
                        <td>${escapeHtml(weapon.armour_penetration || "-")}</td>
                        <td>${escapeHtml(weapon.damage || "-")}</td>
                      </tr>
                    `,
                  )
                  .join("")}
              </tbody>
            </table>
          </section>
        </div>

        ${detail.loadout_html ? `<section class="detail-block"><h3>Loadout</h3><div>${detail.loadout_html}</div></section>` : ""}
        ${detail.transport_html ? `<section class="detail-block"><h3>Transport</h3><div>${detail.transport_html}</div></section>` : ""}
        ${listBlock("Abilities", abilityItems)}
        ${listBlock("Unit composition", compositionItems)}
        ${listBlock("Options", optionItems)}
        ${listBlock("Stratagems", stratagemItems)}
        ${listBlock("Enhancements", enhancementItems)}
        ${listBlock("Detachment abilities", detachmentAbilityItems)}
      </div>
    `;
  }

  function renderSimulationResults(result) {
    const maxProbability = Math.max(...result.monte_carlo.histogram.map((bucket) => bucket.probability), 0.0001);
    const histogramRows = result.monte_carlo.histogram
      .slice(0, 18)
      .map((bucket) => {
        const width = Math.max((bucket.probability / maxProbability) * 100, 1);
        return `
          <div class="histogram-row">
            <span>${bucket.wounds_lost} W</span>
            <div class="bar"><span style="width:${width}%"></span></div>
            <span>${(bucket.probability * 100).toFixed(1)}%</span>
          </div>
        `;
      })
      .join("");

    elements.resultsPanel.innerHTML = `
      <div class="results-grid">
        <section class="result-card">
          <p class="section-label">Expected value</p>
          <h3>${escapeHtml(result.weapon_name)} into ${escapeHtml(result.target_name)}</h3>
          <div class="metric-grid">
            <div class="metric"><span>Attacks</span><strong>${result.expected.attacks.toFixed(2)}</strong></div>
            <div class="metric"><span>Hits</span><strong>${result.expected.hits.toFixed(2)}</strong></div>
            <div class="metric"><span>Wounds</span><strong>${result.expected.wounds.toFixed(2)}</strong></div>
            <div class="metric"><span>Unsaved wounds</span><strong>${result.expected.unsaved_wounds.toFixed(2)}</strong></div>
            <div class="metric"><span>Raw damage</span><strong>${result.expected.raw_damage.toFixed(2)}</strong></div>
            <div class="metric"><span>Effective hit / wound mod</span><strong>${result.effective_hit_modifier >= 0 ? "+" : ""}${result.effective_hit_modifier} / ${result.effective_wound_modifier >= 0 ? "+" : ""}${result.effective_wound_modifier}</strong></div>
          </div>
          <div class="rule-list">
            ${result.supported_rules.map((rule) => `<span class="chip chip-supported">${escapeHtml(rule)}</span>`).join("")}
            ${result.ignored_rules.map((rule) => `<span class="chip chip-ignored">${escapeHtml(rule)}</span>`).join("")}
          </div>
        </section>
        <section class="result-card">
          <p class="section-label">Monte Carlo</p>
          <div class="metric-grid">
            <div class="metric"><span>Average wounds lost</span><strong>${result.monte_carlo.average_wounds_lost.toFixed(2)}</strong></div>
            <div class="metric"><span>Average models slain</span><strong>${result.monte_carlo.average_models_slain.toFixed(2)}</strong></div>
            <div class="metric"><span>Kill probability</span><strong>${(result.monte_carlo.kill_probability * 100).toFixed(1)}%</strong></div>
            <div class="metric"><span>Average raw damage</span><strong>${result.monte_carlo.average_raw_damage.toFixed(2)}</strong></div>
            <div class="metric"><span>P10 / Median</span><strong>${result.monte_carlo.p10_wounds_lost.toFixed(1)} / ${result.monte_carlo.median_wounds_lost.toFixed(1)}</strong></div>
            <div class="metric"><span>P90</span><strong>${result.monte_carlo.p90_wounds_lost.toFixed(1)}</strong></div>
          </div>
          <div class="histogram">${histogramRows || "<p class='empty-state'>No histogram available.</p>"}</div>
        </section>
      </div>
    `;
  }

  function buildSimulationPayload() {
    const payload = {
      attacker_weapon_id: Number(elements.weaponSelect.value),
      attacker_models: Number(document.getElementById("attacker-models").value),
      defender_mode: state.defenderMode,
      defender_model_id: state.defenderMode === "datasheet" ? Number(elements.defenderModelSelect.value) : null,
      target_model_count: Number(document.getElementById("target-model-count").value),
      defender_in_cover: document.getElementById("target-cover").checked,
      hit_reroll: document.getElementById("hit-reroll").value,
      wound_reroll: document.getElementById("wound-reroll").value,
      hit_modifier: Number(document.getElementById("hit-modifier").value),
      wound_modifier: Number(document.getElementById("wound-modifier").value),
      half_range: document.getElementById("half-range").checked,
      stationary: document.getElementById("stationary").checked,
      charged: document.getElementById("charged").checked,
      trials: Number(document.getElementById("simulation-trials").value),
      custom_target_name: document.getElementById("custom-target-name").value || "Custom Target",
      custom_toughness: Number(document.getElementById("custom-target-toughness").value || 0),
      custom_save: Number(document.getElementById("custom-target-save").value || 0),
      custom_invulnerable_save: Number(document.getElementById("custom-target-invuln").value || 0) || null,
      custom_wounds: Number(document.getElementById("custom-target-wounds").value || 0),
      custom_keywords: document
        .getElementById("custom-target-keywords")
        .value.split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    };

    if (state.defenderMode === "datasheet") {
      payload.custom_toughness = null;
      payload.custom_save = null;
      payload.custom_invulnerable_save = null;
      payload.custom_wounds = null;
      payload.custom_keywords = [];
    }

    return payload;
  }

  function setDefenderMode(mode) {
    state.defenderMode = mode;
    elements.segments.forEach((segment) => {
      segment.classList.toggle("active", segment.dataset.mode === mode);
    });
    elements.targetPanels.datasheet.classList.toggle("hidden", mode !== "datasheet");
    elements.targetPanels.custom.classList.toggle("hidden", mode !== "custom");
  }

  async function handleSync() {
    elements.syncButton.disabled = true;
    setSyncStatus("Downloading and importing Wahapedia data…");
    try {
      const result = await fetchJson("/api/sync", { method: "POST", body: JSON.stringify({}) });
      const totalRows = result.tables.reduce((sum, table) => sum + table.rows_imported, 0);
      setSyncStatus(`Sync complete. Imported ${totalRows.toLocaleString()} rows across ${result.tables.length} tables.`);
      state.detailCache.clear();
      await Promise.all([loadDashboard(), loadCatalog()]);
      elements.weaponSelect.innerHTML = "<option value=''>Select an attacker first</option>";
      elements.defenderModelSelect.innerHTML = "<option value=''>Select a target first</option>";
    } catch (error) {
      setSyncStatus(error.message, true);
    } finally {
      elements.syncButton.disabled = false;
    }
  }

  async function handleSimulate(event) {
    event.preventDefault();
    elements.resultsPanel.innerHTML = "<p class='empty-state'>Running simulation…</p>";
    try {
      const payload = buildSimulationPayload();
      const result = await fetchJson("/api/simulate", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      renderSimulationResults(result);
    } catch (error) {
      elements.resultsPanel.innerHTML = `<p class="empty-state" style="color: var(--danger)">${escapeHtml(error.message)}</p>`;
    }
  }

  function attachEvents() {
    elements.syncButton.addEventListener("click", handleSync);
    elements.attackerInput.addEventListener("change", () => void handleAttackerChange());
    elements.defenderInput.addEventListener("change", () => void handleDefenderChange());
    elements.browserSearch.addEventListener("input", renderBrowserList);
    elements.browserFaction.addEventListener("change", renderBrowserList);
    elements.simulationForm.addEventListener("submit", (event) => void handleSimulate(event));
    elements.segments.forEach((segment) => {
      segment.addEventListener("click", () => setDefenderMode(segment.dataset.mode));
    });
  }

  async function init() {
    updateStats(bootstrap.stats);
    attachEvents();
    setDefenderMode("datasheet");
    try {
      await loadCatalog();
      setSyncStatus("Catalogue ready.");
    } catch (error) {
      setSyncStatus(`Catalogue load failed: ${error.message}`, true);
      elements.browserList.innerHTML = "<p class='empty-state'>No datasheets loaded yet. Try refreshing data.</p>";
    }
  }

  void init();
})();
