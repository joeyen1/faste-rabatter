# Faste Rabatter

En app for å søke opp faste medlemsrabatter fra DNB, OBOS, Elbilforeningen,
USBL og LOfavør på ett sted. Kjører som en PWA (nettapp) du legger til på
hjemskjermen på iPhone – ingen App Store, ingen Xcode.

## Slik virker det

1. **Skrapere** (Python) henter rabattlister fra hver leverandørs nettside og
   lagrer dem som JSON.
2. **`combine.py`** slår sammen alle JSON-filene til én fil:
   `webapp/data/discounts.json`.
3. **`webapp/`** er selve appen – ren HTML/CSS/JS, ingen byggesteg. Den leser
   `data/discounts.json` og lar deg søke på butikknavn.

```
dnb_faste_rabatter.py            → dnb_faste_rabatter.json
obos_medlemsfordeler.py          → obos_medlemsfordeler.json
usbl_medlemsfordeler.py          → usbl_medlemsfordeler.json
lofavor_medlemsfordeler.py       → lofavor_medlemsfordeler.json
elbilforeningen_medlemsfordeler.json   (manuelt vedlikeholdt, se under)
                ↓
            combine.py
                ↓
     webapp/data/discounts.json
                ↓
        webapp/ (PWA-en)
```

## Oppdatere dataene

```bash
pip install requests beautifulsoup4

python3 dnb_faste_rabatter.py
python3 obos_medlemsfordeler.py
python3 usbl_medlemsfordeler.py
python3 lofavor_medlemsfordeler.py
python3 combine.py
```

Dette overskriver `webapp/data/discounts.json` med ferske tall. Kjør dette
manuelt når du vil ha oppdaterte rabatter (f.eks. en gang i måneden).

### LOfavør dekker foreløpig bare "Ferie og opplevelser"

`lofavor_medlemsfordeler.py` henter kun kategorien `ferie-og-opplevelser` som
standard (17 tilbud). LOfavør har flere kategorier (Forsikring, Bank, Bolig,
Juridisk m.fl.) – for å hente flere, kjør skriptet med kategori-slugene som
argumenter, f.eks.:

```bash
python3 lofavor_medlemsfordeler.py ferie-og-opplevelser forsikring bank
```

(finn slug-navnet i URL-en til hver kategoriside på lofavor.no)

### Elbilforeningen er et unntak

`elbil.no` er beskyttet av Cloudflare sin bot-beskyttelse, som blokkerer
vanlige script-forespørsler (`requests`/`curl`). Det finnes derfor **ikke**
noe script for denne leverandøren – `elbilforeningen_medlemsfordeler.json`
er et manuelt øyeblikksbilde hentet 2026-07-17. For å oppdatere det:

1. Åpne https://elbil.no/medlemsfordeler/ (og side 2) i en vanlig nettleser
2. Oppdater listen i `elbilforeningen_medlemsfordeler.json` for hånd
3. Kjør `python3 combine.py` på nytt

## Kjøre appen lokalt

```bash
cd webapp
python3 -m http.server 8765
```

Åpne http://localhost:8765 i Safari på Mac for å se den, eller besøk samme
adresse fra iPhone hvis den er på samme WiFi (bytt `localhost` med Macens
lokale IP, f.eks. `http://192.168.1.23:8765`).

For at du skal kunne åpne appen fra iPhone hvor som helst (ikke bare hjemme
på WiFi) og legge den til på hjemskjermen permanent, må `webapp/`-mappen
hostes et sted med en stabil URL – f.eks. gratis på **GitHub Pages** eller
**Netlify**. Si ifra så setter jeg det opp.

## Legge til på hjemskjermen (iPhone)

1. Åpne app-URL-en i Safari
2. Trykk på Del-ikonet (firkant med pil opp)
3. Velg «Legg til på Hjem-skjerm»

Appen får eget ikon og åpnes i fullskjerm som en vanlig app. Den fungerer
også offline etter første besøk (dataene caches).

## Datastruktur

Hvert rabatt-objekt i `discounts.json` ser slik ut:

```json
{
  "provider": "DNB",
  "retailer": "Odlo",
  "discount_percentage": 10,
  "description": "...",
  "online_only": true,
  "requires_code": true,
  "source_url": "https://odlo.no"
}
```

## Kjente forbehold

- **DNB**: 66 rabatter, ekstrahert fra rabattkort-lenker på siden. Delt
  rabattkode (`DNB8547`) vises i appen.
- **OBOS**: 93 rabatter, hentet fra Next.js sin RSC-datastrøm (siden
  server-rendrer ikke rabattene som synlig HTML). Svenske OBOS-fordeler er
  filtrert bort.
- **USBL**: 58 rabatter, vanlig HTML-scraping.
- **Elbilforeningen**: 34 rabatter, manuelt vedlikeholdt (se over).
- **LOfavør**: 17 rabatter (kun "Ferie og opplevelser" foreløpig, se over).
  Ekstern lenke hentes fra CTA-knappen på produktsiden; noen produkter mangler
  denne og lenker da til selve LOfavør-siden i stedet.
- Prosentsatser er hentet med regex fra beskrivelsesteksten og kan mangle
  for tilbud som ikke er rene prosent-rabatter (f.eks. faste kronebeløp,
  "2 for 1", rentefordeler).
- **ToS**: Sjekk hver leverandørs vilkår før dette brukes i større skala enn
  personlig bruk.
