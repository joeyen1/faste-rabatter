(function () {
  "use strict";

  const searchInput = document.getElementById("search");
  const resultsEl = document.getElementById("results");
  const emptyStateEl = document.getElementById("empty-state");
  const filtersEl = document.getElementById("filters");
  const subtitleEl = document.getElementById("subtitle");
  const updatedAtEl = document.getElementById("updated-at");
  const settingsBtn = document.getElementById("settings-btn");
  const settingsOverlay = document.getElementById("settings-overlay");
  const settingsList = document.getElementById("settings-list");
  const settingsClose = document.getElementById("settings-close");

  const EXCLUDED_KEY = "fasteRabatter:excludedProviders";

  /** @type {Array<any>} */
  let discounts = [];
  let providers = [];
  let sharedCodeByProvider = {};
  let activeProvider = null; // null = alle

  // Leverandører brukeren har valgt bort ("ikke medlem av") - lagres lokalt
  // på telefonen/nettleseren, ikke på tvers av enheter.
  let excludedProviders = loadExcludedProviders();

  function loadExcludedProviders() {
    try {
      const raw = localStorage.getItem(EXCLUDED_KEY);
      return new Set(raw ? JSON.parse(raw) : []);
    } catch {
      return new Set();
    }
  }

  function saveExcludedProviders() {
    try {
      localStorage.setItem(EXCLUDED_KEY, JSON.stringify([...excludedProviders]));
    } catch {
      // localStorage utilgjengelig (privat nettlesing e.l.) - bare fortsett uten lagring
    }
  }

  function normalize(str) {
    return (str || "")
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, ""); // fjern aksenter for søk
  }

  function formatDate(iso) {
    if (!iso) return "";
    try {
      const d = new Date(iso);
      return d.toLocaleDateString("nb-NO", { day: "numeric", month: "short", year: "numeric" });
    } catch {
      return iso;
    }
  }

  async function loadData() {
    const res = await fetch("data/discounts.json", { cache: "no-store" });
    const data = await res.json();

    discounts = data.discounts || [];
    (data.sources || []).forEach((s) => {
      if (s.shared_discount_code) sharedCodeByProvider[s.provider] = s.shared_discount_code;
    });
    providers = [...new Set(discounts.map((d) => d.provider))].sort();

    // Fjern eventuelle lagrede valg som ikke lenger finnes i dataene
    excludedProviders.forEach((p) => {
      if (!providers.includes(p)) excludedProviders.delete(p);
    });

    updatedAtEl.textContent = data.generated_at
      ? `Oppdatert ${formatDate(data.generated_at)}`
      : "";

    renderFilters();
    renderSettingsList();
    render();
  }

  function visibleProviders() {
    return providers.filter((p) => !excludedProviders.has(p));
  }

  function renderFilters() {
    filtersEl.innerHTML = "";

    if (activeProvider && excludedProviders.has(activeProvider)) {
      activeProvider = null;
    }

    const allChip = makeChip("Alle", null);
    filtersEl.appendChild(allChip);

    visibleProviders().forEach((p) => {
      filtersEl.appendChild(makeChip(p, p));
    });
  }

  function renderSettingsList() {
    settingsList.innerHTML = "";

    providers.forEach((p) => {
      const label = document.createElement("label");
      label.className = "settings-row";

      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = !excludedProviders.has(p);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          excludedProviders.delete(p);
        } else {
          excludedProviders.add(p);
        }
        saveExcludedProviders();
        renderFilters();
        render();
      });

      const span = document.createElement("span");
      span.textContent = p;

      label.appendChild(checkbox);
      label.appendChild(span);
      settingsList.appendChild(label);
    });
  }

  function openSettings() {
    settingsOverlay.hidden = false;
  }

  function closeSettings() {
    settingsOverlay.hidden = true;
  }

  settingsBtn.addEventListener("click", openSettings);
  settingsClose.addEventListener("click", closeSettings);
  settingsOverlay.addEventListener("click", (e) => {
    if (e.target === settingsOverlay) closeSettings();
  });

  function makeChip(label, providerValue) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip";
    btn.textContent = label;
    btn.setAttribute("aria-pressed", String(activeProvider === providerValue));
    btn.addEventListener("click", () => {
      activeProvider = providerValue;
      renderFilters();
      render();
    });
    return btn;
  }

  function matches(item, query) {
    if (excludedProviders.has(item.provider)) return false;
    if (activeProvider && item.provider !== activeProvider) return false;
    if (!query) return true;
    const haystack = normalize(item.retailer + " " + (item.description || ""));
    return haystack.includes(query);
  }

  function render() {
    const query = normalize(searchInput.value.trim());
    const filtered = discounts.filter((d) => matches(d, query));

    const visibleCount = discounts.length - discounts.filter((d) => excludedProviders.has(d.provider)).length;
    subtitleEl.textContent =
      excludedProviders.size > 0
        ? `${visibleCount} av ${discounts.length} rabatter fra ${visibleProviders().length} av ${providers.length} leverandører`
        : `${discounts.length} rabatter fra ${providers.length} leverandører`;

    resultsEl.innerHTML = "";

    if (filtered.length === 0) {
      emptyStateEl.hidden = false;
      return;
    }
    emptyStateEl.hidden = true;

    // Vis kun et rimelig antall når det ikke er søkt på noe spesifikt,
    // for å unngå å rendre 250+ kort med en gang.
    const limit = query || activeProvider ? filtered.length : 40;

    const frag = document.createDocumentFragment();
    filtered.slice(0, limit).forEach((item) => {
      frag.appendChild(renderCard(item));
    });
    resultsEl.appendChild(frag);
  }

  function renderCard(item) {
    const li = document.createElement("li");

    const a = document.createElement("a");
    a.className = "card";
    a.href = item.source_url || "#";
    a.target = "_blank";
    a.rel = "noopener noreferrer";

    const top = document.createElement("div");
    top.className = "card-top";

    const title = document.createElement("h2");
    title.className = "card-title";
    title.textContent = item.retailer;
    top.appendChild(title);

    if (item.discount_percentage) {
      const pct = document.createElement("span");
      pct.className = "pct";
      pct.textContent = `${item.discount_percentage}%`;
      top.appendChild(pct);
    }

    a.appendChild(top);

    if (item.description) {
      const desc = document.createElement("p");
      desc.className = "card-desc";
      desc.textContent = item.description;
      a.appendChild(desc);
    }

    const badges = document.createElement("div");
    badges.className = "badges";

    const providerBadge = document.createElement("span");
    providerBadge.className = `badge provider-${item.provider}`;
    providerBadge.textContent = item.provider;
    badges.appendChild(providerBadge);

    if (item.online_only) {
      badges.appendChild(makeBadge("Kun nett"));
    }

    if (item.requires_code) {
      const code = sharedCodeByProvider[item.provider];
      badges.appendChild(makeBadge(code ? `Kode: ${code}` : "Krever kode"));
    }

    a.appendChild(badges);
    li.appendChild(a);
    return li;
  }

  function makeBadge(text) {
    const span = document.createElement("span");
    span.className = "badge";
    span.textContent = text;
    return span;
  }

  let debounceTimer;
  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(render, 80);
  });

  loadData().catch((err) => {
    subtitleEl.textContent = "Kunne ikke laste rabatter.";
    console.error(err);
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("service-worker.js").catch(() => {});
    });
  }
})();
