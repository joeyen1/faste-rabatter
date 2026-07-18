"""
Scraper for Pensjonistforbundet sine medlemsfordeler
(https://www.pensjonistforbundet.no/medlemsfordeler)

Next.js-side med data i __NEXT_DATA__. Oversiktssiden har alle 33
fordelene i pageProps.allBenefits (tittel, "highlight" med rabattsats,
tekst), men mangler en ren ekstern lenke til partnerens nettside - den må
hentes fra hver enkelt fordelsside (pageProps.benefit), der den ofte ligger
gjemt i en av flere Contentful-rich-text-moduler uten fast feltnavn. Vi
søker derfor gjennom hele JSON-blobben til hver fordel etter URL-er og
filtrerer bort kjente ikke-partner-domener (bilder, video, egne sider).

Kjør: python3 pensjonistforbundet_medlemsfordeler.py
Krever: pip install requests
"""

import json
import re

import requests

BASE_URL = "https://www.pensjonistforbundet.no"
INDEX_URL = f"{BASE_URL}/medlemsfordeler"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)

# Domener som dukker opp i rich text-moduler men ikke er selve partneren
# (bilder/CDN, videoembeds, generell helseinfo, egne sider).
NON_PARTNER_DOMAINS = (
    "ctfassets.net",
    "contentful.com",
    "pensjonistforbundet.no",
    "vimeo.com",
    "youtube.com",
    "youtu.be",
    "helsedirektoratet.no",
    "helsenorge.no",
)


def fetch_next_data(url: str) -> dict:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    m = NEXT_DATA_RE.search(resp.text)
    if not m:
        raise RuntimeError(f"Fant ikke __NEXT_DATA__ på {url}")
    return json.loads(m.group(1))


def clean_text(s: str) -> str:
    # Fjern nullbredde-mellomrom o.l. usynlige tegn som av og til sniker
    # seg inn i Contentful sin rich text.
    s = re.sub(r"[\u200b-\u200f\ufeff]", "", s or "")
    return re.sub(r"\s+", " ", s).strip()


def find_partner_url(benefit: dict, fallback_url: str) -> str:
    blob = json.dumps(benefit)
    # Stopp på "]" og ")" i tillegg til anførselstegn/whitespace, ellers
    # dras markdown-lenker som [tekst](url) inn som del av URL-en.
    for url in re.findall(r'https?://[^"\\\s\]\)]+', blob):
        if not any(domain in url for domain in NON_PARTNER_DOMAINS):
            return url.rstrip(").,")
    return fallback_url


def build_card(benefit: dict, detail_url: str) -> dict:
    title = clean_text(benefit.get("title"))
    highlight = clean_text(benefit.get("highlight"))
    summary = clean_text(benefit.get("summary"))
    content = clean_text(benefit.get("content"))

    description = clean_text(" - ".join(p for p in [highlight, summary, content] if p))

    pct_match = re.search(
        r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", highlight + " " + content, re.I
    )
    percentage = int(pct_match.group(1)) if pct_match else None

    return {
        "provider": "Pensjonistforbundet",
        "retailer": title,
        "discount_percentage": percentage,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": bool(re.search(r"(?i)rabattkode|kampanjekode", description)),
        "source_url": find_partner_url(benefit, detail_url),
    }


def main():
    index_data = fetch_next_data(INDEX_URL)
    all_benefits = index_data["props"]["pageProps"]["allBenefits"]

    print(f"Fant {len(all_benefits)} medlemsfordeler i oversikten, henter detaljer ...")

    discounts = []
    for b in all_benefits:
        slug = b.get("slug")
        if not slug:
            continue
        detail_url = f"{INDEX_URL}/{slug}"
        try:
            detail_data = fetch_next_data(detail_url)
            benefit = detail_data["props"]["pageProps"]["benefit"]
        except (requests.RequestException, KeyError, RuntimeError) as e:
            print(f"  Hopper over {b.get('title')}: {e}")
            benefit = b  # bruk oversiktsdataene som fallback

        discounts.append(build_card(benefit, detail_url))

    print(f"Fant {len(discounts)} medlemsrabatter hos Pensjonistforbundet")

    output = {
        "provider": "Pensjonistforbundet",
        "source_page": INDEX_URL,
        "discounts": discounts,
    }

    with open("pensjonistforbundet_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til pensjonistforbundet_medlemsfordeler.json")


if __name__ == "__main__":
    main()
