"""
Scraper for LOfavør sine medlemsfordeler (https://www.lofavor.no/<kategori>)

Kategorisidene (f.eks. "ferie-og-opplevelser") lister opp produkter i en
<ul class="product-list-minors"> med tittel + lenke til hver produktside.
Selve rabattbeskrivelsen finnes bare på produktsiden, i
<section class="page-intro"> ... <h1> + <div class="large">. Vi henter
derfor kategorisiden først for å finne alle produkt-URLer, og besøker så
hver produktside for beskrivelse, rabattprosent og ekstern partnerlenke.

Kjør: python3 lofavor_medlemsfordeler.py [kategori-slug ...]
Uten argumenter hentes "ferie-og-opplevelser".
Krever: pip install requests beautifulsoup4
"""

import json
import re
import sys
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.lofavor.no"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

DEFAULT_CATEGORIES = ["ferie-og-opplevelser"]



def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def list_product_urls(category_slug: str) -> list[tuple[str, str]]:
    """Returnerer [(tittel, produkt-url), ...] for en kategoriside."""
    html = fetch_html(f"{BASE_URL}/{category_slug}")
    soup = BeautifulSoup(html, "html.parser")

    seen = set()
    products = []
    for ul in soup.select("ul.product-list-minors"):
        for a in ul.select("li a[href]"):
            href = urljoin(BASE_URL, a["href"])
            title = clean_text(a.get_text())
            if href in seen or not title:
                continue
            seen.add(href)
            products.append((title, href))
    return products


def find_partner_link(soup: BeautifulSoup) -> str | None:
    """Finn CTA-knappen som lenker til partnerens egen nettside.

    Siden bruker handlePartnerClick() både på selve CTA-knappen og på en
    rekke interne footer-/meny-lenker (personvern, vilkår, nyhetsbrev osv),
    så vi kan ikke bare ta den første treffen. CTA-knappen kjennetegnes ved
    class="btn btn-primary" og target="_blank"; fall tilbake til en hvilken
    som helst ekstern (ikke-lofavor.no) target="_blank"-lenke om den mangler.
    """
    candidates = soup.select('a[onclick^="handlePartnerClick"][target="_blank"][href]')

    def is_external(href: str) -> bool:
        return bool(href) and "lofavor.no" not in href

    for a in candidates:
        classes = a.get("class") or []
        if "btn-primary" in classes and is_external(a["href"]):
            return a["href"]

    for a in candidates:
        if is_external(a["href"]):
            return a["href"]

    return None


def parse_product_page(url: str, fallback_title: str) -> dict | None:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    intro = soup.select_one("section.page-intro")
    if not intro:
        return None

    h1 = intro.select_one("h1")
    retailer = clean_text(h1.get_text()) if h1 else fallback_title

    desc_container = intro.select_one("div.large")
    description = clean_text(desc_container.get_text(" ")) if desc_container else ""

    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
    percentage = int(pct_match.group(1)) if pct_match else None

    source_url = find_partner_link(soup) or url

    return {
        "provider": "LOfavør",
        "retailer": retailer,
        "discount_percentage": percentage,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": source_url,
        "lofavor_page": url,
    }


def parse_category(category_slug: str) -> list[dict]:
    discounts = []
    for title, url in list_product_urls(category_slug):
        try:
            card = parse_product_page(url, title)
        except requests.RequestException as e:
            print(f"  Hopper over {title} ({url}): {e}")
            continue
        if card:
            discounts.append(card)
        time.sleep(0.3)  # vær grei mot serveren
    return discounts


def main():
    categories = sys.argv[1:] or DEFAULT_CATEGORIES

    all_discounts = []
    for slug in categories:
        print(f"Henter kategori '{slug}' ...")
        discounts = parse_category(slug)
        print(f"  Fant {len(discounts)} produkter")
        all_discounts.extend(discounts)

    print(f"\nFant totalt {len(all_discounts)} medlemsfordeler hos LOfavør")

    output = {
        "provider": "LOfavør",
        "source_page": f"{BASE_URL}/{categories[0]}",
        "categories": categories,
        "discounts": all_discounts,
    }

    with open("lofavor_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til lofavor_medlemsfordeler.json")


if __name__ == "__main__":
    main()
