# Faste Rabatter

En app for å søke opp faste medlemsrabatter fra DNB, OBOS, Elbilforeningen,
USBL, LOfavør, Akademikerforbundet, Kobbl, Norsk Fysioterapeutforbund,
Unio, YS, NITO og Pensjonistforbundet på ett sted. Kjører som en PWA
(nettapp) du legger til på hjemskjermen på iPhone – ingen App Store, ingen
Xcode.

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
akademikerforbundet_medlemsfordeler.py → akademikerforbundet_medlemsfordeler.json
kobbl_medlemsfordeler.py         → kobbl_medlemsfordeler.json
fysio_medlemsfordeler.py         → fysio_medlemsfordeler.json
unio_medlemsprodukter.py         → unio_medlemsprodukter.json
ys_medlemsfordeler.py            → ys_medlemsfordeler.json
nito_medlemsfordeler.py          → nito_medlemsfordeler.json
pensjonistforbundet_medlemsfordeler.py → pensjonistforbundet_medlemsfordeler.json
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
python3 akademikerforbundet_medlemsfordeler.py
python3 kobbl_medlemsfordeler.py
python3 fysio_medlemsfordeler.py
python3 unio_medlemsprodukter.py
python3 ys_medlemsfordeler.py
python3 nito_medlemsfordeler.py
python3 pensjonistforbundet_medlemsfordeler.py
python3 combine.py
```

Dette overskriver `webapp/data/discounts.json` med ferske tall. Kjør dette
manuelt når du vil ha oppdaterte rabatter (f.eks. en gang i måneden).

### LOfavør henter alle seks kategoriene

`lofavor_medlemsfordeler.py` henter som standard alle kategoriene på
lofavor.no (Forsikring, Ferie og opplevelser, Hus og hjem, Bank, Juridisk,
Ung) – til sammen 63 tilbud. "Ung"-kategorien overlapper stort sett med de
andre og deduplideres automatisk (samme produktside listet flere steder).
Vil du bare hente noen få kategorier, gi kategori-slugene som argumenter:

```bash
python3 lofavor_medlemsfordeler.py ferie-og-opplevelser bank
```

### Akademikerforbundet henter kun butikk-/leverandørrabattene

`akademikerforbundet_medlemsfordeler.py` henter kategoriene Bil, Ferie,
Trening og sport, Bøker og tidsskrifter og Diverse medlemsfordeler (11
tilbud). Forsikring, Bank, Kurs og Rådgivning er bevisst utelatt – det er
generiske medlemstjenester fra én leverandør (Akaforsikring/Nordea), ikke
butikkrabatter, og siden bruker uansett en helt annen HTML-mal der.

### Kobbl henter fra et skjult API, ikke synlig HTML

`kobbl.no` rendrer ikke rabattene i HTML i det hele tatt - en liten
plugin-script henter dem fra `https://api.bbld.io/memberbenefits/Contracts/current`
(en delt medlemsfordel-plattform for flere boligbyggelag) med en
bearer-token som ligger i selve sidens HTML (`data-token`). Scriptet henter
denne siden først for et ferskt token, akkurat slik nettleseren gjør, og
kaller så samme API. Ingen hemmeligheter er hardkodet - subscription-keyen
er offentlig i sidens egen JS-bunt, og tokenet fornyes automatisk hver gang
siden lastes.

### Norsk Fysioterapeutforbund henter kun det som er unikt

`fysio.no/medlemsfordeler` er en HubSpot-side med en accordion der de
fleste fanene er generiske forbundstjenester eller en gjenfortelling av
Unios sentrale avtaler (dekket av `unio_medlemsprodukter.py`). Skraperen
plukker derfor bare ut de reelt NFF-unike butikkrabattene (Garmin,
Stormberg, Torshov Sport, Fjordkraft, Kunstverket Galleri) - 5 tilbud.

### Unio er hovedorganisasjonen bak flere av forbundene

`unio_medlemsprodukter.py` henter Unios 11 sentrale medlemsprodukter
(Avis, BMW, Cutters, Extra Optical, Stormberg, Nordea, m.fl.). Disse er
samme avtaler som ofte dukker opp igjen hos tilsluttede forbund som
Akademikerforbundet og Norsk Fysioterapeutforbund - det er forventet og
gir et poeng: samme rabatt kan gjelde uansett hvilket Unio-forbund du er
medlem av.

### YS og NITO er egne hovedorganisasjoner/forbund

`ys_medlemsfordeler.py` (24 tilbud) og `nito_medlemsfordeler.py` (30
tilbud, kun "Rabatter"-kategorien - forsikring/bank/juridisk er utelatt
som hos Akademikerforbundet) henter fra hver sin side med egne
partneravtaler, uavhengig av Unio.

### Pensjonistforbundet

`pensjonistforbundet_medlemsfordeler.py` henter alle 33 fordelene fra en
Next.js/Contentful-datastrøm (`__NEXT_DATA__`). Ekstern partnerlenke
finnes ikke i et fast felt, så skraperen søker gjennom hele fordelens
JSON-data etter URL-er og filtrerer bort kjente ikke-partner-domener
(bilder, video, egne sider).

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
- **LOfavør**: 63 rabatter fra alle seks kategoriene (se over). Ekstern lenke
  hentes fra CTA-knappen på produktsiden; noen produkter mangler denne og
  lenker da til selve LOfavør-siden i stedet.
- **Akademikerforbundet**: 11 rabatter (kun butikk-/leverandørkategoriene,
  se over).
- **Kobbl**: 42 rabatter, hentet fra et skjult API (se over). Både bonus-
  og rabattprosent finnes i dataene; `discount_percentage` prioriterer
  selve rabatten fremfor bonus (cashback).
- **Norsk Fysioterapeutforbund**: 5 rabatter (kun NFF-unike, se over).
- **Unio**: 11 rabatter (sentrale medlemsprodukter, se over).
- **YS**: 24 rabatter.
- **NITO**: 30 rabatter (kun "Rabatter"-kategorien, se over).
- **Pensjonistforbundet**: 33 rabatter, hentet fra Next.js/Contentful-data
  (se over).
- Prosentsatser er hentet med regex fra beskrivelsesteksten og kan mangle
  for tilbud som ikke er rene prosent-rabatter (f.eks. faste kronebeløp,
  "2 for 1", rentefordeler).
- **ToS**: Sjekk hver leverandørs vilkår før dette brukes i større skala enn
  personlig bruk.
