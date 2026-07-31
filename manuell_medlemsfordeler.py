"""
Scraper for Norsk Manuellterapeutforening (NMF) sine rabattavtaler
(https://manuell.no/rabattavtaler)

Siden er en WIPS CMS-side der artikkellisten ikke rendres i den statiske
HTML-en, men hentes klientside fra sidens eget artikkel-API:

    GET https://manuell.no/Api/v2/template/rendered-articles?pageId=827723440

Vi gjør nøyaktig samme kall som siden selv gjør i nettleseren. Hver artikkel
har et "isExternalUrl.articleLink"-flagg som forteller om "Les mer"-lenken
peker ut av manuell.no eller til en intern artikkelside (som da prefikses
med domenet).

Ett par avtaler har en generisk tittel ("Ny rabattavtale") satt av NMF selv
i stedet for partnerens navn - disse er overstyrt manuelt ut fra teaser-/
intro-teksten.

Kjør: python3 manuell_medlemsfordeler.py
Krever: pip install requests
"""

import json
import re

import requests

PAGE_URL = "https://manuell.no/rabattavtaler"
API_URL = "https://manuell.no/Api/v2/template/rendered-articles?pageId=827723440"
SITE_ROOT = "https://manuell.no"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Noen artikler har en generisk NMF-satt tittel i stedet for partnerens navn.
RETAILER_OVERRIDES = {
    14241: "Bertel O. Steen",
}


def fetch_articles() -> list[dict]:
    resp = requests.get(API_URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json().get("articles", [])


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def make_card(article: dict) -> dict:
    doc_id = article.get("docId")
    title = clean_text(article["titles"]["main"])
    retailer = RETAILER_OVERRIDES.get(doc_id, title)
    description = clean_text(article["content"].get("intro"))

    read_more = article["urls"]["readMore"]
    is_external = article.get("isExternalUrl", {}).get("articleLink", False)
    source_url = read_more if is_external else f"{SITE_ROOT}{read_more}"

    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)

    return {
        "provider": "Norsk Manuellterapeutforening",
        "retailer": retailer,
        "discount_percentage": int(pct_match.group(1)) if pct_match else None,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": source_url,
    }


def main():
    articles = fetch_articles()
    discounts = [make_card(a) for a in articles]

    print(f"Fant {len(discounts)} rabattavtaler hos Norsk Manuellterapeutforening")

    output = {
        "provider": "Norsk Manuellterapeutforening",
        "source_page": PAGE_URL,
        "discounts": discounts,
    }

    with open("manuell_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til manuell_medlemsfordeler.json")


if __name__ == "__main__":
    main()
