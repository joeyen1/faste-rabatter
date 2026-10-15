"""
Scraper for Norsk Fysioterapeutforbund (Fysioterapeutene) sine medlemsfordeler
(https://fysio.no/medlemskap/medlemsfordeler-og-rabatter)

Siden ble bygget om høsten 2026: gamle /medlemsfordeler redirecter hit, og
accordion-en heter nå fy-accordion (en flat liste med ~21 enkeltavtaler, hver
med <.fy-accordion__label> og <.fy-accordion__panel>). Vi hopper over
generiske finans-/bankavtaler (Nordea, pensjon, billån, inkasso) som ikke er
butikkrabatter. Avtaler som også finnes hos Unio beholdes bevisst - samme
rabatt gjelder for flere forbund, og det er nettopp det appen skal vise.

Kjør: python3 fysio_medlemsfordeler.py
Krever: pip install requests beautifulsoup4
"""

import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

URL = "https://fysio.no/medlemskap/medlemsfordeler-og-rabatter"
PROVIDER = "Norsk Fysioterapeutforbund"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Finans-/forbundstjenester som ikke er butikkrabatter.
SKIP_LABEL_KEYWORDS = ("nordea", "pensjon", "billån", "inkasso")

# Nøkkelord i overskriften -> rent butikknavn (ellers brukes overskriften).
RETAILER_NAMES = [
    ("trinnvis", "Trinnvis"),
    ("noteless", "Noteless"),
    ("crowe", "Crowe"),
    ("thon", "Thon Hotels"),
    ("norgesbooking", "Norgesbooking"),
    ("historiske", "De Historiske"),
    ("avis", "Avis"),
    ("garmin", "Garmin"),
    ("torshov", "Torshov Sport"),
    ("stormberg", "Stormberg"),
    ("bertel", "Bertel O. Steen"),
    ("bmw", "BMW"),
    ("esso", "Esso"),
    ("fjordkraft", "Fjordkraft"),
    ("extra optical", "Extra Optical"),
    ("cutters", "Cutters"),
    ("kunstverket", "Kunstverket Galleri"),
]


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def clean_text(s: str) -> str:
    s = re.sub(r"\[email.{0,3}protected\]", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def retailer_name(label: str) -> str:
    low = label.lower()
    for keyword, name in RETAILER_NAMES:
        if keyword in low:
            return name
    return label


def source_link(panel) -> str | None:
    external = [
        a["href"]
        for a in panel.select("a[href]")
        if a["href"].startswith("http") and "fysio.no" not in a["href"]
    ]
    non_unio = [h for h in external if "unio.no" not in h]
    return (non_unio or external or [None])[0]


def parse_discounts(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    discounts = []

    for item in soup.select(".fy-accordion__item"):
        label_el = item.select_one(".fy-accordion__label")
        panel = item.select_one(".fy-accordion__panel")
        if not label_el or not panel:
            continue

        label = clean_text(label_el.get_text())
        if any(k in label.lower() for k in SKIP_LABEL_KEYWORDS):
            continue

        description = clean_text(panel.get_text(" "))
        if not description:
            continue

        pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
        discounts.append(
            {
                "provider": PROVIDER,
                "retailer": retailer_name(label),
                "discount_percentage": int(pct_match.group(1)) if pct_match else None,
                "description": description,
                "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
                "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
                "source_url": source_link(panel) or URL,
            }
        )
    return discounts


def main():
    discounts = parse_discounts(fetch_html(URL))
    print(f"Fant {len(discounts)} medlemsrabatter hos {PROVIDER}")

    with open("fysio_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(
            {"provider": PROVIDER, "source_page": URL, "discounts": discounts},
            f,
            ensure_ascii=False,
            indent=2,
        )
    print("Lagret til fysio_medlemsfordeler.json")


if __name__ == "__main__":
    main()
