"""
Tester parse-logikken mot en syntetisk HTML-snutt bygget for å etterligne
mønsteret vi så i den faktiske sideteksten (bilde-alt med boilerplate,
prosent-badge, butikknavn, beskrivelse). Dette er IKKE ekte DNB-HTML
(vi har ikke nettverkstilgang i sandkassen), men validerer at
ekstraksjonslogikken takler den observerte tekststrukturen riktig.
"""
from dnb_faste_rabatter import parse_discounts

MOCK_HTML = """
<html><body>
<section>
<h2>Faste rabatter</h2>
<ul>
  <li>
    <a href="https://odlo.no">
      <img alt="Faste Rabatter 560x120 Odlo" src="odlo.jpg">
      <span class="badge">10 %</span>
      <h3>Odlo</h3>
      <p>Grunnlagt i Norge i 1946 – perfeksjonert i de sveitsiske Alpene. Tilbudet gjelder i nettbutikken.</p>
    </a>
  </li>
  <li>
    <a href="https://www.hellyhansen.com/">
      <img alt="Faste Rabatter Helly Hansen" src="hh.jpg">
      <span class="badge">10%</span>
      <h3>Helly Hansen</h3>
      <p>Helly Hansen er kjent for sitt vanntette og pustende Helly Tech-materiale. NB! Rabatten gjelder kun i nettbutikk og ikke i fysiske butikker.</p>
    </a>
  </li>
  <li>
    <a href="/kundeprogram/fordeler/supertilbud">Les mer om Supertilbud</a>
  </li>
</ul>
</section>
</body></html>
"""

discounts, code = parse_discounts(MOCK_HTML)
for d in discounts:
    print(d)
print("Antall funnet:", len(discounts))
assert len(discounts) == 2, "Skal kun plukke opp de to eksterne rabattkortene, ikke DNB-interne lenker"
assert discounts[0]["retailer"] == "Odlo"
assert discounts[0]["discount_percentage"] == 10
assert discounts[1]["retailer"] == "Helly Hansen"
print("OK - grunnleggende parse-logikk fungerer som forventet")
