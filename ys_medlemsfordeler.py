"""
Scraper for YS (Yrkesorganisasjonenes Sentralforbund) sine medlemsfordeler
(https://ys.no/medlemsfordeler/)

Siden lister rabattene som <article class="post-article"> med en tittel
(<h2>, av og til tom - da ligger butikknavnet i en ".boldtext"-span i
stedet), en kort beskrivelse (".post-shorttext") og en lenke til
partnerens nettside. Noen kort er generiske YS-tjenester uten ekstern
butikk (f.eks. "YS Selvstendig", karriereveiviser) - disse hoppes over.

Kjør: python3 ys_medlemsfordeler.py
Krever: pip install requests beautifulsoup4
"""

import json
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

URL = "https://ys.no/medlemsfordeler/"

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


def domain_name(href: str) -> str:
    netloc = urlparse(href).netloc.lower().replace("www.", "")
    return netloc.split(".")[0].capitalize()


def first_link(article) -> str | None:
    for a in article.select("a[href]"):
        href = a["href"].strip()
        if href.startswith("http"):
            return href
    return None


def parse_discounts(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    discounts = []

    for article in soup.select("article.post-article"):
        h2 = article.select_one("h2, H2")
        cat = article.select_one(".boldtext")
        short = article.select_one(".post-shorttext")

        h2_text = clean_text(h2.get_text()) if h2 else ""
        cat_text = clean_text(cat.get_text()) if cat else ""
        description = clean_text(short.get_text(" ")) if short else ""

        href = first_link(article)

        # Hopp over interne ys.no-tjenester uten ekstern butikk/partner
        # (f.eks. generiske forbundssider, karriereveiviser, "YS Selvstendig").
        if not href or "ys.no" in urlparse(href).netloc:
            continue

        # Kategori-labelen er som regel selve butikknavnet når den er satt
        # (unntatt den generiske "YS Fordel"-labelen) - mer pålitelig enn
        # H2, som ofte er en markedsføringsoverskrift i stedet for et navn.
        retailer = (cat_text if cat_text and cat_text != "YS Fordel" else "") or h2_text or domain_name(href)
        if not retailer or not description:
            continue

        pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)

        discounts.append(
            {
                "provider": "YS",
                "retailer": retailer,
                "discount_percentage": int(pct_match.group(1)) if pct_match else None,
                "description": description,
                "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
                "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode|kode ", description)),
                "source_url": href,
            }
        )

    return discounts


def main():
    html = fetch_html(URL)
    discounts = parse_discounts(html)

    print(f"Fant {len(discounts)} medlemsfordeler hos YS")

    output = {
        "provider": "YS",
        "source_page": URL,
        "discounts": discounts,
    }

    with open("ys_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til ys_medlemsfordeler.json")


if __name__ == "__main__":
    main()
