"""
Scraper for Unio sine medlemsprodukter (https://www.unio.no/medlemsprodukter/)

Unio er hovedorganisasjonen flere fagforbund er tilsluttet (bl.a.
Akademikerforbundet, Norsk Fysioterapeutforbund). Disse sentralt
fremforhandlede avtalene dukker derfor ofte opp igjen i de enkelte
forbundenes egne medlemsfordel-sider.

Indekssiden lister bare produktnavn + lenke til hver egen produktside
(WPBakery "banner"-widget uten synlig <a href> i grep-bar form for de
fleste - vi henter derfor lenkene fra de tilfellene som faktisk har
href="/medlemsprodukter/<slug>/" i markup). Hver produktside har ett
<h2> med tittel, etterfulgt av avsnitt med beskrivelse, helt frem til en
gjentakende "Unios medlemsprodukter:"-liste nederst (samme liste på alle
sidene - vi bruker teksten som stoppmarkør for å ikke dra med den).

Kjør: python3 unio_medlemsprodukter.py
Krever: pip install requests beautifulsoup4
"""

import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.unio.no"
INDEX_URL = f"{BASE_URL}/medlemsprodukter/"
STOP_MARKER = "Unios medlemsprodukter"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Sidetitlene er ofte markedsføringstekst ("Opplev kjøreglede med modeller
# fra BMW Norge AS") snarere enn rene butikknavn - overstyr til kortnavn
# der vi kjenner slugen, så søk på butikknavn fungerer bedre.
RETAILER_NAME_OVERRIDES = {
    "bertel-o-steen": "Bertel O. Steen",
    "bmw": "BMW",
    "de-historiske": "De Historiske",
    "nordea": "Nordea",
    "nordea-liv": "Nordea Liv",
}

# Reserveliste i tilfelle indekssiden ikke gir alle lenkene i statisk HTML
# (WPBakery-bannerne er ofte JS-drevne uten synlig href for de fleste kortene).
FALLBACK_SLUGS = [
    "avis",
    "bertel-o-steen",
    "bmw",
    "cutters",
    "de-historiske",
    "esso-mastercard",
    "extra-optical",
    "nordea",
    "nordea-liv",
    "norgesbooking",
    "stormberg",
]


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def list_product_slugs() -> list[str]:
    html = fetch_html(INDEX_URL)
    slugs = sorted(set(re.findall(r'medlemsprodukter/([a-z0-9-]+)/?"', html)))
    return slugs or FALLBACK_SLUGS


def parse_product_page(slug: str) -> dict | None:
    url = urljoin(INDEX_URL, f"{slug}/")
    html = fetch_html(url)

    h2_match = re.search(r"<h2[^>]*>([^<]+)</h2>", html)
    if not h2_match:
        return None
    retailer = RETAILER_NAME_OVERRIDES.get(slug, clean_text(h2_match.group(1)))

    stop_idx = html.find(STOP_MARKER)
    segment = html[h2_match.end() : stop_idx if stop_idx != -1 else None]

    soup_segment = BeautifulSoup(segment, "html.parser")
    description = clean_text(soup_segment.get_text(" "))

    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
    percentage = int(pct_match.group(1)) if pct_match else None

    source_url = url
    for a in soup_segment.select("a[href]"):
        href = a["href"]
        if href.startswith("http") and "unio.no" not in href:
            source_url = href
            break

    return {
        "provider": "Unio",
        "retailer": retailer,
        "discount_percentage": percentage,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": source_url,
    }


def main():
    slugs = list_product_slugs()

    discounts = []
    for slug in slugs:
        card = parse_product_page(slug)
        if card:
            discounts.append(card)

    print(f"Fant {len(discounts)} medlemsprodukter hos Unio")

    output = {
        "provider": "Unio",
        "source_page": INDEX_URL,
        "discounts": discounts,
    }

    with open("unio_medlemsprodukter.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til unio_medlemsprodukter.json")


if __name__ == "__main__":
    main()
