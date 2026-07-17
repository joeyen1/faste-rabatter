"""
Scraper for OBOS sine medlemsfordeler (https://www.obos.no/medlem/medlemsfordeler)

OBOS-siden er en Next.js-app. Fordelene rendres server-side og sendes til
klienten som JSON innebygd i "RSC flight"-datastrømmen (<script>self.__next_f
.push([1, "..."])</script>-tagger), ikke som synlig HTML-markup. Vi henter
denne JSON-en direkte i stedet for å parse HTML-elementer.

Kjør: python3 obos_medlemsfordeler.py
Krever: pip install requests
"""

import json
import re

import requests

URL = "https://www.obos.no/medlem/medlemsfordeler"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

BENEFIT_START = re.compile(
    r'\{"_createdAt":"[^"]*","_id":"[^"]*","_type":"member_memberBenefit"'
)


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return resp.text


def decode_flight_payload(html: str) -> str:
    """Next.js sender siden som flere self.__next_f.push([1, "<escaped json/js>"])
    kall. Vi slår sammen alle bitene til én lang tekststreng vi kan søke i."""
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    full = "".join(chunks)
    # Bitene er JS-string-literal-escapet (\uXXXX, \", osv.) - unicode_escape
    # dekoder dette, men tolker samtidig UTF-8-byte-sekvenser som latin1,
    # så vi må kode tilbake til bytes og lese dem som UTF-8 på nytt.
    return full.encode().decode("unicode_escape").encode("latin1").decode("utf-8", errors="replace")


def extract_balanced_json(text: str, start: int) -> str | None:
    """Finn hele det balanserte {...}-objektet som starter på `start`,
    med respekt for anførselstegn og escaping inni strenger."""
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
    return None


def extract_benefit_objects(full_text: str) -> list[dict]:
    objs = []
    for m in BENEFIT_START.finditer(full_text):
        raw = extract_balanced_json(full_text, m.start())
        if not raw:
            continue
        try:
            objs.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return objs


def block_text(portable_text_blocks) -> str:
    if not portable_text_blocks:
        return ""
    parts = []
    for block in portable_text_blocks:
        for child in block.get("children", []):
            parts.append(child.get("text", ""))
    return re.sub(r"\s+", " ", " ".join(parts)).strip()


def is_norway(benefit: dict) -> bool:
    """Filtrer bort OBOS Sverige-fordeler (siden inneholder begge)."""
    areas = benefit.get("areas") or []
    names = {(a.get("name") or "").lower() for a in areas}
    return not ({"sverige", "stockholm"} & names)


def normalize(benefit: dict) -> dict | None:
    company = benefit.get("company") or {}
    retailer = re.sub(r"\s+", " ", (company.get("name") or "")).strip()
    if not retailer:
        return None

    description = block_text((benefit.get("externalView") or {}).get("description"))
    if not description:
        description = re.sub(r"\s+", " ", (benefit.get("hero") or {}).get("ingress") or "").strip()

    # (?<![\d,]) unngår å plukke opp desimaldelen i f.eks. "4,55 %" rente
    pct_match = re.search(r"(?<![\d,])(\d{1,3})\s?(?:%|prosent)", description, re.I)
    percentage = int(pct_match.group(1)) if pct_match else None

    login_cta = (benefit.get("externalView") or {}).get("loginCtaDescription", "") or ""
    requires_code = bool(re.search(r"(?i)kode", login_cta))

    slug = (benefit.get("slug") or {}).get("current")
    source_url = f"https://www.obos.no/medlem/medlemsfordeler/{slug}" if slug else None

    return {
        "provider": "OBOS",
        "retailer": retailer,
        "discount_percentage": percentage,
        "description": description,
        "online_only": bool(re.search(r"(?i)på nett|nettbutikk|netthandel", description)),
        "requires_code": requires_code,
        "source_url": source_url,
    }


def parse_discounts(html: str) -> list[dict]:
    full_text = decode_flight_payload(html)
    benefits = extract_benefit_objects(full_text)

    discounts = []
    seen = set()
    for b in benefits:
        if not is_norway(b):
            continue
        card = normalize(b)
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

    print(f"Fant {len(discounts)} medlemsfordeler hos OBOS")

    output = {
        "provider": "OBOS",
        "source_page": URL,
        "discounts": discounts,
    }

    with open("obos_medlemsfordeler.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Lagret til obos_medlemsfordeler.json")


if __name__ == "__main__":
    main()
