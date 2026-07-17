(function () {
  "use strict";

  const searchInput = document.getElementById("search");
  const resultsEl = document.getElementById("results");
  const emptyStateEl = document.getElementById("empty-state");
  const filtersEl = document.getElementById("filters");
  const subtitleEl = document.getElementById("subtitle");
  const updatedAtEl = document.getElementById("updated-at");

  /** @type {Array<any>} */
  let discounts = [];
  let providers = [];
  let sharedCodeByProvider = {};
  let activeProvider = null; // null = alle

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

    subtitleEl.textContent = `${discounts.length} rabatter fra ${providers.length} leverandører`;
    updatedAtEl.textContent = data.generated_at
      ? `Oppdatert ${formatDate(data.generated_at)}`
      : "";

    renderFilters();
    render();
  }

  function renderFilters() {
    filtersEl.innerHTML = "";

    const allChip = makeChip("Alle", null);
    filtersEl.appendChild(allChip);

    providers.forEach((p) => {
      filtersEl.appendChild(makeChip(p, p));
    });
  }

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
    if (activeProvider && item.provider !== activeProvider) return false;
    if (!query) return true;
    const haystack = normalize(item.retailer + " " + (item.description || ""));
    return haystack.includes(query);
  }

  function render() {
    const query = normalize(searchInput.value.trim());
    const filtered = discounts.filter((d) => matches(d, query));

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
