"""
Scraper for NITO sine medlemsfordeler
(https://www.nito.no/medlemskap-og-fordeler/medlemsfordeler/)

Oversiktssiden grupperer fordeler i seksjoner (Forsikringer, Banktjenester,
Rabatter, Verktøy og ressurser, ...). Vi henter kun "Rabatter"-gruppen -
det er den eneste med faktiske butikk-/leverandørrabatter; de andre er
generiske forbundstjenester (forsikring via Tryg, banktjenester via
Nordea, juridisk bistand, lønnsstatistikk osv).

Hvert kort i "Rabatter" viser bare partnernavn (som bilde-alt-tekst) og en
tittel, uten beskrivelse - selve rabatteksten/prosenten finnes bare på
hver enkelt underside, så vi besøker dem (samme mønster som LOfavør).

Kjør: python3 nito_medlemsfordeler.py
Krever: pip install requests beautifulsoup4
"""

import json
import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.nito.no"
INDEX_URL = f"{BASE_URL}/medlemskap-og-fordeler/medlemsfordeler/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Rabattgruppen inneholder også "Verv en kollega" (medlemsverving, ikke en
# butikkrabatt) - den ekskluderes eksplisitt.
EXCLUDED_TITLES = {"Verv en kollega – det lønner seg!"}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    # Fjern myke bindestreker (\xad) og null-tegn som av og til sniker seg
    # inn i Sitecore sin alt-tekst/rich text.
    s = re.sub(r"[\xad\x00]", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def find_rabatter_group(soup: BeautifulSoup):
    for group in soup.select(".member-benefit-list__group"):
        heading = group.find(["h1", "h2", "h3"])
        if heading and clean_text(heading.get_text()) == "Rabatter":
            return group
    return None


def list_discount_teasers() -> list[dict]:
    html = fetch_html(INDEX_URL)
    soup = BeautifulSoup(html, "html.parser")

    group = find_rabatter_group(soup)
    if not group:
        return []

    teasers = []
    seen = set()
    for art in group.select("article.article-teaser"):
        partner_img = art.select_one(".article-teaser__partner img")
        heading = art.select_one(".article-teaser__heading")
        link = heading.find("a") if heading else None
        if not link or not link.get("href"):
            continue

        title = clean_text(heading.get_text())
        if title in EXCLUDED_TITLES:
            continue

        url = urljoin(BASE_URL, link["href"])
        if url in seen:
            continue
        seen.add(url)

        teasers.append(
            {
                "partner": clean_text(partner_img["alt"]) if partner_img and partner_img.get("alt") else "",
                "title": title,
                "url": url,
            }
        )
    return teasers


def parse_detail_page(teaser: dict) -> dict | None:
    html = fetch_html(teaser["url"])
    soup = BeautifulSoup(html, "html.parser")

    text_blocks = soup.select(".text-block__text.editorial")
    description = clean_text(" ".join(b.get_text(" ") for b in text_blocks))
    if not description:
        description = teaser["title"]

    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
    percentage = int(pct_match.group(1)) if pct_match else None

    source_url = teaser["url"]
    for block in text_blocks:
        for a in block.select("a[href]"):
            href = a["href"]
            if href.startswith("http") and "nito.no" not in href:
                source_url = href
                break
        else:
            continue
        break

    # Partnernavnet fra bilde-alt-teksten er som regel penere enn tittelen
    # ("Bertel O. Steen" fremfor "Bilrabatt Mercedes-Benz"), men noen
    # partner-bilder har generiske "NITO"-alt-tekster - da bruker vi tittelen.
    retailer = teaser["partner"] if teaser["partner"] and teaser["partner"] != "NITO" else teaser["title"]

    return {
        "provider": "NITO",
        "retailer": retailer,
        "discount_percentage": percentage,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": source_url,
    }


def main():
    teasers = list_discount_teasers()
    print(f"Fant {len(teasers)} rabatter i oversikten, henter detaljer ...")

    discounts = []
    for teaser in teasers:
        try:
            card = parse_detail_page(teaser)
        except requests.RequestException as e:
            print(f"  Hopper over {teaser['title']}: {e}")
            continue
        if card:
            discounts.append(card)
        time.sleep(0.2)

    print(f"Fant {len(discounts)} medlemsrabatter hos NITO")

    output = {
        "provider": "NITO",
        "source_page": INDEX_URL,
        "discounts": discounts,
    }

    with open("nito_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til nito_medlemsfordeler.json")


if __name__ == "__main__":
    main()
