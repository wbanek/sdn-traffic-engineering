# Raport: clos-frr

Katalog: `results/official/load-0.7/clos-frr/20261105_211456`

## 1. Scenariusz

- Topologia: `clos` (frr: `clos-frr.clab.yml`)
- Warianty: **ecmp** (FRR, bez kontrolera)
- Czas testu: 60 s, warmup (pomijany w statystykach, liczony od startu każdego przepływu): 5 s, powtórzeń: 20, seed: 42
- Wykonane przebiegi: ecmp/rep1, ecmp/rep10, ecmp/rep11, ecmp/rep12, ecmp/rep13, ecmp/rep14, ecmp/rep15, ecmp/rep16, ecmp/rep17, ecmp/rep18, ecmp/rep19, ecmp/rep2, ecmp/rep20, ecmp/rep3, ecmp/rep4, ecmp/rep5, ecmp/rep6, ecmp/rep7, ecmp/rep8, ecmp/rep9

Harmonogram losowego tła różni się między powtórzeniami (seed + nr powtórzenia, wspólny dla wariantów); poniżej powtórzenie 1.

| id | klasa | źródło → cel | proto | zadana [Mb/s] | DSCP | start–koniec [s] |
|---|---|---|---|---|---|---|
| gen01 | background | h2-bg1 → h3-bg2 | udp | 4.49 | – | 0.1–7.1 |
| gen02 | background | h4-bg2 → h3-bg1 | udp | 3.16 | – | 0.2–5.2 |
| gen03 | background | h4-bg1 → h2-bg2 | udp | 5.25 | – | 0.9–5.9 |
| gen04 | background | h4-bg1 → h1-bg2 | udp | 3.56 | – | 3.3–8.3 |
| gen05 | background | h4-bg1 → h3-bg1 | udp | 2.36 | – | 4.3–59.3 |
| gen06 | background | h1-bg2 → h2-bg1 | udp | 1.93 | – | 4.6–17.6 |
| gen07 | background | h2-bg1 → h3-bg1 | udp | 1.39 | – | 4.7–9.7 |
| gen08 | background | h1-bg1 → h2-bg1 | udp | 3.29 | – | 6.1–34.1 |
| gen09 | background | h3-bg2 → h2-bg1 | udp | 4.51 | – | 7.6–18.6 |
| gen10 | background | h1-bg2 → h3-bg1 | udp | 3.96 | – | 7.8–12.8 |
| gen11 | background | h2-bg1 → h4-bg2 | udp | 5.85 | – | 8.5–22.5 |
| gen12 | background | h1-bg2 → h3-bg1 | udp | 4.90 | – | 9.6–19.6 |
| vid1 | video | h1-video → h4-video | udp | 3.00 | 46 | 10–50 |
| vid2 | video | h2-video → h4-video | udp | 3.00 | 46 | 12–48 |
| gen13 | background | h4-bg1 → h1-bg1 | udp | 3.07 | – | 14.1–24.1 |
| gen14 | background | h3-bg2 → h1-bg2 | udp | 5.37 | – | 16.2–32.2 |
| gen15 | background | h3-bg1 → h1-bg1 | udp | 3.12 | – | 18.1–36.1 |
| gen16 | background | h2-bg1 → h1-bg1 | udp | 4.96 | – | 19.3–24.3 |
| gen17 | background | h2-bg1 → h4-bg2 | udp | 4.86 | – | 21.8–26.8 |
| gen18 | background | h3-bg2 → h1-bg1 | udp | 3.49 | – | 24.3–43.3 |
| gen19 | background | h4-bg2 → h2-bg1 | udp | 2.93 | – | 28.3–57.3 |
| gen20 | background | h1-bg2 → h4-bg2 | udp | 5.68 | – | 30–35 |
| gen21 | background | h4-bg1 → h2-bg1 | udp | 3.04 | – | 30.8–44.8 |
| gen22 | background | h4-bg1 → h2-bg1 | udp | 3.69 | – | 33.1–38.1 |
| gen23 | background | h2-bg2 → h4-bg2 | udp | 1.26 | – | 35.3–55.3 |
| gen24 | background | h3-bg1 → h1-bg2 | udp | 4.88 | – | 35.6–41.6 |
| gen25 | background | h4-bg1 → h1-bg2 | udp | 3.51 | – | 41.2–46.2 |
| gen26 | background | h1-bg1 → h4-bg1 | udp | 5.23 | – | 41.4–59.4 |
| gen27 | background | h1-bg2 → h4-bg1 | udp | 2.10 | – | 44.5–50.5 |
| gen28 | background | h4-bg1 → h1-bg2 | udp | 1.54 | – | 45.4–50.4 |
| gen29 | background | h4-bg1 → h1-bg2 | udp | 1.53 | – | 45.7–52.7 |
| gen30 | background | h1-bg2 → h3-bg1 | udp | 3.69 | – | 46–52 |
| gen31 | background | h2-bg1 → h4-bg2 | udp | 2.18 | – | 47.1–52.1 |
| gen32 | background | h4-bg2 → h3-bg2 | udp | 5.19 | – | 47.3–59.3 |
| gen33 | background | h4-bg2 → h3-bg2 | udp | 2.60 | – | 49.5–55.5 |
| gen34 | background | h2-bg2 → h3-bg2 | udp | 1.75 | – | 49.5–59.5 |

![Harmonogram](timeline.png)

## 2. Wideo: QoS według wariantu

Wartości: średnia ± odchylenie standardowe z powtórzeń.

| przepływ | wariant | przepływność [Mb/s] | jitter [ms] | utrata [%] | RTT mediana [ms] | RTT p95 [ms] |
|---|---|---|---|---|---|---|
| vid1 | ecmp | 2.72 ± 0.41 | 0.222 ± 0.162 | 9.28 ± 13.61 | 11.017 ± 21.839 | 51.959 ± 37.200 |
| vid2 | ecmp | 2.77 ± 0.31 | 0.195 ± 0.106 | 7.41 ± 10.34 | 13.318 ± 23.992 | 41.721 ± 38.662 |

RTT z `ping` co 0,1 s między hostami wideo (osobny przepływ ICMP z tym samym DSCP - w SDN może iść inną ścieżką niż strumień UDP).

![video_vid1.png](video_vid1.png)

![video_vid2.png](video_vid2.png)

## 3. Ruch tła


Agregat tła w obrębie powtórzenia, potem średnia ± odchylenie standardowe po powtórzeniach (utrata = Σ utraconych / Σ wysłanych datagramów; dostarczone = Σ przepływności / Σ zadanych; przepływy trwające nie dłużej niż warmup pominięte).

| wariant | strumieni tła / powt. | dostarczone / zadane [%] | jitter [ms] | utrata [%] |
|---|---|---|---|---|
| ecmp | 28 | 92.8 ± 4.9 | 0.178 ± 0.057 | 7.48 ± 5.39 |

## 4. Obciążenie łączy fabricu

Średnia i maksimum z próbek co 1 s w oknie 0–60 s; MLU = maksymalne obciążenie łącza; drops = pakiety odrzucone przez `tbf` na wyjściu łącza.

| wariant | rep | średnie obciążenie łączy [%] | MLU [%] | łącza > 90% | drops tbf | CPU VM śr./maks. [%] |
|---|---|---|---|---|---|---|
| ecmp | 1 | 22.0 | 101.5 | 9/24 | 3891 | 10 / 13 |
| ecmp | 2 | 31.9 | 102.7 | 12/24 | 22211 | 13 / 20 |
| ecmp | 3 | 36.3 | 103.1 | 11/24 | 35283 | 13 / 18 |
| ecmp | 4 | 24.4 | 102.2 | 5/24 | 8014 | 11 / 14 |
| ecmp | 5 | 28.1 | 102.1 | 11/24 | 4989 | 12 / 16 |
| ecmp | 6 | 18.5 | 102.5 | 7/24 | 5030 | 11 / 13 |
| ecmp | 7 | 29.9 | 103.2 | 12/24 | 6329 | 12 / 17 |
| ecmp | 8 | 28.4 | 102.0 | 13/24 | 13270 | 11 / 16 |
| ecmp | 9 | 29.4 | 103.0 | 11/24 | 23496 | 12 / 16 |
| ecmp | 10 | 28.6 | 102.8 | 11/24 | 20928 | 12 / 18 |
| ecmp | 11 | 29.6 | 102.5 | 12/24 | 24877 | 12 / 18 |
| ecmp | 12 | 19.8 | 101.8 | 7/24 | 3435 | 11 / 15 |
| ecmp | 13 | 31.7 | 101.6 | 11/24 | 4626 | 12 / 15 |
| ecmp | 14 | 26.5 | 102.5 | 9/24 | 31080 | 12 / 15 |
| ecmp | 15 | 33.6 | 103.0 | 12/24 | 28861 | 13 / 19 |
| ecmp | 16 | 29.7 | 102.1 | 10/24 | 11484 | 11 / 16 |
| ecmp | 17 | 29.8 | 102.7 | 9/24 | 27545 | 12 / 16 |
| ecmp | 18 | 23.1 | 102.0 | 7/24 | 2548 | 11 / 15 |
| ecmp | 19 | 26.6 | 101.9 | 11/24 | 4752 | 11 / 18 |
| ecmp | 20 | 26.9 | 102.6 | 7/24 | 9901 | 12 / 15 |

Łącza z obciążeniem > 10% (maksimum [%] / drops, powtórzenie 1):

| łącze | ecmp |
|---|---|
| leaf1→spine1 | 55 / 0 |
| leaf1→spine2 | 101 / 735 |
| leaf1→spine3 | 41 / 0 |
| leaf2→spine1 | 50 / 0 |
| leaf2→spine2 | 64 / 0 |
| leaf2→spine3 | 100 / 259 |
| leaf3→spine1 | 92 / 0 |
| leaf3→spine2 | 51 / 0 |
| leaf3→spine3 | 57 / 0 |
| leaf4→spine1 | 37 / 0 |
| leaf4→spine2 | 72 / 0 |
| leaf4→spine3 | 101 / 0 |
| spine1→leaf1 | 93 / 0 |
| spine1→leaf2 | 55 / 0 |
| spine1→leaf3 | 18 / 0 |
| spine1→leaf4 | 50 / 0 |
| spine2→leaf1 | 59 / 0 |
| spine2→leaf2 | 55 / 0 |
| spine2→leaf3 | 92 / 0 |
| spine2→leaf4 | 101 / 2404 |
| spine3→leaf1 | 101 / 493 |
| spine3→leaf2 | 101 / 0 |
| spine3→leaf3 | 79 / 0 |
| spine3→leaf4 | 61 / 0 |

![Obciążenie łączy](links.png)

## 5. Ścieżki wybrane przez kontroler (powtórzenie 1)

Z logu kontrolera (linie `Flow`), dopasowane po piątce przepływu; ✓ = reguły widoczne w `dump-flows` na tych samych przełącznikach.

| przepływ | ecmp |
|---|---|
| gen01 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen02 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen03 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen04 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen05 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen06 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen07 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen08 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen09 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen10 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen11 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen12 | ECMP (hash L4), nieobserwowana bezpośrednio |
| vid1 | ECMP (hash L4), nieobserwowana bezpośrednio |
| vid2 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen13 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen14 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen15 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen16 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen17 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen18 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen19 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen20 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen21 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen22 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen23 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen24 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen25 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen26 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen27 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen28 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen29 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen30 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen31 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen32 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen33 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen34 | ECMP (hash L4), nieobserwowana bezpośrednio |

## 6. Wnioski

<!-- WNIOSKI:START -->
_Do uzupełnienia: krótkie wnioski wyłącznie na podstawie liczb z sekcji 2–5._
<!-- WNIOSKI:END -->

![Porównanie wariantów](compare.png)

## 7. Wiarygodność pomiaru

- ecmp rep1, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen07: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen24: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen19: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen20: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen08: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen22: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen23: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen06: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen14: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen19: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen24: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen26: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen32: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen39: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen41: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen13: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen35: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen29: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen37: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen43: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen11: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen22: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen32: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen35: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen37: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen06: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen08: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen22: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen33: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen37: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen01: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen20: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen24: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen32: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen01: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen16: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen18: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen19: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen29: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen07: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen12: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen27: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen42: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen45: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen15: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen01: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen11: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen13: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen30: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen33: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen38: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen42: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen22: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen28: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen29: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen21: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen30: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen35: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen42: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen15: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen29: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen11: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen23: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen30: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen27: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen33: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen34: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen37: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen23: przepływ krótszy niż warmup - statystyki z całości
