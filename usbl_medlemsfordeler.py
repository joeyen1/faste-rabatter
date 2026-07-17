"""
Scraper for USBL sine medlemsfordeler (https://www.usbl.no/medlemskap/medlemsfordeler)

Siden er vanlig server-rendret HTML. Hvert tilbud er en <a class="page-list__item-container">
med butikknavn i en <h2>/<span> og beskrivelse i en <p class="page-list__item-text">.

Kjør: python3 usbl_medlemsfordeler.py
Krever: pip install requests beautifulsoup4
"""

import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.usbl.no"
URL = f"{BASE_URL}/medlemskap/medlemsfordeler"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def parse_card(a_tag) -> dict | None:
    heading = a_tag.select_one("h2 .page-list__item-heading-span, h2")
    if not heading:
        return None
    retailer = clean_text(heading.get_text())
    if not retailer:
        return None

    desc_tag = a_tag.select_one("p.page-list__item-text")
    description = clean_text(desc_tag.get_text()) if desc_tag else ""

    href = a_tag.get("href", "")
    source_url = urljoin(BASE_URL, href)

    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
    percentage = int(pct_match.group(1)) if pct_match else None

    return {
        "provider": "USBL",
        "retailer": retailer,
        "discount_percentage": percentage,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": source_url,
    }


def parse_discounts(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    discounts = []
    seen = set()
    for a in soup.select("a.page-list__item-container"):
        card = parse_card(a)
        if not card:
            continue
        key = (card["retailer"], card["source_url"])
        if key in seen:
            continue
        seen.add(key)
        discounts.append(card)
    return discounts


def main():
    html = fetch_html(URL)
    discounts = parse_discounts(html)

    print(f"Fant {len(discounts)} medlemsfordeler hos USBL")

    output = {
        "provider": "USBL",
        "source_page": URL,
        "discounts": discounts,
    }

    with open("usbl_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til usbl_medlemsfordeler.json")


if __name__ == "__main__":
    main()
