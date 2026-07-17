"""
Scraper for DNB sine "Faste rabatter" (https://www.dnb.no/kundeprogram/fordeler/faste-rabatter)

Henter listen over faste nettbutikk-rabatter DNB kundeprogram-kunder har,
og normaliserer dem til et felles skjema som kan lagres i databasen sammen
med data fra OBOS og USBL.

Kjør: python3 dnb_faste_rabatter.py
Krever: pip install requests beautifulsoup4
"""

import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

URL = "https://www.dnb.no/kundeprogram/fordeler/faste-rabatter"

HEADERS = {
    # Bruk en vanlig nettleser-UA - noen sider blokkerer default python-requests UA
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    # DNB sender ikke charset i Content-Type-headeren, så requests faller
    # tilbake til ISO-8859-1 (HTTP-standardens default for text/*) selv om
    # innholdet faktisk er UTF-8. Det gir mojibake ("Ã¥" i stedet for "å").
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def is_external_retailer_link(href: str) -> bool:
    """Rabattkortene lenker til den eksterne nettbutikken (f.eks. odlo.no),
    mens navigasjon/interne lenker peker til dnb.no. Vi bruker det til å
    skille rabattkort fra resten av siden."""
    if not href or not href.startswith("http"):
        return False
    netloc = urlparse(href).netloc.lower()
    return "dnb.no" not in netloc


def extract_shared_discount_code(soup: BeautifulSoup) -> str | None:
    """DNB bruker én delt rabattkode (f.eks. 'DNB8547') som tastes inn i
    handlekurven i nettbutikkene. Prøver å finne den i sideteksten."""
    text = soup.get_text(" ")
    match = re.search(r"\b([A-Z]{2,6}\d{3,8})\b", text)
    return match.group(1) if match else None


def parse_discount_card(a_tag) -> dict | None:
    full_text = clean_text(a_tag.get_text(" "))
    if not full_text:
        return None

    pct_match = re.search(r"(\d{1,3})\s?%", full_text)
    if not pct_match:
        # Ikke et rabattkort (f.eks. en vanlig tekstlenke uten prosentbadge)
        return None

    percentage = int(pct_match.group(1))
    href = a_tag["href"]

    # 1. Prøv bildets alt-tekst som kilde til butikknavn (renskes for
    #    boilerplate som "Faste Rabatter 560x120 Odlo" -> "Odlo")
    store_name = None
    img = a_tag.find("img")
    if img and img.get("alt"):
        alt = clean_text(img["alt"])
        alt = re.sub(r"(?i)faste rabatter\s*\d*x?\d*\s*", "", alt).strip()
        if alt:
            store_name = alt

    # 2. Fallback: overskrift-tag inni kortet
    if not store_name:
        heading = a_tag.find(["h1", "h2", "h3", "h4", "strong", "b"])
        if heading:
            store_name = clean_text(heading.get_text())

    # 3. Siste utvei: domenenavn
    if not store_name:
        store_name = urlparse(href).netloc.replace("www.", "").split(".")[0].capitalize()

    # Bygg beskrivelse: fjern prosent og duplikate forekomster av butikknavnet
    description = full_text
    description = re.sub(r"\d{1,3}\s?%", "", description, count=1).strip()
    description = re.sub(r"(?i)faste rabatter\s*\d*x?\d*", "", description).strip()
    if store_name:
        description = re.sub(re.escape(store_name), "", description, count=2).strip()
    description = clean_text(description)

    online_only = bool(re.search(r"(?i)(kun\s+)?i?\s*nettbutikk", full_text)) and bool(
        re.search(r"(?i)ikke i fysisk|gjelder i nettbutikk|kun i nettbutikk|gjelder kun i nettbutikk", full_text)
    )

    return {
        "provider": "DNB",
        "retailer": store_name,
        "discount_percentage": percentage,
        "description": description,
        "online_only": online_only,
        "requires_code": True,
        "source_url": href,
    }


def parse_discounts(html: str) -> tuple[list[dict], str | None]:
    soup = BeautifulSoup(html, "html.parser")

    seen_hrefs = set()
    discounts = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not is_external_retailer_link(href) or href in seen_hrefs:
            continue

        card = parse_discount_card(a)
        if card:
            seen_hrefs.add(href)
            discounts.append(card)

    shared_code = extract_shared_discount_code(soup)
    return discounts, shared_code


def main():
    html = fetch_html(URL)
    discounts, shared_code = parse_discounts(html)

    print(f"Fant {len(discounts)} faste rabatter hos DNB")
    if shared_code:
        print(f"Delt rabattkode funnet: {shared_code}")

    output = {
        "provider": "DNB",
        "source_page": URL,
        "shared_discount_code": shared_code,
        "discounts": discounts,
    }

    with open("dnb_faste_rabatter.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til dnb_faste_rabatter.json")


if __name__ == "__main__":
    main()
