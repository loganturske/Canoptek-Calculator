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
    armyLists: [],
    armyListMap: new Map(),
    armyListDetailCache: new Map(),
    selectedArmyListId: null,
    editingArmyEntryId: null,
    editingArmyEntrySnapshot: null,
    armyEntryDatasheetId: null,
    attackerBuildPreview: null,
    attackerEffectSelections: new Set(),
    attackerId: null,
    defenderId: null,
    defenderMode: "datasheet",
    popupAction: null,
    lastFocusedElement: null,
    activeWorkspaceTab: "workbench",
  };

  const elements = {
    syncButton: document.getElementById("sync-button"),
    syncStatus: document.getElementById("sync-status"),
    datalist: document.getElementById("datasheet-options"),
    attackerInput: document.getElementById("attacker-input"),
    attackerModelsInput: document.getElementById("attacker-models"),
    attackerLeaderSelect: document.getElementById("attacker-leader-select"),
    attackerBuildStatus: document.getElementById("attacker-build-status"),
    attackerBuildEffects: document.getElementById("attacker-build-effects"),
    defenderInput: document.getElementById("defender-input"),
    targetModelCountInput: document.getElementById("target-model-count"),
    weaponSelect: document.getElementById("weapon-select"),
    defenderModelSelect: document.getElementById("defender-model-select"),
    simulationForm: document.getElementById("simulation-form"),
    resultsPanel: document.getElementById("results-panel"),
    armyListSelect: document.getElementById("army-list-select"),
    armyListName: document.getElementById("army-list-name"),
    armyListFaction: document.getElementById("army-list-faction"),
    armyListNotes: document.getElementById("army-list-notes"),
    armyListStatus: document.getElementById("army-list-status"),
    armyListSummary: document.getElementById("army-list-summary"),
    armyListEntries: document.getElementById("army-list-entries"),
    armyListNew: document.getElementById("army-list-new"),
    armyListCreate: document.getElementById("army-list-create"),
    armyListSave: document.getElementById("army-list-save"),
    armyListDelete: document.getElementById("army-list-delete"),
    armyEntryForm: document.getElementById("army-entry-form"),
    armyEntryDatasheet: document.getElementById("army-entry-datasheet"),
    armyEntryModel: document.getElementById("army-entry-model"),
    armyEntryUnitSize: document.getElementById("army-entry-unit-size"),
    armyEntryQuantity: document.getElementById("army-entry-quantity"),
    armyEntryCost: document.getElementById("army-entry-cost"),
    armyEntryPoints: document.getElementById("army-entry-points"),
    armyEntrySortOrder: document.getElementById("army-entry-sort-order"),
    armyEntryNickname: document.getElementById("army-entry-nickname"),
    armyEntryNotes: document.getElementById("army-entry-notes"),
    armyEntryContext: document.getElementById("army-entry-context"),
    armyEntrySubmit: document.getElementById("army-entry-submit"),
    armyEntryClear: document.getElementById("army-entry-clear"),
    simAttackerList: document.getElementById("sim-attacker-list"),
    simAttackerEntry: document.getElementById("sim-attacker-entry"),
    simDefenderList: document.getElementById("sim-defender-list"),
    simDefenderEntry: document.getElementById("sim-defender-entry"),
    simLoadAttacker: document.getElementById("sim-load-attacker"),
    simLoadDefender: document.getElementById("sim-load-defender"),
    browserSearch: document.getElementById("browser-search"),
    browserFaction: document.getElementById("browser-faction"),
    browserList: document.getElementById("browser-list"),
    datasheetDetail: document.getElementById("datasheet-detail"),
    workspaceTabs: Array.from(document.querySelectorAll("[data-workspace-tab]")),
    workspacePanels: Array.from(document.querySelectorAll("[data-workspace-panel]")),
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

  const workspaceTabIds = ["workbench", "roster"];

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

  function normalizeWorkspaceTab(tabId) {
    return workspaceTabIds.includes(tabId) ? tabId : "workbench";
  }

  function readWorkspaceTabFromHash() {
    return normalizeWorkspaceTab(window.location.hash.replace(/^#/, ""));
  }

  function updateWorkspaceTabHash(tabId) {
    const nextUrl = new URL(window.location.href);
    nextUrl.hash = tabId;

    if (window.history && typeof window.history.replaceState === "function") {
      window.history.replaceState(null, "", nextUrl.toString());
      return;
    }

    window.location.hash = tabId;
  }

  function setActiveWorkspaceTab(tabId, { updateHash = true } = {}) {
    const normalizedTab = normalizeWorkspaceTab(tabId);
    state.activeWorkspaceTab = normalizedTab;

    elements.workspaceTabs.forEach((tab) => {
      const isActive = tab.dataset.workspaceTab === normalizedTab;
      tab.classList.toggle("is-active", isActive);
      tab.setAttribute("aria-selected", isActive ? "true" : "false");
      tab.tabIndex = isActive ? 0 : -1;
    });

    elements.workspacePanels.forEach((panel) => {
      panel.hidden = panel.dataset.workspacePanel !== normalizedTab;
    });

    if (updateHash) {
      updateWorkspaceTabHash(normalizedTab);
    }
  }

  function moveWorkspaceTabFocus(currentTabId, direction) {
    const currentIndex = workspaceTabIds.indexOf(normalizeWorkspaceTab(currentTabId));
    const nextIndex = (currentIndex + direction + workspaceTabIds.length) % workspaceTabIds.length;
    const nextTabId = workspaceTabIds[nextIndex];
    const nextTab = elements.workspaceTabs.find((tab) => tab.dataset.workspaceTab === nextTabId);

    if (!nextTab) {
      return;
    }

    setActiveWorkspaceTab(nextTabId);
    nextTab.focus();
  }

  function handleWorkspaceTabKeydown(event) {
    const currentTabId = event.currentTarget.dataset.workspaceTab;

    if (event.key === "ArrowRight" || event.key === "ArrowDown") {
      event.preventDefault();
      moveWorkspaceTabFocus(currentTabId, 1);
      return;
    }

    if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
      event.preventDefault();
      moveWorkspaceTabFocus(currentTabId, -1);
      return;
    }

    if (event.key === "Home") {
      event.preventDefault();
      setActiveWorkspaceTab(workspaceTabIds[0]);
      elements.workspaceTabs[0]?.focus();
      return;
    }

    if (event.key === "End") {
      event.preventDefault();
      const lastIndex = workspaceTabIds.length - 1;
      setActiveWorkspaceTab(workspaceTabIds[lastIndex]);
      elements.workspaceTabs[lastIndex]?.focus();
    }
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

  function setArmyListStatus(message, isError = false) {
    elements.armyListStatus.textContent = message;
    elements.armyListStatus.style.color = isError ? "var(--danger)" : "";
  }

  function setArmyEntryContext(message, isError = false) {
    elements.armyEntryContext.textContent = message;
    elements.armyEntryContext.style.color = isError ? "var(--danger)" : "";
  }

  function resetArmyEntryModelSelect(message = "Select a datasheet first") {
    elements.armyEntryModel.innerHTML = `<option value="">${escapeHtml(message)}</option>`;
  }

  function resetArmyEntryCostSelect(message = "Select a datasheet first") {
    elements.armyEntryCost.innerHTML = `<option value="">${escapeHtml(message)}</option>`;
  }

  function setArmyEntryEditorEnabled(enabled) {
    Array.from(
      elements.armyEntryForm.querySelectorAll("input, select, textarea, button"),
    ).forEach((control) => {
      control.disabled = !enabled;
    });
    elements.armyEntryClear.disabled = !enabled;
  }

  function clearArmyEntrySelection() {
    state.armyEntryDatasheetId = null;
    delete elements.armyEntryDatasheet.dataset.selectedId;
  }

  function setArmyEntrySelection(datasheetId, fallbackName = "") {
    state.armyEntryDatasheetId = datasheetId || null;

    if (!datasheetId) {
      delete elements.armyEntryDatasheet.dataset.selectedId;
      elements.armyEntryDatasheet.value = "";
      return;
    }

    const summary = state.datasheetMap.get(datasheetId);
    elements.armyEntryDatasheet.dataset.selectedId = datasheetId;
    elements.armyEntryDatasheet.value = summary
      ? buildDisplayLabel(summary)
      : fallbackName || datasheetId;
  }

  function resolveArmyEntryDatasheetId() {
    const matchedId = state.displayToId.get(elements.armyEntryDatasheet.value);
    if (matchedId) {
      state.armyEntryDatasheetId = matchedId;
      elements.armyEntryDatasheet.dataset.selectedId = matchedId;
      return matchedId;
    }

    const storedId = elements.armyEntryDatasheet.dataset.selectedId || state.armyEntryDatasheetId;
    return storedId || null;
  }

  function parseUnitSizeFromCostLabel(label) {
    if (!label) {
      return null;
    }

    const explicitMatch = label.match(/(\d+)\s*models?/i);
    if (explicitMatch) {
      return Number(explicitMatch[1]);
    }

    const fallbackMatch = label.match(/\d+/);
    return fallbackMatch ? Number(fallbackMatch[0]) : null;
  }

  function readIntegerFromElement(element, fallback = 0) {
    const value = Number(element.value);
    return Number.isFinite(value) ? value : fallback;
  }

  function readOptionalIntegerFromElement(element) {
    const rawValue = element.value.trim();
    if (!rawValue) {
      return null;
    }

    const value = Number(rawValue);
    return Number.isFinite(value) ? value : null;
  }

  function normalizeOptionalText(value) {
    const trimmed = String(value || "").trim();
    return trimmed || null;
  }

  function formatTrackedPoints(totalPoints, hasUnpricedEntries = false) {
    if (hasUnpricedEntries) {
      return `${totalPoints} pts tracked`;
    }
    return `${totalPoints} pts`;
  }

  function buildArmyListOptionLabel(armyList) {
    const warnings = [];
    if (armyList.has_unpriced_entries) {
      warnings.push("partial");
    }
    if (armyList.has_stale_entries) {
      warnings.push("stale");
    }

    const suffix = warnings.length ? ` :: ${warnings.join(", ")}` : "";
    return `${armyList.name} :: ${armyList.faction_name} :: ${formatTrackedPoints(
      armyList.total_points,
      armyList.has_unpriced_entries,
    )}${suffix}`;
  }

  function populateArmyListSelect(selectElement, placeholder, selectedValue = "") {
    selectElement.innerHTML = "";

    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = placeholder;
    selectElement.appendChild(placeholderOption);

    state.armyLists.forEach((armyList) => {
      const option = document.createElement("option");
      option.value = String(armyList.id);
      option.textContent = buildArmyListOptionLabel(armyList);
      selectElement.appendChild(option);
    });

    selectElement.value = selectedValue ? String(selectedValue) : "";
  }

  function syncArmyListSelectors() {
    const currentArmyListId = state.selectedArmyListId ? String(state.selectedArmyListId) : "";
    const attackerListId = elements.simAttackerList.value;
    const defenderListId = elements.simDefenderList.value;

    populateArmyListSelect(elements.armyListSelect, "Create a new list", currentArmyListId);
    populateArmyListSelect(elements.simAttackerList, "Choose a saved list", attackerListId);
    populateArmyListSelect(elements.simDefenderList, "Choose a saved list", defenderListId);
  }

  async function loadArmyLists() {
    const armyLists = await fetchJson("/api/army-lists", {}, {
      title: "Roster load failed",
      message: "Saved army lists could not be loaded.",
    });

    state.armyLists = armyLists;
    state.armyListMap.clear();
    armyLists.forEach((armyList) => {
      state.armyListMap.set(armyList.id, armyList);
    });
    syncArmyListSelectors();
    return armyLists;
  }

  async function loadArmyListDetail(armyListId, { force = false } = {}) {
    const key = Number(armyListId);
    if (!force && state.armyListDetailCache.has(key)) {
      return state.armyListDetailCache.get(key);
    }

    const detail = await fetchJson(`/api/army-lists/${key}`, {}, {
      title: "Roster load failed",
      message: "The selected army list could not be loaded.",
    });
    state.armyListDetailCache.set(key, detail);
    return detail;
  }

  async function loadSimulationEntryOptions(side, armyListId) {
    const entrySelect =
      side === "attacker" ? elements.simAttackerEntry : elements.simDefenderEntry;

    if (!armyListId) {
      entrySelect.innerHTML = "<option value=''>Choose a list first</option>";
      return;
    }

    entrySelect.innerHTML = "<option value=''>Loading units...</option>";

    try {
      const detail = await loadArmyListDetail(Number(armyListId));
      entrySelect.innerHTML = "";

      const placeholderOption = document.createElement("option");
      placeholderOption.value = "";
      placeholderOption.textContent = detail.entries.length
        ? "Choose a saved unit"
        : "No units saved in this list";
      entrySelect.appendChild(placeholderOption);

      detail.entries.forEach((entry) => {
        const option = document.createElement("option");
        option.value = String(entry.id);
        option.textContent = `${entry.display_name} :: ${entry.unit_size} models${
          entry.quantity > 1 ? ` x${entry.quantity}` : ""
        }`;
        option.disabled = !entry.datasheet_available;
        entrySelect.appendChild(option);
      });
    } catch (error) {
      entrySelect.innerHTML = "<option value=''>Unable to load units</option>";
      throw error;
    }
  }

  function renderArmyListSummary(detail) {
    const warningChips = [
      detail.faction_available ? "" : "<span class='chip chip-ignored'>Faction data missing</span>",
      detail.has_unpriced_entries
        ? "<span class='chip chip-ignored'>Points total is partial</span>"
        : "<span class='chip chip-supported'>Points fully tracked</span>",
      detail.has_stale_entries
        ? "<span class='chip chip-ignored'>Some units need attention</span>"
        : "<span class='chip chip-supported'>All unit references resolved</span>",
    ]
      .filter(Boolean)
      .join("");

    const updatedLabel = formatDate(detail.updated_at);
    elements.armyListSummary.innerHTML = `
      <div class="army-summary-shell">
        <div class="army-summary-head">
          <div>
            <p class="section-label">${escapeHtml(detail.faction_name)}</p>
            <h3>${escapeHtml(detail.name)}</h3>
            <p class="army-summary-meta">Updated ${escapeHtml(updatedLabel)}</p>
          </div>
          <div class="rule-list">
            ${warningChips}
          </div>
        </div>
        <div class="army-summary-grid">
          <article class="summary-tile">
            <span>Points</span>
            <strong>${escapeHtml(formatTrackedPoints(detail.total_points, detail.has_unpriced_entries))}</strong>
          </article>
          <article class="summary-tile">
            <span>Units</span>
            <strong>${detail.total_units}</strong>
          </article>
          <article class="summary-tile">
            <span>Models</span>
            <strong>${detail.total_models}</strong>
          </article>
          <article class="summary-tile">
            <span>Entries</span>
            <strong>${detail.entry_count}</strong>
          </article>
        </div>
        ${
          detail.notes
            ? `<p class="army-summary-notes">${escapeHtml(detail.notes)}</p>`
            : ""
        }
      </div>
    `;
  }

  function renderArmyListEntries(detail) {
    if (!detail.entries.length) {
      elements.armyListEntries.innerHTML =
        "<p class='empty-state'>No units added yet. Use the editor to add a datasheet, unit size, and points profile.</p>";
      return;
    }

    elements.armyListEntries.innerHTML = `
      <div class="army-entry-list">
        ${detail.entries
          .map((entry) => {
            const warningHtml = entry.reference_warning
              ? `<p class="entry-warning">${escapeHtml(entry.reference_warning)}</p>`
              : "";
            const pointLabel =
              entry.total_points === null
                ? "Unpriced"
                : `${entry.total_points} pts total`;

            return `
              <article class="army-entry-card ${entry.reference_warning ? "is-warning" : ""}">
                <div class="army-entry-head">
                  <div>
                    <p class="section-label">${escapeHtml(entry.datasheet_name)}</p>
                    <h4>${escapeHtml(entry.display_name)}</h4>
                  </div>
                  <div class="army-entry-meta">
                    ${
                      entry.datasheet_role
                        ? `<span class="profile-pill">${escapeHtml(entry.datasheet_role)}</span>`
                        : ""
                    }
                    ${
                      entry.cost_label
                        ? `<span class="profile-pill">${escapeHtml(entry.cost_label)}</span>`
                        : ""
                    }
                  </div>
                </div>
                <div class="army-entry-stats">
                  <div class="entry-stat">
                    <span>Unit size</span>
                    <strong>${entry.unit_size}</strong>
                  </div>
                  <div class="entry-stat">
                    <span>Quantity</span>
                    <strong>${entry.quantity}</strong>
                  </div>
                  <div class="entry-stat">
                    <span>Models tracked</span>
                    <strong>${entry.entry_model_count}</strong>
                  </div>
                  <div class="entry-stat">
                    <span>Points</span>
                    <strong>${escapeHtml(pointLabel)}</strong>
                  </div>
                </div>
                ${
                  entry.model_name
                    ? `<p class="entry-note">Model line: ${escapeHtml(entry.model_name)}${
                        entry.model_available === false ? " (missing in current data)" : ""
                      }</p>`
                    : ""
                }
                ${entry.notes ? `<p class="entry-note">${escapeHtml(entry.notes)}</p>` : ""}
                ${warningHtml}
                <div class="button-row">
                  <button class="button button-secondary" type="button" data-entry-action="view" data-entry-id="${entry.id}" ${
                    entry.datasheet_available ? "" : "disabled"
                  }>Inspect datasheet</button>
                  <button class="button button-secondary" type="button" data-entry-action="edit" data-entry-id="${entry.id}">Edit</button>
                  <button class="button button-secondary" type="button" data-entry-action="attacker" data-entry-id="${entry.id}" ${
                    entry.datasheet_available ? "" : "disabled"
                  }>Use as attacker</button>
                  <button class="button button-secondary" type="button" data-entry-action="defender" data-entry-id="${entry.id}" ${
                    entry.datasheet_available ? "" : "disabled"
                  }>Use as defender</button>
                  <button class="button button-danger" type="button" data-entry-action="delete" data-entry-id="${entry.id}">Remove</button>
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    `;

    Array.from(elements.armyListEntries.querySelectorAll("[data-entry-action]")).forEach((button) => {
      button.addEventListener("click", () => {
        const entryId = Number(button.dataset.entryId);
        if (!Number.isFinite(entryId)) {
          return;
        }

        if (button.dataset.entryAction === "view") {
          const entry = detail.entries.find((item) => item.id === entryId);
          if (entry) {
            void showDatasheetDetail(entry.datasheet_id);
          }
          return;
        }

        if (button.dataset.entryAction === "edit") {
          void startEditingArmyEntry(entryId);
          return;
        }

        if (button.dataset.entryAction === "attacker") {
          void loadArmyEntryIntoSimulation(entryId, "attacker");
          return;
        }

        if (button.dataset.entryAction === "defender") {
          void loadArmyEntryIntoSimulation(entryId, "defender");
          return;
        }

        if (button.dataset.entryAction === "delete") {
          void deleteArmyEntry(entryId);
        }
      });
    });
  }

  function applyArmyListSelectionState() {
    const hasSelectedList = Boolean(state.selectedArmyListId);
    elements.armyListSelect.value = hasSelectedList ? String(state.selectedArmyListId) : "";
    elements.armyListCreate.disabled = hasSelectedList;
    elements.armyListSave.disabled = !hasSelectedList;
    elements.armyListDelete.disabled = !hasSelectedList;
    setArmyEntryEditorEnabled(hasSelectedList);

    if (!hasSelectedList) {
      setArmyEntryContext(
        "Create or select a list before adding units to the roster.",
        false,
      );
    }
  }

  function populateArmyListForm(detail = null) {
    elements.armyListName.value = detail ? detail.name : "";
    elements.armyListFaction.value = detail ? detail.faction_id : "";
    elements.armyListNotes.value = detail ? detail.notes || "" : "";
    elements.armyListSelect.value = detail ? String(detail.id) : "";
  }

  function clearArmyEntryEditor({ preserveDatasheet = false } = {}) {
    state.editingArmyEntryId = null;
    state.editingArmyEntrySnapshot = null;
    elements.armyEntrySubmit.textContent = "Add unit to list";
    elements.armyEntryQuantity.value = "1";
    elements.armyEntryUnitSize.value = "1";
    elements.armyEntryPoints.value = "";
    elements.armyEntrySortOrder.value = "";
    elements.armyEntryNickname.value = "";
    elements.armyEntryNotes.value = "";

    if (!preserveDatasheet) {
      clearArmyEntrySelection();
      elements.armyEntryDatasheet.value = "";
      resetArmyEntryModelSelect();
      resetArmyEntryCostSelect();
    }

    setArmyEntryContext("Pick a datasheet and a points profile to build a roster entry.");
  }

  function resetArmyListWorkspace() {
    state.selectedArmyListId = null;
    populateArmyListForm();
    clearArmyEntryEditor();
    applyArmyListSelectionState();
    elements.armyListSummary.innerHTML =
      "<p class='empty-state'>Select a saved list or create a new roster to see totals and warnings.</p>";
    elements.armyListEntries.innerHTML =
      "<p class='empty-state'>No units added yet. Create a list, then add units from the editor.</p>";
  }

  async function getSelectedArmyListDetail({ force = false } = {}) {
    if (!state.selectedArmyListId) {
      throw createUiError({
        title: "No roster selected",
        message: "Create or select an army list before editing roster entries.",
      });
    }

    return loadArmyListDetail(state.selectedArmyListId, { force });
  }

  async function selectArmyList(armyListId, { force = false, silent = false } = {}) {
    if (!armyListId) {
      resetArmyListWorkspace();
      if (!silent) {
        setArmyListStatus("Create a roster or load a saved list to start building.");
      }
      return null;
    }

    state.selectedArmyListId = Number(armyListId);
    applyArmyListSelectionState();
    setArmyListStatus("Loading selected roster...");

    const detail = await loadArmyListDetail(state.selectedArmyListId, { force });
    populateArmyListForm(detail);
    renderArmyListSummary(detail);
    renderArmyListEntries(detail);
    clearArmyEntryEditor();
    setArmyListStatus(`Loaded ${detail.name}.`);
    return detail;
  }

  function findMatchingArmyEntryCost(detail, options = {}) {
    if (!detail.costs.length) {
      return -1;
    }

    return detail.costs.findIndex((cost) => {
      if (options.costLabel && cost.description !== options.costLabel) {
        return false;
      }
      if (options.pointsEach !== undefined && options.pointsEach !== null) {
        return cost.cost === options.pointsEach;
      }
      return Boolean(options.costLabel);
    });
  }

  async function hydrateArmyEntryOptions(datasheetId, options = {}) {
    resetArmyEntryModelSelect("Loading model lines...");
    resetArmyEntryCostSelect("Loading points profiles...");

    const detail = await loadDetail(datasheetId);

    const modelOptions = [
      "<option value=''>Default unit profile</option>",
      ...detail.models.map((model) => {
        return `<option value="${model.line}">${escapeHtml(model.name)} (Line ${model.line})</option>`;
      }),
    ];
    elements.armyEntryModel.innerHTML = modelOptions.join("");
    elements.armyEntryModel.value = options.modelLine ? String(options.modelLine) : "";

    const placeholderText = detail.costs.length
      ? "Choose a published points profile"
      : "No published points profiles";
    resetArmyEntryCostSelect(placeholderText);

    if (detail.costs.length) {
      elements.armyEntryCost.innerHTML = "";
      const placeholderOption = document.createElement("option");
      placeholderOption.value = "";
      placeholderOption.textContent = placeholderText;
      elements.armyEntryCost.appendChild(placeholderOption);

      detail.costs.forEach((cost, index) => {
        const option = document.createElement("option");
        option.value = String(index);
        option.dataset.points = cost.cost === null ? "" : String(cost.cost);
        option.dataset.unitSize = String(parseUnitSizeFromCostLabel(cost.description) || "");
        option.dataset.costLabel = cost.description || "";
        option.textContent = `${cost.description || "Unit cost"}${
          cost.cost !== null ? ` :: ${cost.cost} pts` : " :: Variable"
        }`;
        elements.armyEntryCost.appendChild(option);
      });
    }

    const matchingCostIndex = findMatchingArmyEntryCost(detail, options);
    elements.armyEntryCost.value = matchingCostIndex >= 0 ? String(matchingCostIndex) : "";

    if (options.unitSize !== undefined) {
      elements.armyEntryUnitSize.value = String(options.unitSize);
    }
    if (options.quantity !== undefined) {
      elements.armyEntryQuantity.value = String(options.quantity);
    }
    if (options.pointsEach !== undefined && options.pointsEach !== null) {
      elements.armyEntryPoints.value = String(options.pointsEach);
    } else if (matchingCostIndex >= 0) {
      applyArmyEntryCostSelection({ onlyWhenEmpty: true });
    }

    setArmyEntryContext(
      detail.costs.length
        ? "Datasheet loaded. Choose a published points profile or override the points manually."
        : "Datasheet loaded. No published points profile is available, so add points manually if needed.",
    );

    return detail;
  }

  function applyArmyEntryCostSelection({ onlyWhenEmpty = false } = {}) {
    const selectedOption = elements.armyEntryCost.selectedOptions[0];
    if (!selectedOption || !selectedOption.value) {
      return;
    }

    const pointsValue = selectedOption.dataset.points || "";
    const unitSizeValue = selectedOption.dataset.unitSize || "";

    if (pointsValue && (!onlyWhenEmpty || !elements.armyEntryPoints.value.trim())) {
      elements.armyEntryPoints.value = pointsValue;
    }

    if (unitSizeValue && (!onlyWhenEmpty || !elements.armyEntryUnitSize.value.trim())) {
      elements.armyEntryUnitSize.value = unitSizeValue;
    }
  }

  async function handleArmyEntryDatasheetChange() {
    const datasheetId = state.displayToId.get(elements.armyEntryDatasheet.value);
    if (!datasheetId) {
      clearArmyEntrySelection();
      resetArmyEntryModelSelect("Select a valid datasheet");
      resetArmyEntryCostSelect("Select a valid datasheet");
      setArmyEntryContext(
        "Choose a valid datasheet from the imported catalogue before saving a unit.",
        true,
      );
      return;
    }

    setArmyEntrySelection(datasheetId, elements.armyEntryDatasheet.value);

    if (
      !state.editingArmyEntrySnapshot ||
      state.editingArmyEntrySnapshot.datasheet_id !== datasheetId
    ) {
      elements.armyEntryUnitSize.value = "1";
      elements.armyEntryPoints.value = "";
      elements.armyEntryCost.value = "";
      elements.armyEntryModel.value = "";
    }

    try {
      await hydrateArmyEntryOptions(datasheetId);
    } catch (error) {
      resetArmyEntryModelSelect("Unable to load model lines");
      resetArmyEntryCostSelect("Unable to load points profiles");
      setArmyEntryContext(
        "The selected datasheet could not be loaded into the unit editor.",
        true,
      );
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: handleArmyEntryDatasheetChange,
      });
    }
  }

  async function startEditingArmyEntry(entryId) {
    const detail = await getSelectedArmyListDetail();
    const entry = detail.entries.find((item) => item.id === entryId);

    if (!entry) {
      throw createUiError({
        title: "Saved unit not found",
        message: "The requested roster entry could not be found in this list.",
      });
    }

    state.editingArmyEntryId = entry.id;
    state.editingArmyEntrySnapshot = entry;
    setArmyEntrySelection(entry.datasheet_id, entry.datasheet_name);
    elements.armyEntrySubmit.textContent = "Save unit changes";
    elements.armyEntryUnitSize.value = String(entry.unit_size);
    elements.armyEntryQuantity.value = String(entry.quantity);
    elements.armyEntryPoints.value =
      entry.points_each !== null && entry.points_each !== undefined ? String(entry.points_each) : "";
    elements.armyEntrySortOrder.value = String(entry.sort_order);
    elements.armyEntryNickname.value = entry.nickname || "";
    elements.armyEntryNotes.value = entry.notes || "";

    try {
      await hydrateArmyEntryOptions(entry.datasheet_id, {
        modelLine: entry.model_line,
        unitSize: entry.unit_size,
        quantity: entry.quantity,
        pointsEach: entry.points_each,
        costLabel: entry.cost_label,
      });
      setArmyEntryContext(`Editing ${entry.display_name}. Update the fields, then save your changes.`);
    } catch (error) {
      resetArmyEntryModelSelect("Unavailable in current data");
      resetArmyEntryCostSelect("Unavailable in current data");
      setArmyEntryContext(
        "This unit points to data that is no longer in the current import. Pick a new datasheet before changing the unit reference.",
        true,
      );
      if (error && typeof error === "object" && error.status !== 404) {
        showErrorPopup(error, {
          actionLabel: "Try again",
          action: () => startEditingArmyEntry(entryId),
        });
      }
    }
  }

  function buildArmyListCreatePayload() {
    const payload = {
      name: elements.armyListName.value.trim(),
      faction_id: elements.armyListFaction.value,
      notes: normalizeOptionalText(elements.armyListNotes.value),
    };

    const issues = [];
    if (!payload.name) {
      issues.push("Enter a roster name before creating the list.");
    }
    if (!payload.faction_id) {
      issues.push("Choose a faction before creating the list.");
    }

    return { payload, issues };
  }

  function buildArmyListUpdatePayload(detail) {
    const nextName = elements.armyListName.value.trim();
    const nextFactionId = elements.armyListFaction.value;
    const nextNotes = normalizeOptionalText(elements.armyListNotes.value);
    const issues = [];
    const payload = {};

    if (!nextName) {
      issues.push("Roster name cannot be empty.");
    }
    if (!nextFactionId) {
      issues.push("Roster faction cannot be empty.");
    }

    if (issues.length) {
      return { payload: null, issues };
    }

    if (nextName !== detail.name) {
      payload.name = nextName;
    }
    if (nextFactionId !== detail.faction_id) {
      payload.faction_id = nextFactionId;
    }
    if (nextNotes !== (detail.notes ?? null)) {
      payload.notes = nextNotes;
    }

    return { payload, issues };
  }

  function buildArmyEntryCreatePayload() {
    const datasheetId = resolveArmyEntryDatasheetId();
    const modelLine = elements.armyEntryModel.value ? Number(elements.armyEntryModel.value) : null;
    const pointsEach = readOptionalIntegerFromElement(elements.armyEntryPoints);
    const sortOrder = readOptionalIntegerFromElement(elements.armyEntrySortOrder);
    const selectedCostOption = elements.armyEntryCost.selectedOptions[0];
    const payload = {
      datasheet_id: datasheetId,
      model_line: modelLine,
      unit_size: readIntegerFromElement(elements.armyEntryUnitSize),
      quantity: readIntegerFromElement(elements.armyEntryQuantity),
      points_each: pointsEach,
      cost_label:
        selectedCostOption && selectedCostOption.value
          ? normalizeOptionalText(selectedCostOption.dataset.costLabel || selectedCostOption.textContent)
          : null,
      nickname: normalizeOptionalText(elements.armyEntryNickname.value),
      notes: normalizeOptionalText(elements.armyEntryNotes.value),
      sort_order: sortOrder,
    };

    const issues = [];
    if (!datasheetId) {
      issues.push("Choose a valid datasheet before adding a unit.");
    }
    if (payload.unit_size < 1) {
      issues.push("Unit size must be at least 1.");
    }
    if (payload.quantity < 1) {
      issues.push("Quantity must be at least 1.");
    }

    return { payload, issues };
  }

  function buildArmyEntryUpdatePayload(originalEntry) {
    const datasheetId = resolveArmyEntryDatasheetId();
    const modelLine = elements.armyEntryModel.value ? Number(elements.armyEntryModel.value) : null;
    const pointsEach = readOptionalIntegerFromElement(elements.armyEntryPoints);
    const sortOrder = readOptionalIntegerFromElement(elements.armyEntrySortOrder);
    const selectedCostOption = elements.armyEntryCost.selectedOptions[0];
    const currentCostLabel =
      selectedCostOption && selectedCostOption.value
        ? normalizeOptionalText(selectedCostOption.dataset.costLabel || selectedCostOption.textContent)
        : null;
    const payload = {};
    const issues = [];

    if (datasheetId !== originalEntry.datasheet_id) {
      if (!datasheetId) {
        issues.push("Choose a valid datasheet before changing the saved unit.");
      } else {
        payload.datasheet_id = datasheetId;
      }
    }

    if (modelLine !== (originalEntry.model_line ?? null)) {
      payload.model_line = modelLine;
    }

    const unitSize = readIntegerFromElement(elements.armyEntryUnitSize);
    if (unitSize < 1) {
      issues.push("Unit size must be at least 1.");
    } else if (unitSize !== originalEntry.unit_size) {
      payload.unit_size = unitSize;
    }

    const quantity = readIntegerFromElement(elements.armyEntryQuantity);
    if (quantity < 1) {
      issues.push("Quantity must be at least 1.");
    } else if (quantity !== originalEntry.quantity) {
      payload.quantity = quantity;
    }

    if (pointsEach !== (originalEntry.points_each ?? null)) {
      payload.points_each = pointsEach;
    }
    if (currentCostLabel !== (originalEntry.cost_label ?? null)) {
      payload.cost_label = currentCostLabel;
    }

    const nickname = normalizeOptionalText(elements.armyEntryNickname.value);
    if (nickname !== (originalEntry.nickname ?? null)) {
      payload.nickname = nickname;
    }

    const notes = normalizeOptionalText(elements.armyEntryNotes.value);
    if (notes !== (originalEntry.notes ?? null)) {
      payload.notes = notes;
    }

    if (sortOrder !== null && sortOrder !== (originalEntry.sort_order ?? null)) {
      payload.sort_order = sortOrder;
    }

    return { payload, issues };
  }

  async function refreshRosterState(selectedListId = state.selectedArmyListId, statusMessage = "") {
    await loadArmyLists();

    if (selectedListId && state.armyListMap.has(Number(selectedListId))) {
      await selectArmyList(Number(selectedListId), { force: true, silent: true });
    } else {
      resetArmyListWorkspace();
    }

    await syncSimulationEntrySelectors();

    if (statusMessage) {
      setArmyListStatus(statusMessage);
    }
  }

  function showValidationPopup(title, issues, emptyMessage) {
    const error = createUiError({
      title,
      message: issues[0] || emptyMessage,
      detail: issues.map((issue, index) => `${index + 1}. ${issue}`).join("\n"),
    });
    showErrorPopup(error);
  }

  function handleNewArmyList() {
    resetArmyListWorkspace();
    setArmyListStatus("New roster draft ready. Add a name and faction, then create the list.");
    elements.armyListName.focus();
  }

  async function createArmyList() {
    const { payload, issues } = buildArmyListCreatePayload();
    if (issues.length) {
      setArmyListStatus("The roster could not be created with the current inputs.", true);
      showValidationPopup(
        "Roster details missing",
        issues,
        "Update the roster details and try again.",
      );
      return;
    }

    try {
      const detail = await fetchJson(
        "/api/army-lists",
        {
          method: "POST",
          body: JSON.stringify(payload),
        },
        {
          title: "Roster creation failed",
          message: "The army list could not be created.",
        },
      );
      state.armyListDetailCache.set(detail.id, detail);
      await refreshRosterState(detail.id, `Created ${detail.name}.`);
    } catch (error) {
      setArmyListStatus("The roster could not be created. Open the error for details.", true);
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: createArmyList,
      });
    }
  }

  async function saveArmyList() {
    let detail;
    try {
      detail = await getSelectedArmyListDetail();
    } catch (error) {
      showErrorPopup(error);
      return;
    }

    const { payload, issues } = buildArmyListUpdatePayload(detail);
    if (issues.length) {
      setArmyListStatus("The roster changes could not be saved.", true);
      showValidationPopup(
        "Roster details missing",
        issues,
        "Update the roster details and try again.",
      );
      return;
    }

    if (!Object.keys(payload).length) {
      setArmyListStatus("No roster changes to save.");
      return;
    }

    try {
      const updated = await fetchJson(
        `/api/army-lists/${detail.id}`,
        {
          method: "PATCH",
          body: JSON.stringify(payload),
        },
        {
          title: "Roster save failed",
          message: "The army list changes could not be saved.",
        },
      );
      state.armyListDetailCache.set(updated.id, updated);
      await refreshRosterState(updated.id, `Saved ${updated.name}.`);
    } catch (error) {
      setArmyListStatus("The roster changes could not be saved. Open the error for details.", true);
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: saveArmyList,
      });
    }
  }

  async function deleteArmyList() {
    if (!state.selectedArmyListId) {
      showErrorPopup(
        createUiError({
          title: "No roster selected",
          message: "Choose a saved list before trying to delete it.",
        }),
      );
      return;
    }

    const detail = await getSelectedArmyListDetail();
    if (!window.confirm(`Delete the roster "${detail.name}" and all of its saved units?`)) {
      return;
    }

    try {
      await fetchJson(
        `/api/army-lists/${detail.id}`,
        {
          method: "DELETE",
        },
        {
          title: "Roster delete failed",
          message: "The army list could not be deleted.",
        },
      );
      state.armyListDetailCache.delete(detail.id);
      await refreshRosterState(null, `Deleted ${detail.name}.`);
    } catch (error) {
      setArmyListStatus("The roster could not be deleted. Open the error for details.", true);
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: deleteArmyList,
      });
    }
  }

  async function saveArmyEntry() {
    if (!state.selectedArmyListId) {
      showErrorPopup(
        createUiError({
          title: "No roster selected",
          message: "Create or select a list before saving a unit.",
        }),
      );
      return;
    }

    const isEditing = Boolean(state.editingArmyEntrySnapshot);
    const { payload, issues } = isEditing
      ? buildArmyEntryUpdatePayload(state.editingArmyEntrySnapshot)
      : buildArmyEntryCreatePayload();

    if (issues.length) {
      setArmyListStatus("The unit could not be saved with the current setup.", true);
      showValidationPopup(
        isEditing ? "Unit changes incomplete" : "Unit setup incomplete",
        issues,
        "Update the saved unit details and try again.",
      );
      return;
    }

    if (isEditing && !Object.keys(payload).length) {
      setArmyListStatus("No unit changes to save.");
      return;
    }

    const path = isEditing
      ? `/api/army-lists/${state.selectedArmyListId}/entries/${state.editingArmyEntryId}`
      : `/api/army-lists/${state.selectedArmyListId}/entries`;
    const method = isEditing ? "PATCH" : "POST";

    try {
      const detail = await fetchJson(
        path,
        {
          method,
          body: JSON.stringify(payload),
        },
        {
          title: isEditing ? "Unit save failed" : "Unit add failed",
          message: isEditing
            ? "The roster unit changes could not be saved."
            : "The unit could not be added to the roster.",
        },
      );
      state.armyListDetailCache.set(detail.id, detail);
      clearArmyEntryEditor();
      await refreshRosterState(
        detail.id,
        isEditing ? "Saved the roster unit changes." : "Added the unit to the roster.",
      );
    } catch (error) {
      setArmyListStatus("The roster unit could not be saved. Open the error for details.", true);
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: saveArmyEntry,
      });
    }
  }

  async function deleteArmyEntry(entryId) {
    const detail = await getSelectedArmyListDetail();
    const entry = detail.entries.find((item) => item.id === entryId);
    if (!entry) {
      showErrorPopup(
        createUiError({
          title: "Saved unit not found",
          message: "The selected roster entry could not be found.",
        }),
      );
      return;
    }

    if (!window.confirm(`Remove "${entry.display_name}" from ${detail.name}?`)) {
      return;
    }

    try {
      const updated = await fetchJson(
        `/api/army-lists/${detail.id}/entries/${entry.id}`,
        {
          method: "DELETE",
        },
        {
          title: "Unit removal failed",
          message: "The saved unit could not be removed from the roster.",
        },
      );
      state.armyListDetailCache.set(updated.id, updated);
      if (state.editingArmyEntryId === entry.id) {
        clearArmyEntryEditor();
      }
      await refreshRosterState(updated.id, `Removed ${entry.display_name} from the roster.`);
    } catch (error) {
      setArmyListStatus("The roster unit could not be removed. Open the error for details.", true);
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: () => deleteArmyEntry(entryId),
      });
    }
  }

  async function getArmyListEntryById(armyListId, entryId) {
    const detail = await loadArmyListDetail(Number(armyListId));
    const entry = detail.entries.find((item) => item.id === Number(entryId));

    if (!entry) {
      throw createUiError({
        title: "Saved unit not found",
        message: "The selected roster entry could not be found.",
      });
    }

    return { detail, entry };
  }

  async function loadArmyEntryIntoSimulation(entryId, role, armyListId = state.selectedArmyListId) {
    const { entry } = await getArmyListEntryById(armyListId, entryId);

    if (!entry.datasheet_available) {
      throw createUiError({
        title: "Saved unit needs attention",
        message: `${entry.display_name} can no longer be loaded into the simulator because its datasheet is missing from the current import.`,
      });
    }

    const datasheetSummary = state.datasheetMap.get(entry.datasheet_id);
    if (!datasheetSummary) {
      throw createUiError({
        title: "Datasheet not cached",
        message: `${entry.datasheet_name} is not available in the current catalogue cache.`,
      });
    }

    const datasheetLabel = buildDisplayLabel(datasheetSummary);

    if (role === "attacker") {
      elements.attackerInput.value = datasheetLabel;
      await handleAttackerChange();
      elements.attackerModelsInput.value = String(entry.unit_size);
      setArmyListStatus(
        `Loaded ${entry.display_name} into the attacker slot. Switch to the Workbench tab when you are ready to simulate.`,
      );
      setResultsPlaceholder(
        "Saved attacker loaded. Switch to Workbench, choose a weapon profile, and run the simulation when ready.",
      );
      return;
    }

    setDefenderMode("datasheet");
    elements.defenderInput.value = datasheetLabel;
    await handleDefenderChange();
    elements.targetModelCountInput.value = String(entry.unit_size);

    if (entry.model_profile_id) {
      elements.defenderModelSelect.value = String(entry.model_profile_id);
    } else if (entry.model_line) {
      throw createUiError({
        title: "Saved model line missing",
        message: `${entry.display_name} no longer maps to the saved defender model line in the current import.`,
      });
    }

    setArmyListStatus(
      `Loaded ${entry.display_name} into the defender slot. Switch to the Workbench tab when you are ready to simulate.`,
    );
  }

  async function loadSelectedSimulationEntry(role) {
    const listId = role === "attacker" ? elements.simAttackerList.value : elements.simDefenderList.value;
    const entryId =
      role === "attacker" ? elements.simAttackerEntry.value : elements.simDefenderEntry.value;

    if (!listId) {
      showErrorPopup(
        createUiError({
          title: "No roster selected",
          message: `Choose a saved ${role} list before loading a unit into the simulator.`,
        }),
      );
      return;
    }

    if (!entryId) {
      showErrorPopup(
        createUiError({
          title: "No unit selected",
          message: `Choose a saved ${role} unit before loading it into the simulator.`,
        }),
      );
      return;
    }

    try {
      await loadArmyEntryIntoSimulation(Number(entryId), role, Number(listId));
    } catch (error) {
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: () => loadSelectedSimulationEntry(role),
      });
    }
  }

  async function syncSimulationEntrySelectors() {
    const tasks = [];

    if (elements.simAttackerList.value) {
      tasks.push(loadSimulationEntryOptions("attacker", elements.simAttackerList.value));
    } else {
      elements.simAttackerEntry.innerHTML = "<option value=''>Choose a list first</option>";
    }

    if (elements.simDefenderList.value) {
      tasks.push(loadSimulationEntryOptions("defender", elements.simDefenderList.value));
    } else {
      elements.simDefenderEntry.innerHTML = "<option value=''>Choose a list first</option>";
    }

    if (!tasks.length) {
      return;
    }

    const results = await Promise.allSettled(tasks);
    const failed = results.find((result) => result.status === "rejected");
    if (failed) {
      throw failed.reason;
    }
  }

  async function refreshDashboardAndCatalog() {
    const results = await Promise.allSettled([
      loadDashboard(),
      loadCatalog(),
      loadArmyLists(),
    ]);
    const failures = results.filter((result) => result.status === "rejected");
    if (!failures.length && state.selectedArmyListId) {
      try {
        await selectArmyList(state.selectedArmyListId, { force: true, silent: true });
      } catch (error) {
        failures.push({ status: "rejected", reason: error });
      }
    }

    if (!failures.length) {
      try {
        await syncSimulationEntrySelectors();
      } catch (error) {
        failures.push({ status: "rejected", reason: error });
      }
    }

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
      resetAttackerBuildPreview("Choose a valid attacker datasheet to build a unit.");
      return;
    }

    state.attackerBuildPreview = null;
    state.attackerEffectSelections.clear();
    resetWeaponSelect("Loading weapons...");
    setAttackerBuildStatus("Loading attacker data...");

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
      populateAttackerLeaderOptions(detail);
      await loadAttackerBuildPreview();
    } catch (error) {
      state.attackerId = null;
      state.attackerBuildPreview = null;
      state.attackerEffectSelections.clear();
      resetWeaponSelect("Unable to load weapons right now");
      resetAttackerBuildPreview("Unable to load attacker build details right now.");
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

  function describeEffectScope(scope) {
    if (scope === "ranged") {
      return "Ranged only";
    }
    if (scope === "melee") {
      return "Melee only";
    }
    return "Any attack";
  }

  function setAttackerBuildStatus(message, isError = false) {
    elements.attackerBuildStatus.textContent = message;
    elements.attackerBuildStatus.style.color = isError ? "var(--danger)" : "";
  }

  function resetAttackerBuildPreview(
    message = "Choose an attacker datasheet to inspect valid leaders and imported unit effects.",
  ) {
    state.attackerBuildPreview = null;
    state.attackerEffectSelections.clear();
    elements.attackerLeaderSelect.innerHTML = "<option value=''>No leader attached</option>";
    elements.attackerLeaderSelect.value = "";
    elements.attackerLeaderSelect.disabled = true;
    setAttackerBuildStatus(message);
    elements.attackerBuildEffects.innerHTML = `<p class="empty-state">${escapeHtml(message)}</p>`;
  }

  function populateAttackerLeaderOptions(detail) {
    const attachableLeaders = detail.attachable_leaders || [];
    const previousValue = elements.attackerLeaderSelect.value;

    elements.attackerLeaderSelect.innerHTML = "";

    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = attachableLeaders.length
      ? "No leader attached"
      : "No attachable leaders found";
    elements.attackerLeaderSelect.appendChild(placeholderOption);

    attachableLeaders.forEach((leader) => {
      const option = document.createElement("option");
      option.value = leader.id;
      option.textContent = `${leader.name} :: ${leader.faction_name}${
        leader.role ? ` :: ${leader.role}` : ""
      }`;
      elements.attackerLeaderSelect.appendChild(option);
    });

    elements.attackerLeaderSelect.disabled = !attachableLeaders.length;
    elements.attackerLeaderSelect.value = attachableLeaders.some(
      (leader) => leader.id === previousValue,
    )
      ? previousValue
      : "";
  }

  function renderAttackerBuildPreview(preview) {
    const leaderNames = preview.selected_leaders.map((leader) => leader.name);
    const selectedCount = preview.effects.filter((effect) =>
      state.attackerEffectSelections.has(effect.id),
    ).length;

    if (leaderNames.length && preview.effects.length) {
      setAttackerBuildStatus(
        `${preview.attacker_name} with ${leaderNames.join(", ")} attached. ${selectedCount} of ${preview.effects.length} structured effects selected for this attack.`,
      );
    } else if (leaderNames.length) {
      setAttackerBuildStatus(
        `${preview.attacker_name} with ${leaderNames.join(", ")} attached. No structured attack effects are available yet.`,
      );
    } else if (preview.effects.length) {
      setAttackerBuildStatus(
        `${preview.attacker_name} has ${selectedCount} of ${preview.effects.length} structured effects selected for this attack.`,
      );
    } else {
      setAttackerBuildStatus(
        `${preview.attacker_name} does not expose any structured attack effects yet.`,
      );
    }

    if (!preview.effects.length && !preview.unmodeled_abilities.length) {
      elements.attackerBuildEffects.innerHTML =
        "<p class='empty-state'>No structured unit effects are available for this attacker yet.</p>";
      return;
    }

    const effectToggleHtml = preview.effects.length
      ? `
        <section class="builder-effect-group">
          <p class="section-label">Structured effects</p>
          <div class="builder-option-list">
            ${preview.effects
              .map((effect) => {
                const isChecked = state.attackerEffectSelections.has(effect.id);
                const defaultLabel = effect.enabled_by_default ? "Starts on" : "Starts off";
                return `
                  <label class="builder-option">
                    <input type="checkbox" data-attacker-effect-id="${escapeHtml(effect.id)}" ${
                      isChecked ? "checked" : ""
                    } />
                    <span>
                      <strong>${escapeHtml(effect.ability_name)}</strong>
                      <small>${escapeHtml(effect.summary)}</small>
                      <em>${escapeHtml(effect.source_name)} - ${escapeHtml(
                        describeEffectScope(effect.scope),
                      )} - ${escapeHtml(defaultLabel)}</em>
                    </span>
                  </label>
                `;
              })
              .join("")}
          </div>
        </section>
      `
      : "";

    const unmodeledHtml = preview.unmodeled_abilities.length
      ? `
        <section class="builder-effect-group">
          <p class="section-label">Not yet interpreted</p>
          <ul class="builder-note-list">
            ${preview.unmodeled_abilities
              .map((ability) => `<li>${escapeHtml(ability)}</li>`)
              .join("")}
          </ul>
        </section>
      `
      : "";

    elements.attackerBuildEffects.innerHTML =
      effectToggleHtml + unmodeledHtml;

    Array.from(elements.attackerBuildEffects.querySelectorAll("[data-attacker-effect-id]")).forEach(
      (input) => {
        input.addEventListener("change", () => {
          const effectId = input.dataset.attackerEffectId;
          if (!effectId) {
            return;
          }

          if (input.checked) {
            state.attackerEffectSelections.add(effectId);
            return;
          }

          state.attackerEffectSelections.delete(effectId);
        });
      },
    );
  }

  function getSelectedAttackerLeaderIds() {
    return elements.attackerLeaderSelect.value ? [elements.attackerLeaderSelect.value] : [];
  }

  async function loadAttackerBuildPreview() {
    if (!state.attackerId) {
      resetAttackerBuildPreview();
      return;
    }

    setAttackerBuildStatus("Loading imported unit effects...");

    try {
      const previousPreview = state.attackerBuildPreview;
      const preview = await fetchJson(
        "/api/simulation-build-preview",
        {
          method: "POST",
          body: JSON.stringify({
            attacker_datasheet_id: state.attackerId,
            attacker_leader_ids: getSelectedAttackerLeaderIds(),
          }),
        },
        {
          title: "Attacker build preview failed",
          message: "The attacker unit effects could not be loaded.",
        },
      );
      const validEffectIds = new Set(preview.effects.map((effect) => effect.id));
      const previousEffectIds = new Set(
        (previousPreview?.effects || []).map((effect) => effect.id),
      );
      const nextSelections = new Set(
        Array.from(state.attackerEffectSelections).filter((effectId) =>
          validEffectIds.has(effectId),
        ),
      );
      preview.effects.forEach((effect) => {
        if (effect.enabled_by_default && !previousEffectIds.has(effect.id)) {
          nextSelections.add(effect.id);
        }
      });
      state.attackerBuildPreview = preview;
      state.attackerEffectSelections = nextSelections;

      renderAttackerBuildPreview(preview);
    } catch (error) {
      state.attackerBuildPreview = null;
      setAttackerBuildStatus(
        "Attacker effects could not be loaded right now.",
        true,
      );
      elements.attackerBuildEffects.innerHTML =
        "<p class='empty-state'>The unit build preview is unavailable right now.</p>";
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: loadAttackerBuildPreview,
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
    const leaderSummary = result.attacker_leaders.length
      ? `<p class="result-build-meta">Attached leaders: ${escapeHtml(
          result.attacker_leaders.join(", "),
        )}</p>`
      : "";
    const appliedEffectSummary = result.applied_effects.length
      ? `
        <ul class="builder-note-list result-note-list">
          ${result.applied_effects
            .map((effect) => `<li>${escapeHtml(effect)}</li>`)
            .join("")}
        </ul>
      `
      : "";
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
          ${leaderSummary}
          ${appliedEffectSummary}
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
    setActiveWorkspaceTab("workbench");
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
      attacker_leader_ids: getSelectedAttackerLeaderIds(),
      attacker_enabled_effect_ids: Array.from(state.attackerEffectSelections),
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
    await Promise.all([loadCatalog(), loadArmyLists()]);
    applyArmyListSelectionState();
    resetArmyEntryModelSelect();
    resetArmyEntryCostSelect();
    await syncSimulationEntrySelectors();
    setSyncStatus("Catalogue ready.");
    setArmyListStatus(
      state.armyLists.length
        ? "Saved rosters ready. Select one or create a new list."
        : "Create a roster or load a saved list to start building.",
    );
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
      state.armyListDetailCache.clear();
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
    elements.workspaceTabs.forEach((tab) => {
      tab.addEventListener("click", () => {
        setActiveWorkspaceTab(tab.dataset.workspaceTab);
      });
      tab.addEventListener("keydown", handleWorkspaceTabKeydown);
    });
    window.addEventListener("hashchange", () => {
      setActiveWorkspaceTab(readWorkspaceTabFromHash(), { updateHash: false });
    });

    elements.syncButton.addEventListener("click", () => {
      void runSync();
    });
    elements.attackerInput.addEventListener("change", () => {
      void handleAttackerChange();
    });
    elements.attackerLeaderSelect.addEventListener("change", () => {
      void loadAttackerBuildPreview();
    });
    elements.defenderInput.addEventListener("change", () => {
      void handleDefenderChange();
    });
    elements.armyListNew.addEventListener("click", handleNewArmyList);
    elements.armyListCreate.addEventListener("click", () => {
      void createArmyList();
    });
    elements.armyListSave.addEventListener("click", () => {
      void saveArmyList();
    });
    elements.armyListDelete.addEventListener("click", () => {
      void deleteArmyList();
    });
    elements.armyListSelect.addEventListener("change", () => {
      if (!elements.armyListSelect.value) {
        handleNewArmyList();
        return;
      }

      void selectArmyList(Number(elements.armyListSelect.value)).catch((error) => {
        setArmyListStatus("The selected roster could not be loaded.", true);
        showErrorPopup(error, {
          actionLabel: "Try again",
          action: () => selectArmyList(Number(elements.armyListSelect.value)),
        });
      });
    });
    elements.armyEntryDatasheet.addEventListener("input", () => {
      const matchedId = state.displayToId.get(elements.armyEntryDatasheet.value);
      if (matchedId) {
        elements.armyEntryDatasheet.dataset.selectedId = matchedId;
        state.armyEntryDatasheetId = matchedId;
        return;
      }

      clearArmyEntrySelection();
    });
    elements.armyEntryDatasheet.addEventListener("change", () => {
      void handleArmyEntryDatasheetChange();
    });
    elements.armyEntryCost.addEventListener("change", () => {
      applyArmyEntryCostSelection();
    });
    elements.armyEntryClear.addEventListener("click", () => {
      clearArmyEntryEditor();
    });
    elements.armyEntryForm.addEventListener("submit", (event) => {
      event.preventDefault();
      void saveArmyEntry();
    });
    elements.simAttackerList.addEventListener("change", () => {
      void loadSimulationEntryOptions("attacker", elements.simAttackerList.value).catch((error) => {
        showErrorPopup(error, {
          actionLabel: "Try again",
          action: () => loadSimulationEntryOptions("attacker", elements.simAttackerList.value),
        });
      });
    });
    elements.simDefenderList.addEventListener("change", () => {
      void loadSimulationEntryOptions("defender", elements.simDefenderList.value).catch((error) => {
        showErrorPopup(error, {
          actionLabel: "Try again",
          action: () => loadSimulationEntryOptions("defender", elements.simDefenderList.value),
        });
      });
    });
    elements.simLoadAttacker.addEventListener("click", () => {
      void loadSelectedSimulationEntry("attacker");
    });
    elements.simLoadDefender.addEventListener("click", () => {
      void loadSelectedSimulationEntry("defender");
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
    setActiveWorkspaceTab(readWorkspaceTabFromHash(), { updateHash: false });
    setDefenderMode("datasheet");
    resetWeaponSelect();
    resetDefenderSelect();
    resetAttackerBuildPreview();
    resetArmyListWorkspace();

    try {
      await loadInitialData();
    } catch (error) {
      setSyncStatus("Catalogue load failed. Open the error message for details.", true);
      elements.browserList.innerHTML =
        "<p class='empty-state'>No datasheets loaded yet. Try refreshing data.</p>";
      setArmyListStatus("Saved rosters could not be loaded. Open the error message for details.", true);
      showErrorPopup(error, {
        actionLabel: "Try again",
        action: loadInitialData,
      });
    }
  }

  void init();
})();
