"""
Scraper for Kobbl (boligbyggelag) sine medlemsrabatter
(https://www.kobbl.no/privat/medlemskap/rabatter-og-bonuser/)

Rabattene rendres ikke i den statiske HTML-en i det hele tatt - siden har
bare et tomt <div class="kobbl-medlemsfordeler" data-token="..."> som fylles
av kobbl-scripts.js via et fetch-kall til:

    GET https://api.bbld.io/memberbenefits/Contracts/current
    headers: x-api-version, Ocp-Apim-Subscription-Key, Authorization: Bearer <token>

Både subscription-key og bearer-token er hardkodet/injisert i det som
sendes til enhver besøkende i vanlig HTML/JS - vi gjør nøyaktig det samme
kallet som siden selv gjør i nettleseren, bare fra Python. Token'et hentes
ferskt fra siden hver gang scriptet kjører (det har typisk noen ukers
gyldighet), så det er ingen hardkodet hemmelighet å vedlikeholde her.

"bbld.io" ser ut til å være en delt medlemsfordel-plattform brukt av flere
boligbyggelag (samme mønster som OBOS/USBL sine egne, men med felles API).

Kjør: python3 kobbl_medlemsfordeler.py
Krever: pip install requests beautifulsoup4
"""

import json
import re
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

PAGE_URL = "https://www.kobbl.no/privat/medlemskap/rabatter-og-bonuser/"
API_URL = "https://api.bbld.io/memberbenefits/Contracts/current"
SUBSCRIPTION_KEY = "221aa763aa5f4d4db5bf4701e9b50f40"

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


def extract_token(html: str) -> str:
    m = re.search(r'class="kobbl-medlemsfordeler"[^>]*data-token="([^"]+)"', html)
    if not m:
        raise RuntimeError("Fant ikke data-token på Kobbl-siden - siden kan ha endret struktur")
    return m.group(1)


def fetch_contracts(token: str) -> list[dict]:
    resp = requests.get(
        API_URL,
        headers={
            "x-api-version": "2.0-system",
            "Cache-Control": "no-cache",
            "Ocp-Apim-Subscription-Key": SUBSCRIPTION_KEY,
            "Authorization": f"Bearer {token}",
        },
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json().get("contracts", [])


def clean_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def html_to_text(html: str) -> str:
    return clean_text(BeautifulSoup(html or "", "html.parser").get_text(" "))


def is_active(contract: dict) -> bool:
    now = datetime.now(timezone.utc)

    def parse(dt_str):
        if not dt_str:
            return None
        return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)

    valid_from = parse(contract.get("validFrom"))
    valid_to = parse(contract.get("validTo"))
    if valid_from and now < valid_from:
        return False
    if valid_to and now > valid_to:
        return False
    return True


def normalize(contract: dict) -> dict | None:
    retailer = clean_text(contract.get("name"))
    if not retailer:
        return None

    bonus_text = clean_text(contract.get("bonusText"))
    discount_text = clean_text(contract.get("discountText"))
    benefit_text = html_to_text(contract.get("benefit"))

    description_parts = [p for p in [discount_text, bonus_text, benefit_text] if p]
    description = clean_text(" – ".join(dict.fromkeys(description_parts)))

    # Prioriter selve rabatt-prosenten (discountText/benefit) fremfor
    # bonusRate, siden bonus er cashback og ikke en rabatt i kassen.
    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", discount_text + " " + benefit_text, re.I)
    percentage = int(pct_match.group(1)) if pct_match else None

    source_url = (contract.get("urlWebsite") or "").strip() or PAGE_URL

    return {
        "provider": "Kobbl",
        "retailer": retailer,
        "discount_percentage": percentage,
        "description": description,
        "online_only": bool(re.search(r"(?i)nettbutikk|netthandel", description)) and contract.get("partnerType") == "Online",
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": source_url,
    }


def parse_discounts() -> list[dict]:
    html = fetch_html(PAGE_URL)
    token = extract_token(html)
    contracts = fetch_contracts(token)

    discounts = []
    for c in contracts:
        if not is_active(c):
            continue
        card = normalize(c)
        if card:
            discounts.append(card)
    return discounts


def main():
    discounts = parse_discounts()

    print(f"Fant {len(discounts)} medlemsfordeler hos Kobbl")

    output = {
        "provider": "Kobbl",
        "source_page": PAGE_URL,
        "discounts": discounts,
    }

    with open("kobbl_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til kobbl_medlemsfordeler.json")


if __name__ == "__main__":
    main()
