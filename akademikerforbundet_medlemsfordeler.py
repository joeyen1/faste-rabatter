"""
Scraper for Akademikerforbundet sine medlemsfordeler
(https://www.akademikerforbundet.no/medlemskap/medlemsfordeler/)

Nettstedet er bygget i Sitevision. Hovedsiden er bare en kategorioversikt
(Rådgivning, Kurs, Forsikring, Bank, Bil, Ferie, Trening og sport, Bøker og
tidsskrifter, Diverse medlemsfordeler) - selve rabattene ligger på hver
underkategoriside, som lister opp tilbud i blokker:

    <div class="paragraph clearfix" id="par-...">
      <h2>Tittel</h2>
      [ev. <figure>...</figure>]
      <div class="content"><p>beskrivelse, ev. rabattkode og ekstern lenke</p></div>
    </div>

Vi skraper bare kategoriene med faktiske butikk-/leverandørrabatter (Bil,
Ferie, Trening og sport, Bøker og tidsskrifter, Diverse medlemsfordeler).
Forsikring/Bank/Kurs/Rådgivning er droppet - de er generiske medlemstjenester
fra én leverandør (Akaforsikring/Nordea), ikke butikkrabatter, og bruker
uansett en helt annen HTML-mal (produktbokser uten rabattekst).

Kjør: python3 akademikerforbundet_medlemsfordeler.py [kategori-slug ...]
Krever: pip install requests beautifulsoup4
"""

import json
import re
import sys
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.akademikerforbundet.no"
CATEGORY_PATH = "/medlemskap/medlemsfordeler"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

DEFAULT_CATEGORIES = [
    "bil",
    "ferie",
    "trening-og-sport",
    "boker-og-tidsskrifter",
    "diverse-medlemsfordeler",
]


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def clean_retailer_name(title: str) -> str:
    """Titlene inneholder ofte prosentsatsen ("20 % hos Cutters",
    "Extra Opticals 20 % rabatt på briller") - trekk ut bare butikknavnet
    så søk på butikknavn fungerer bedre."""
    m = re.match(r"^\d{1,3}\s?%\s*hos\s+(.+)$", title, re.I)
    if m:
        return m.group(1).strip()
    m = re.match(r"^(.+?)\s+\d{1,3}\s?%", title)
    if m and m.group(1).strip():
        return m.group(1).strip()
    return title


def find_source_link(content_div, category_url: str) -> str:
    """Første eksterne lenke i beskrivelsen (til partnerens/Unios side om
    tilbudet), ellers kategorisiden selv."""
    for a in content_div.select("a[href]"):
        href = a["href"]
        if href.startswith("http") and "akademikerforbundet.no" not in href:
            return href
    return category_url


def parse_category(category_slug: str) -> list[dict]:
    category_url = f"{BASE_URL}{CATEGORY_PATH}/{category_slug}/"
    html = fetch_html(category_url)
    soup = BeautifulSoup(html, "html.parser")

    discounts = []
    for block in soup.select('div.paragraph.clearfix[id^="par-"]'):
        h2 = block.find("h2")
        content = block.select_one("div.content")
        if not h2 or not content:
            continue

        title = clean_text(h2.get_text())
        description = clean_text(content.get_text(" "))
        if not title or not description:
            continue

        pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
        percentage = int(pct_match.group(1)) if pct_match else None

        discounts.append(
            {
                "provider": "Akademikerforbundet",
                "retailer": clean_retailer_name(title),
                "discount_percentage": percentage,
                "description": description,
                "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
                "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
                "source_url": find_source_link(content, category_url),
            }
        )
    return discounts


def main():
    categories = sys.argv[1:] or DEFAULT_CATEGORIES

    all_discounts = []
    for slug in categories:
        print(f"Henter kategori '{slug}' ...")
        discounts = parse_category(slug)
        print(f"  Fant {len(discounts)} tilbud")
        all_discounts.extend(discounts)

    print(f"\nFant totalt {len(all_discounts)} medlemsfordeler hos Akademikerforbundet")

    output = {
        "provider": "Akademikerforbundet",
        "source_page": f"{BASE_URL}{CATEGORY_PATH}/",
        "categories": categories,
        "discounts": all_discounts,
    }

    with open("akademikerforbundet_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til akademikerforbundet_medlemsfordeler.json")


if __name__ == "__main__":
    main()
