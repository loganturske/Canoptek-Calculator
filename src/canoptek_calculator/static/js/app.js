(function () {
  const bootstrap = window.__CANOPTEK_BOOTSTRAP__ || {
    factions: [],
    stats: {},
    defaultTrials: 5000,
  };

  const state = {
    datasheets: [],
    datasheetMap: new Map(),
    displayToId: new Map(),
    detailCache: new Map(),
    attackerId: null,
    defenderId: null,
    defenderMode: "datasheet",
    popupAction: null,
    lastFocusedElement: null,
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
    errorPopup: document.getElementById("error-popup"),
    errorTitle: document.getElementById("error-popup-title"),
    errorMessage: document.getElementById("error-popup-message"),
    errorDetails: document.getElementById("error-popup-details"),
    errorDetailText: document.getElementById("error-popup-detail-text"),
    errorClose: document.getElementById("error-popup-close"),
    errorDismiss: document.getElementById("error-popup-dismiss"),
    errorRetry: document.getElementById("error-popup-retry"),
    errorCloseTargets: Array.from(document.querySelectorAll("[data-error-close]")),
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
    document.getElementById("meta-last-download").textContent = formatDate(
      stats.last_downloaded_at,
    );
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

  function setResultsPlaceholder(message, isError = false) {
    const style = isError ? ' style="color: var(--danger)"' : "";
    elements.resultsPanel.innerHTML = `<p class="empty-state"${style}>${escapeHtml(message)}</p>`;
  }

  function resetWeaponSelect(message = "Select an attacker first") {
    elements.weaponSelect.innerHTML = `<option value="">${escapeHtml(message)}</option>`;
  }

  function resetDefenderSelect(message = "Select a target first") {
    elements.defenderModelSelect.innerHTML = `<option value="">${escapeHtml(message)}</option>`;
  }

  function createUiError({ title, message, detail = "", status = null } = {}) {
    const error = new Error(message || "An unexpected error occurred.");
    error.uiTitle = title || "Something went wrong";
    error.uiDetail = detail;
    error.status = status;
    return error;
  }

  function normalizeError(error, fallback = {}) {
    const title =
      (error && typeof error === "object" && error.uiTitle) ||
      fallback.title ||
      "Something went wrong";
    const message =
      (error instanceof Error && error.message) ||
      (typeof error === "string" ? error : "") ||
      fallback.message ||
      "An unexpected error occurred.";
    const detail =
      (error && typeof error === "object" && error.uiDetail) || fallback.detail || "";
    const action =
      (error && typeof error === "object" && error.uiAction) || fallback.action || null;
    const actionLabel =
      (error && typeof error === "object" && error.uiActionLabel) ||
      fallback.actionLabel ||
      "";

    return { title, message, detail, action, actionLabel };
  }

  function showErrorPopup(error, fallback = {}) {
    const descriptor = normalizeError(error, fallback);

    if (elements.errorPopup.hidden) {
      state.lastFocusedElement =
        document.activeElement instanceof HTMLElement ? document.activeElement : null;
    }

    state.popupAction = descriptor.action;
    elements.errorTitle.textContent = descriptor.title;
    elements.errorMessage.textContent = descriptor.message;
    elements.errorDetailText.textContent = descriptor.detail || "";
    elements.errorDetails.open = false;
    elements.errorDetails.hidden = !descriptor.detail;
    elements.errorRetry.hidden = !descriptor.action;
    elements.errorRetry.textContent = descriptor.actionLabel || "Try again";
    elements.errorPopup.hidden = false;
    document.body.classList.add("popup-open");

    const focusTarget = descriptor.action ? elements.errorRetry : elements.errorDismiss;
    window.setTimeout(() => {
      focusTarget.focus();
    }, 0);

    return descriptor;
  }

  function hideErrorPopup() {
    if (elements.errorPopup.hidden) {
      return;
    }

    elements.errorPopup.hidden = true;
    elements.errorRetry.hidden = true;
    elements.errorDetails.hidden = true;
    elements.errorDetailText.textContent = "";
    state.popupAction = null;
    document.body.classList.remove("popup-open");

    if (state.lastFocusedElement && state.lastFocusedElement.isConnected) {
      state.lastFocusedElement.focus();
    }
  }

  async function retryPopupAction() {
    const action = state.popupAction;
    hideErrorPopup();

    if (!action) {
      return;
    }

    try {
      await action();
    } catch (error) {
      showErrorPopup(error);
    }
  }

  function formatValidationIssue(issue) {
    if (!issue || typeof issue !== "object") {
      return String(issue);
    }

    const location = Array.isArray(issue.loc)
      ? issue.loc.filter((part) => part !== "body").join(" > ")
      : "";
    const message = issue.msg || "Invalid value.";
    return location ? `${location}: ${message}` : message;
  }

  function extractErrorFromBody(body) {
    if (typeof body === "string") {
      const text = body.trim();
      if (!text) {
        return { message: "", detail: "" };
      }

      if (text.startsWith("<")) {
        return {
          message: "",
          detail: "The server returned an HTML error page instead of a JSON response.",
        };
      }

      return { message: text, detail: text };
    }

    if (!body) {
      return { message: "", detail: "" };
    }

    const source = body.detail ?? body.message ?? body.error ?? body;

    if (Array.isArray(source)) {
      const detail = source.map((issue) => formatValidationIssue(issue)).join("\n");
      return {
        message: source[0] && source[0].msg ? source[0].msg : "Some values were rejected.",
        detail,
      };
    }

    if (typeof source === "string") {
      return { message: source, detail: source };
    }

    if (source && typeof source === "object") {
      const message = source.message || source.error || "";
      return {
        message,
        detail: JSON.stringify(source, null, 2),
      };
    }

    return { message: "", detail: "" };
  }

  function describeRequestFailure(status) {
    if (status === 400) {
      return "The request could not be processed with the current inputs.";
    }
    if (status === 404) {
      return "The requested Warhammer data could not be found.";
    }
    if (status === 422) {
      return "Some values were invalid. Review the setup and try again.";
    }
    if (status === 429) {
      return "The app is busy right now. Please wait a moment and try again.";
    }
    if (status >= 500) {
      return "The server hit an unexpected error. Please try again shortly.";
    }
    return "The request failed. Please try again.";
  }

  async function fetchJson(url, options = {}, context = {}) {
    const method = options.method || "GET";
    const headers = {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...(options.headers || {}),
    };

    let response;
    try {
      response = await fetch(url, { ...options, headers });
    } catch (error) {
      throw createUiError({
        title: context.title || "Connection failed",
        message:
          navigator.onLine === false
            ? "You appear to be offline. Reconnect and try again."
            : context.networkMessage ||
              "The app could not reach the server. Make sure the service is still running.",
        detail: [
          `Request: ${method} ${url}`,
          error instanceof Error ? error.message : String(error),
        ]
          .filter(Boolean)
          .join("\n"),
      });
    }

    let body = null;
    const contentType = response.headers.get("Content-Type") || "";
    if (response.status !== 204) {
      try {
        body = contentType.includes("json") ? await response.json() : await response.text();
      } catch (error) {
        body = null;
      }
    }

    if (!response.ok) {
      const parsed = extractErrorFromBody(body);
      const detailLines = [`Request: ${method} ${url}`, `Status: ${response.status} ${response.statusText}`];
      if (parsed.detail && parsed.detail !== parsed.message) {
        detailLines.push(parsed.detail);
      }

      throw createUiError({
        title: context.title || "Request failed",
        message: parsed.message || context.message || describeRequestFailure(response.status),
        detail: detailLines.join("\n"),
        status: response.status,
      });
    }

    return body;
  }

  async function loadDashboard() {
    const stats = await fetchJson("/api/dashboard", {}, {
      title: "Dashboard update failed",
      message: "The dashboard stats could not be refreshed.",
    });
    updateStats(stats);
  }

  async function loadCatalog() {
    const datasheets = await fetchJson("/api/datasheets?limit=2500", {}, {
      title: "Catalogue load failed",
      message: "The datasheet catalogue could not be loaded.",
    });
    state.datasheets = datasheets;
    hydrateDatasheetSelectors(datasheets);
    renderBrowserList();
  }

  async function loadDetail(datasheetId) {
    if (state.detailCache.has(datasheetId)) {
      return state.detailCache.get(datasheetId);
    }

    const detail = await fetchJson(`/api/datasheets/${datasheetId}`, {}, {
      title: "Datasheet load failed",
      message: "The selected datasheet could not be loaded.",
    });
    state.detailCache.set(datasheetId, detail);
    return detail;
  }

  async function refreshDashboardAndCatalog() {
    const results = await Promise.allSettled([loadDashboard(), loadCatalog()]);
    const failures = results.filter((result) => result.status === "rejected");
    if (!failures.length) {
      return;
    }

    const detail = failures
      .map((result) => {
        const descriptor = normalizeError(result.reason);
        return [descriptor.title, descriptor.message, descriptor.detail].filter(Boolean).join("\n");
      })
      .join("\n\n");

    throw createUiError({
      title: "Interface refresh failed",
      message: "The data updated, but the page could not refresh every panel cleanly.",
      detail,
    });
  }

  function selectFromInput(inputElement) {
    const datasheetId = state.displayToId.get(inputElement.value);
    return datasheetId || null;
  }

  async function handleAttackerChange() {
    state.attackerId = selectFromInput(elements.attackerInput);
    if (!state.attackerId) {
      resetWeaponSelect("Select a valid attacker");
      return;
    }

    resetWeaponSelect("Loading weapons...");

    try {
      const detail = await loadDetail(state.attackerId);
      const options = detail.weapons.map((weapon) => {
        const disabled = weapon.is_simulatable ? "" : "disabled";
        const suffix = weapon.is_simulatable ? "" : " (unsupported)";
        return `<option value="${weapon.weapon_id}" ${disabled}>${escapeHtml(
          weapon.name,
        )} [${escapeHtml(weapon.weapon_type || "Unknown")}]${suffix}</option>`;
      });
      elements.weaponSelect.innerHTML = options.length
        ? options.join("")
        : "<option value=''>No weapons available</option>";
    } catch (error) {
      state.attackerId = null;
      resetWeaponSelect("Unable to load weapons right now");
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: handleAttackerChange,
      });
    }
  }

  async function handleDefenderChange() {
    state.defenderId = selectFromInput(elements.defenderInput);
    if (!state.defenderId) {
      resetDefenderSelect("Select a valid defender");
      return;
    }

    resetDefenderSelect("Loading model lines...");

    try {
      const detail = await loadDetail(state.defenderId);
      const options = detail.models.map((model) => {
        return `<option value="${model.model_id}">${escapeHtml(model.name)} (T${
          model.toughness ?? "?"
        } / ${model.save ?? "?"}+ / ${model.wounds ?? "?"}W)</option>`;
      });
      elements.defenderModelSelect.innerHTML = options.length
        ? options.join("")
        : "<option value=''>No model lines available</option>";
    } catch (error) {
      state.defenderId = null;
      resetDefenderSelect("Unable to load defender data right now");
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: handleDefenderChange,
      });
    }
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
                <small>${escapeHtml(datasheet.faction_name)} - ${escapeHtml(
                  datasheet.source_name,
                )}${datasheet.role ? ` - ${escapeHtml(datasheet.role)}` : ""}</small>
              </button>
            `,
          )
          .join("")}
      </div>
    `;

    Array.from(elements.browserList.querySelectorAll("[data-datasheet-id]")).forEach((button) => {
      button.addEventListener("click", () => {
        void showDatasheetDetail(button.dataset.datasheetId);
      });
    });
  }

  function normalizeExternalLink(link) {
    if (!link) {
      return null;
    }
    if (link.startsWith("http://") || link.startsWith("https://")) {
      return link;
    }
    if (link.startsWith("/")) {
      return `https://wahapedia.ru${link}`;
    }
    return `https://wahapedia.ru/${link.replace(/^\/+/, "")}`;
  }

  function buildAccordionSection(title, bodyHtml, options = {}) {
    if (!bodyHtml) {
      return "";
    }

    const openAttr = options.open ? " open" : "";
    const countHtml =
      options.count !== undefined && options.count !== null
        ? `<span class="section-badge">${escapeHtml(String(options.count))}</span>`
        : "";
    const auxHtml = options.aux
      ? `<span class="section-aux">${escapeHtml(options.aux)}</span>`
      : "";

    return `
      <details class="datasheet-section ${options.className || ""}"${openAttr}>
        <summary>
          <span class="datasheet-section-title">
            <strong>${escapeHtml(title)}</strong>
            ${countHtml}
            ${auxHtml}
          </span>
          <span class="section-chevron" aria-hidden="true"></span>
        </summary>
        <div class="datasheet-section-body">
          ${bodyHtml}
        </div>
      </details>
    `;
  }

  function renderHtmlSection(title, html, options = {}) {
    if (!html) {
      return "";
    }

    return buildAccordionSection(
      title,
      `<div class="rich-text-block">${html}</div>`,
      options,
    );
  }

  function renderBulletSection(title, items, options = {}) {
    if (!items.length) {
      return "";
    }

    return buildAccordionSection(
      title,
      `<ul class="datasheet-bullets">
        ${items
          .map((item) => `<li>${options.allowHtml ? item : escapeHtml(item)}</li>`)
          .join("")}
      </ul>`,
      {
        count: items.length,
        ...options,
      },
    );
  }

  function renderModelProfiles(models) {
    if (!models.length) {
      return "<p class='empty-state'>No model profiles are available for this datasheet.</p>";
    }

    const statOrder = [
      ["M", (model) => model.movement || "-"],
      ["T", (model) => model.toughness ?? "-"],
      ["Sv", (model) => (model.save ? `${model.save}+` : "-")],
      ["Inv", (model) => (model.invulnerable_save ? `${model.invulnerable_save}+` : "-")],
      ["W", (model) => model.wounds ?? "-"],
      ["Ld", (model) => model.leadership || "-"],
      ["OC", (model) => model.objective_control || "-"],
      ["Base", (model) => model.base_size || "-"],
    ];

    return `
      <div class="model-profile-grid">
        ${models
          .map((model) => {
            const stats = statOrder
              .map(
                ([label, getValue]) => `
                  <div class="profile-stat">
                    <span>${label}</span>
                    <strong>${escapeHtml(String(getValue(model)))}</strong>
                  </div>
                `,
              )
              .join("");

            return `
              <article class="model-profile-card">
                <div class="model-profile-head">
                  <div>
                    <p class="section-label">Model line ${model.line}</p>
                    <h4>${escapeHtml(model.name)}</h4>
                  </div>
                  ${
                    model.base_size_description
                      ? `<span class="profile-pill">${escapeHtml(model.base_size_description)}</span>`
                      : ""
                  }
                </div>
                <div class="model-profile-stats">
                  ${stats}
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    `;
  }

  function isMeleeWeapon(weapon) {
    const weaponType = (weapon.weapon_type || "").toLowerCase();
    const rangeValue = (weapon.range || "").toLowerCase();
    return weaponType.includes("melee") || rangeValue.includes("melee");
  }

  function renderWeaponTable(title, weapons) {
    if (!weapons.length) {
      return "";
    }

    return `
      <section class="weapon-table-card">
        <div class="weapon-table-header">
          <p class="section-label">${escapeHtml(title)}</p>
          <span class="profile-pill">${weapons.length} profiles</span>
        </div>
        <table class="data-table weapon-table">
          <thead>
            <tr><th>Weapon</th><th>Range</th><th>A</th><th>Skill</th><th>S</th><th>AP</th><th>D</th></tr>
          </thead>
          <tbody>
            ${weapons
              .map((weapon) => {
                const supportedRules = weapon.rules
                  .map((rule) => `<span class="chip chip-supported">${escapeHtml(rule)}</span>`)
                  .join("");
                const ignoredRules = weapon.ignored_rules
                  .map((rule) => `<span class="chip chip-ignored">${escapeHtml(rule)}</span>`)
                  .join("");
                const warning = !weapon.is_simulatable && weapon.simulation_issue
                  ? `<p class="weapon-note weapon-note-warning">${escapeHtml(weapon.simulation_issue)}</p>`
                  : "";

                return `
                  <tr>
                    <td class="weapon-name-cell">
                      <div class="weapon-name-row">
                        <strong>${escapeHtml(weapon.name)}</strong>
                        ${
                          weapon.weapon_type
                            ? `<span class="profile-pill">${escapeHtml(weapon.weapon_type)}</span>`
                            : ""
                        }
                      </div>
                      ${
                        weapon.description_html
                          ? `<div class="weapon-note rich-text-inline">${weapon.description_html}</div>`
                          : ""
                      }
                      ${
                        supportedRules || ignoredRules
                          ? `<div class="rule-list compact-rule-list">${supportedRules}${ignoredRules}</div>`
                          : ""
                      }
                      ${warning}
                    </td>
                    <td>${escapeHtml(weapon.range || "-")}</td>
                    <td>${escapeHtml(weapon.attacks || "-")}</td>
                    <td>${escapeHtml(weapon.skill || "-")}</td>
                    <td>${escapeHtml(weapon.strength || "-")}</td>
                    <td>${escapeHtml(weapon.armour_penetration || "-")}</td>
                    <td>${escapeHtml(weapon.damage || "-")}</td>
                  </tr>
                `;
              })
              .join("")}
          </tbody>
        </table>
      </section>
    `;
  }

  function renderAbilitySection(abilities) {
    if (!abilities.length) {
      return "";
    }

    const body = `
      <div class="ability-stack">
        ${abilities
          .map((ability, index) => {
            const meta = [ability.ability_type, ability.model].filter(Boolean);
            return `
              <details class="ability-entry"${index === 0 ? " open" : ""}>
                <summary>
                  <span class="ability-heading">
                    <strong>${escapeHtml(ability.name)}</strong>
                    <span class="ability-meta">
                      ${meta
                        .map((value) => `<span class="chip chip-supported">${escapeHtml(value)}</span>`)
                        .join("")}
                      ${
                        ability.parameter
                          ? `<code>${escapeHtml(ability.parameter)}</code>`
                          : ""
                      }
                    </span>
                  </span>
                  <span class="section-chevron" aria-hidden="true"></span>
                </summary>
                <div class="ability-body rich-text-block">
                  ${ability.description_html || "<p>No rules text is available for this ability.</p>"}
                </div>
              </details>
            `;
          })
          .join("")}
      </div>
    `;

    return buildAccordionSection("Abilities", body, {
      count: abilities.length,
      open: true,
      className: "datasheet-section-highlight",
    });
  }

  function renderRuleCard(rule, options = {}) {
    return `
      <article class="rule-card ${options.className || ""}">
        <div class="rule-card-head">
          <div>
            <h4>${escapeHtml(rule.name)}</h4>
            ${
              rule.subtitle
                ? `<p class="rule-card-subtitle">${escapeHtml(rule.subtitle)}</p>`
                : ""
            }
          </div>
          <div class="rule-card-flags">
            ${
              rule.cost !== null
                ? `<span class="profile-pill">${rule.cost} ${escapeHtml(options.costLabel || "pts")}</span>`
                : ""
            }
          </div>
        </div>
        ${
          rule.description_html
            ? `<div class="rule-card-body rich-text-block">${rule.description_html}</div>`
            : "<p class='empty-state'>No additional rules text is listed.</p>"
        }
      </article>
    `;
  }

  function renderRuleSection(title, rules, options = {}) {
    if (!rules.length) {
      return "";
    }

    return buildAccordionSection(
      title,
      `<div class="rule-card-grid">
        ${rules.map((rule) => renderRuleCard(rule, options)).join("")}
      </div>`,
      {
        count: rules.length,
        ...options,
      },
    );
  }

  function renderDetail(detail) {
    const sourceLink = normalizeExternalLink(detail.link);
    const costStrip = detail.costs.length
      ? `
        <div class="detail-cost-strip">
          ${detail.costs
            .map((cost) => {
              const description = cost.description ? escapeHtml(cost.description) : "Unit cost";
              const amount = cost.cost !== null ? `${cost.cost} pts` : "Variable";
              return `
                <div class="cost-pill">
                  <span>${description}</span>
                  <strong>${escapeHtml(amount)}</strong>
                </div>
              `;
            })
            .join("")}
        </div>
      `
      : "";

    const introMeta = [detail.source_name, detail.role].filter(Boolean);
    const rangedWeapons = detail.weapons.filter((weapon) => !isMeleeWeapon(weapon));
    const meleeWeapons = detail.weapons.filter((weapon) => isMeleeWeapon(weapon));
    const leaderRulesHtml = [detail.leader_head_html, detail.leader_footer_html]
      .filter(Boolean)
      .join("");

    const secondarySections = [
      renderAbilitySection(detail.abilities),
      renderHtmlSection("Loadout", detail.loadout_html, { open: true }),
      renderBulletSection("Unit composition", detail.unit_composition, { open: true }),
      renderBulletSection(
        "Wargear options",
        detail.options.map((option) => {
          return `${option.button ? `<strong>${escapeHtml(option.button)}</strong> ` : ""}${
            option.description_html || ""
          }`;
        }),
        { allowHtml: true, count: detail.options.length },
      ),
      renderHtmlSection("Transport rules", detail.transport_html),
      renderHtmlSection("Leader rules", leaderRulesHtml),
      renderHtmlSection("Damaged profile", detail.damaged_profile_html, {
        aux: detail.damaged_profile_label,
      }),
      renderRuleSection("Stratagems", detail.stratagems, {
        costLabel: "CP",
      }),
      renderRuleSection("Enhancements", detail.enhancements, {
        costLabel: "pts",
      }),
      renderRuleSection("Detachment abilities", detail.detachment_abilities),
    ]
      .filter(Boolean)
      .join("");

    elements.datasheetDetail.innerHTML = `
      <div class="detail-stack necron-datasheet">
        <section class="detail-hero-panel">
          <div class="detail-hero-main">
            <p class="section-label">${escapeHtml(detail.faction_name)}</p>
            <h2>${escapeHtml(detail.name)}</h2>
            <p class="detail-subtitle">
              ${introMeta.map((item) => escapeHtml(item)).join(" - ")}
            </p>
            ${detail.legend_html ? `<div class="detail-legend rich-text-block">${detail.legend_html}</div>` : ""}
            ${costStrip}
          </div>
          <aside class="detail-hero-side">
            <div class="detail-link-row">
              ${
                sourceLink
                  ? `<a class="button button-secondary detail-link" href="${escapeHtml(
                      sourceLink,
                    )}" target="_blank" rel="noreferrer">Open Wahapedia entry</a>`
                  : ""
              }
            </div>
            <div class="keyword-cloud">
              ${detail.keywords
                .map((keyword) => `<span class="chip chip-supported">${escapeHtml(keyword)}</span>`)
                .join("")}
            </div>
          </aside>
        </section>

        <section class="detail-block detail-profile-bank">
          <div class="detail-block-head">
            <div>
              <p class="section-label">Profile matrix</p>
              <h3>Model characteristics</h3>
            </div>
            <span class="profile-pill">${detail.models.length} model lines</span>
          </div>
          ${renderModelProfiles(detail.models)}
        </section>

        <section class="detail-block detail-weapon-bank">
          <div class="detail-block-head">
            <div>
              <p class="section-label">Weapon matrix</p>
              <h3>Weapons and simulation tags</h3>
            </div>
            <span class="profile-pill">${detail.weapons.length} total profiles</span>
          </div>
          <div class="weapon-bank-grid">
            ${renderWeaponTable("Ranged weapons", rangedWeapons)}
            ${renderWeaponTable("Melee weapons", meleeWeapons)}
            ${
              !detail.weapons.length
                ? "<p class='empty-state'>No weapon profiles are available for this datasheet.</p>"
                : ""
            }
          </div>
        </section>

        <div class="datasheet-section-stack">
          ${secondarySections}
        </div>
      </div>
    `;
  }

  function renderSimulationResults(result) {
    const maxProbability = Math.max(
      ...result.monte_carlo.histogram.map((bucket) => bucket.probability),
      0.0001,
    );
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
            <div class="metric"><span>Effective hit / wound mod</span><strong>${
              result.effective_hit_modifier >= 0 ? "+" : ""
            }${result.effective_hit_modifier} / ${
              result.effective_wound_modifier >= 0 ? "+" : ""
            }${result.effective_wound_modifier}</strong></div>
          </div>
          <div class="rule-list">
            ${result.supported_rules
              .map((rule) => `<span class="chip chip-supported">${escapeHtml(rule)}</span>`)
              .join("")}
            ${result.ignored_rules
              .map((rule) => `<span class="chip chip-ignored">${escapeHtml(rule)}</span>`)
              .join("")}
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

  async function showDatasheetDetail(datasheetId) {
    elements.datasheetDetail.innerHTML = "<p class='empty-state'>Loading datasheet...</p>";

    try {
      const detail = await loadDetail(datasheetId);
      renderDetail(detail);
    } catch (error) {
      elements.datasheetDetail.innerHTML =
        "<p class='empty-state'>We could not load that datasheet right now.</p>";
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: () => showDatasheetDetail(datasheetId),
      });
    }
  }

  function readNumberValue(id) {
    const value = Number(document.getElementById(id).value);
    return Number.isFinite(value) ? value : 0;
  }

  function readOptionalNumberValue(id) {
    const rawValue = document.getElementById(id).value.trim();
    if (!rawValue) {
      return null;
    }

    const value = Number(rawValue);
    return Number.isFinite(value) ? value : null;
  }

  function buildSimulationPayload() {
    const trimmedName = document.getElementById("custom-target-name").value.trim();

    const payload = {
      attacker_weapon_id: Number(elements.weaponSelect.value),
      attacker_models: readNumberValue("attacker-models"),
      defender_mode: state.defenderMode,
      defender_model_id:
        state.defenderMode === "datasheet" ? Number(elements.defenderModelSelect.value) : null,
      target_model_count: readNumberValue("target-model-count"),
      defender_in_cover: document.getElementById("target-cover").checked,
      hit_reroll: document.getElementById("hit-reroll").value,
      wound_reroll: document.getElementById("wound-reroll").value,
      hit_modifier: readNumberValue("hit-modifier"),
      wound_modifier: readNumberValue("wound-modifier"),
      half_range: document.getElementById("half-range").checked,
      stationary: document.getElementById("stationary").checked,
      charged: document.getElementById("charged").checked,
      trials: readNumberValue("simulation-trials"),
      custom_target_name: trimmedName || "Custom Target",
      custom_toughness: readNumberValue("custom-target-toughness"),
      custom_save: readNumberValue("custom-target-save"),
      custom_invulnerable_save: readOptionalNumberValue("custom-target-invuln"),
      custom_wounds: readNumberValue("custom-target-wounds"),
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

  function validateSimulationPayload(payload) {
    const issues = [];

    if (!state.attackerId) {
      issues.push("Choose a valid attacker datasheet.");
    }
    if (!payload.attacker_weapon_id) {
      issues.push("Choose a weapon profile before running the simulation.");
    }
    if (payload.attacker_models < 1) {
      issues.push("Attacking models must be at least 1.");
    }
    if (payload.trials < 100) {
      issues.push("Trials must be at least 100.");
    }
    if (payload.target_model_count < 1) {
      issues.push("Target models in unit must be at least 1.");
    }

    if (payload.defender_mode === "datasheet") {
      if (!state.defenderId) {
        issues.push("Choose a valid defender datasheet.");
      }
      if (!payload.defender_model_id) {
        issues.push("Choose a defender model line.");
      }
      return issues;
    }

    if (!payload.custom_target_name.trim()) {
      issues.push("Enter a custom target name.");
    }
    if (payload.custom_toughness < 1) {
      issues.push("Custom target toughness must be at least 1.");
    }
    if (payload.custom_save < 2 || payload.custom_save > 7) {
      issues.push("Custom target save must be between 2 and 7.");
    }
    if (
      payload.custom_invulnerable_save !== null &&
      (payload.custom_invulnerable_save < 2 || payload.custom_invulnerable_save > 7)
    ) {
      issues.push("Invulnerable saves must be between 2 and 7 when provided.");
    }
    if (payload.custom_wounds < 1) {
      issues.push("Custom target wounds must be at least 1.");
    }

    return issues;
  }

  function setDefenderMode(mode) {
    state.defenderMode = mode;
    elements.segments.forEach((segment) => {
      segment.classList.toggle("active", segment.dataset.mode === mode);
    });
    elements.targetPanels.datasheet.classList.toggle("hidden", mode !== "datasheet");
    elements.targetPanels.custom.classList.toggle("hidden", mode !== "custom");
  }

  async function loadInitialData() {
    await loadCatalog();
    setSyncStatus("Catalogue ready.");
  }

  async function runSync() {
    elements.syncButton.disabled = true;
    setSyncStatus("Downloading and importing Wahapedia data...");

    try {
      const result = await fetchJson(
        "/api/sync",
        {
          method: "POST",
          body: JSON.stringify({}),
        },
        {
          title: "Data sync failed",
          message: "Wahapedia data could not be refreshed.",
        },
      );

      const totalRows = result.tables.reduce((sum, table) => sum + table.rows_imported, 0);
      state.detailCache.clear();
      resetWeaponSelect();
      resetDefenderSelect();

      try {
        await refreshDashboardAndCatalog();
        setSyncStatus(
          `Sync complete. Imported ${totalRows.toLocaleString()} rows across ${result.tables.length} tables.`,
        );
      } catch (error) {
        setSyncStatus(
          "Data sync finished, but the page could not refresh all live panels.",
          true,
        );
        showErrorPopup(error, {
          actionLabel: "Try again",
          action: refreshDashboardAndCatalog,
        });
      }
    } catch (error) {
      const descriptor = showErrorPopup(error, {
        actionLabel: "Try again",
        action: runSync,
      });
      setSyncStatus(descriptor.message, true);
    } finally {
      elements.syncButton.disabled = false;
    }
  }

  async function runSimulation() {
    const payload = buildSimulationPayload();
    const issues = validateSimulationPayload(payload);

    if (issues.length) {
      const error = createUiError({
        title: "Simulation setup incomplete",
        message: issues[0],
        detail: issues.map((issue, index) => `${index + 1}. ${issue}`).join("\n"),
      });
      setResultsPlaceholder("Fix the setup issue and run the simulation again.", true);
      showErrorPopup(error);
      return;
    }

    setResultsPlaceholder("Running simulation...");

    try {
      const result = await fetchJson(
        "/api/simulate",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        {
          title: "Simulation failed",
          message: "The attack sequence could not be simulated.",
        },
      );
      renderSimulationResults(result);
    } catch (error) {
      setResultsPlaceholder(
        "The simulation could not be completed. Open the error message for details.",
        true,
      );
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: runSimulation,
      });
    }
  }

  function attachPopupEvents() {
    elements.errorClose.addEventListener("click", hideErrorPopup);
    elements.errorDismiss.addEventListener("click", hideErrorPopup);
    elements.errorRetry.addEventListener("click", () => {
      void retryPopupAction();
    });
    elements.errorCloseTargets.forEach((element) => {
      element.addEventListener("click", hideErrorPopup);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && !elements.errorPopup.hidden) {
        hideErrorPopup();
      }
    });
  }

  function attachGlobalErrorHandlers() {
    window.addEventListener("error", (event) => {
      const detail =
        event.error && event.error.stack
          ? event.error.stack
          : event.message || "Unknown browser error.";
      showErrorPopup(
        createUiError({
          title: "Unexpected interface error",
          message:
            "The page ran into an unexpected problem. You can try again or refresh the browser.",
          detail,
        }),
      );
    });

    window.addEventListener("unhandledrejection", (event) => {
      event.preventDefault();
      if (event.reason instanceof Error) {
        showErrorPopup(event.reason);
        return;
      }

      showErrorPopup(
        createUiError({
          title: "Unexpected background error",
          message:
            "A background action failed unexpectedly. Try the action again or refresh the page.",
          detail: String(event.reason ?? "Unknown promise rejection."),
        }),
      );
    });
  }

  function attachEvents() {
    attachPopupEvents();
    attachGlobalErrorHandlers();

    elements.syncButton.addEventListener("click", () => {
      void runSync();
    });
    elements.attackerInput.addEventListener("change", () => {
      void handleAttackerChange();
    });
    elements.defenderInput.addEventListener("change", () => {
      void handleDefenderChange();
    });
    elements.browserSearch.addEventListener("input", renderBrowserList);
    elements.browserFaction.addEventListener("change", renderBrowserList);
    elements.simulationForm.addEventListener("submit", (event) => {
      event.preventDefault();
      void runSimulation();
    });
    elements.segments.forEach((segment) => {
      segment.addEventListener("click", () => setDefenderMode(segment.dataset.mode));
    });
  }

  async function init() {
    updateStats(bootstrap.stats);
    attachEvents();
    setDefenderMode("datasheet");
    resetWeaponSelect();
    resetDefenderSelect();

    try {
      await loadInitialData();
    } catch (error) {
      setSyncStatus("Catalogue load failed. Open the error message for details.", true);
      elements.browserList.innerHTML =
        "<p class='empty-state'>No datasheets loaded yet. Try refreshing data.</p>";
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: loadInitialData,
      });
    }
  }

  void init();
})();
