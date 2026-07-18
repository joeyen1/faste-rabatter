"""
Scraper for Norsk Fysioterapeutforbund (NFF) sine medlemsfordeler
(https://fysio.no/medlemsfordeler)

Siden er en HubSpot-side med en accordion (<a class="accordion__open"> +
<div class="accordion__content">) der hvert element er én "fane". De
fleste fanene er generiske forbundstjenester (Forsikring, Kurstilbud,
Juridisk bistand, Faggrupper, ...) eller sentrale Unio-avtaler som allerede
skrapes separat via unio_medlemsprodukter.py (Billån/Nordea, AVIS, BMW,
Extra Optical, Esso, Bertel O. Steen/elbil, De Historiske, Norgesbooking,
Nordea Liv/pensjon, Cutters - alle listet på nytt i "Andre økonomiske
fordeler"-fanen). Vi plukker derfor bare ut butikkrabattene som er unike
for NFF-medlemmer og ikke allerede dekket av Unio-skraperen.

Kjør: python3 fysio_medlemsfordeler.py
Krever: pip install requests beautifulsoup4
"""

import json
import re

import requests
from bs4 import BeautifulSoup

URL = "https://fysio.no/medlemsfordeler"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Enkeltstående accordion-faner som er reelle butikkrabatter (ikke generiske
# forbundstjenester som Forsikring/Kurstilbud/Juridisk bistand/osv).
STANDALONE_RETAILER_TITLES = {"Garmin", "Stormberg", "Torshov Sport"}

# Innenfor "Andre økonomiske fordeler" er de fleste <li>-punktene bare en
# gjenfortelling av Unios sentrale avtaler (dekket av unio_medlemsprodukter.py).
# Disse to er NFF-spesifikke og finnes ikke der.
LIST_ITEM_RETAILER_OVERRIDES = {
    "Strømavtale og mobilabonnement": "Fjordkraft",
    "Kunstverket Galleri AS": "Kunstverket Galleri",
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def make_card(retailer: str, description: str, source_url: str) -> dict:
    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
    return {
        "provider": "Norsk Fysioterapeutforbund",
        "retailer": retailer,
        "discount_percentage": int(pct_match.group(1)) if pct_match else None,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": source_url,
    }


def first_external_link(el, exclude_domain="fysio.no") -> str | None:
    for a in el.select("a[href]"):
        href = a["href"]
        if href.startswith("http") and exclude_domain not in href:
            return href
    return None


def parse_discounts(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    discounts = []

    for open_link in soup.select("a.accordion__open"):
        title = clean_text(open_link.get_text())
        content = open_link.find_next_sibling("div", class_="accordion__content")
        if not content:
            continue

        if title in STANDALONE_RETAILER_TITLES:
            description = clean_text(content.get_text(" "))
            source_url = first_external_link(content) or URL
            discounts.append(make_card(title, description, source_url))

        elif title == "Andre økonomiske fordeler":
            for li in content.select("li"):
                strong = li.find("strong")
                item_title = clean_text(strong.get_text()) if strong else ""
                if item_title not in LIST_ITEM_RETAILER_OVERRIDES:
                    continue
                retailer = LIST_ITEM_RETAILER_OVERRIDES[item_title]
                description = clean_text(li.get_text(" "))
                source_url = first_external_link(li, exclude_domain="unio.no") or URL
                discounts.append(make_card(retailer, description, source_url))

    return discounts


def main():
    html = fetch_html(URL)
    discounts = parse_discounts(html)

    print(f"Fant {len(discounts)} unike medlemsrabatter hos Norsk Fysioterapeutforbund")

    output = {
        "provider": "Norsk Fysioterapeutforbund",
        "source_page": URL,
        "discounts": discounts,
    }

    with open("fysio_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til fysio_medlemsfordeler.json")


if __name__ == "__main__":
    main()
