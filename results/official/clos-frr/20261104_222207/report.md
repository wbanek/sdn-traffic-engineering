# Raport: clos-frr

Katalog: `results/official/clos-frr/20261104_222207`

## 1. Scenariusz

- Topologia: `clos` (frr: `clos-frr.clab.yml`)
- Warianty: **ecmp** (FRR, bez kontrolera)
- Czas testu: 60 s, warmup (pomijany w statystykach, liczony od startu każdego przepływu): 5 s, powtórzeń: 20, seed: 42
- Wykonane przebiegi: ecmp/rep1, ecmp/rep10, ecmp/rep11, ecmp/rep12, ecmp/rep13, ecmp/rep14, ecmp/rep15, ecmp/rep16, ecmp/rep17, ecmp/rep18, ecmp/rep19, ecmp/rep2, ecmp/rep20, ecmp/rep3, ecmp/rep4, ecmp/rep5, ecmp/rep6, ecmp/rep7, ecmp/rep8, ecmp/rep9

Harmonogram losowego tła różni się między powtórzeniami (seed + nr powtórzenia, wspólny dla wariantów); poniżej powtórzenie 1.

| id | klasa | źródło → cel | proto | zadana [Mb/s] | DSCP | start–koniec [s] |
|---|---|---|---|---|---|---|
| gen01 | background | h2-bg1 → h3-bg2 | udp | 4.49 | – | 0–7 |
| gen02 | background | h4-bg2 → h3-bg1 | udp | 3.16 | – | 0.1–5.1 |
| gen03 | background | h4-bg1 → h2-bg2 | udp | 5.25 | – | 0.6–5.6 |
| gen04 | background | h4-bg1 → h1-bg2 | udp | 3.56 | – | 2.3–7.3 |
| gen05 | background | h4-bg1 → h3-bg1 | udp | 2.36 | – | 3–60 |
| gen06 | background | h1-bg2 → h2-bg1 | udp | 1.93 | – | 3.2–16.2 |
| gen07 | background | h2-bg1 → h3-bg1 | udp | 1.39 | – | 3.3–8.3 |
| gen08 | background | h1-bg1 → h2-bg1 | udp | 3.29 | – | 4.2–32.2 |
| gen09 | background | h3-bg2 → h2-bg1 | udp | 4.51 | – | 5.3–16.3 |
| gen10 | background | h1-bg2 → h3-bg1 | udp | 3.96 | – | 5.5–10.5 |
| gen11 | background | h2-bg1 → h4-bg2 | udp | 5.85 | – | 5.9–19.9 |
| gen12 | background | h1-bg2 → h3-bg1 | udp | 4.90 | – | 6.7–16.7 |
| gen13 | background | h4-bg1 → h1-bg1 | udp | 3.07 | – | 9.8–19.8 |
| vid1 | video | h1-video → h4-video | udp | 3.00 | 46 | 10–50 |
| gen14 | background | h3-bg2 → h1-bg2 | udp | 5.37 | – | 11.3–27.3 |
| vid2 | video | h2-video → h4-video | udp | 3.00 | 46 | 12–48 |
| gen15 | background | h3-bg1 → h1-bg1 | udp | 3.12 | – | 12.6–30.6 |
| gen16 | background | h2-bg1 → h1-bg1 | udp | 4.96 | – | 13.5–18.5 |
| gen17 | background | h2-bg1 → h4-bg2 | udp | 4.86 | – | 15.3–20.3 |
| gen18 | background | h3-bg2 → h1-bg1 | udp | 3.49 | – | 17–36 |
| gen19 | background | h4-bg2 → h2-bg1 | udp | 2.93 | – | 19.8–48.8 |
| gen20 | background | h1-bg2 → h4-bg2 | udp | 5.68 | – | 21–26 |
| gen21 | background | h4-bg1 → h2-bg1 | udp | 3.04 | – | 21.5–35.5 |
| gen22 | background | h4-bg1 → h2-bg1 | udp | 3.69 | – | 23.2–28.2 |
| gen23 | background | h2-bg2 → h4-bg2 | udp | 1.26 | – | 24.7–44.7 |
| gen24 | background | h3-bg1 → h1-bg2 | udp | 4.88 | – | 25–31 |
| gen25 | background | h4-bg1 → h1-bg2 | udp | 3.51 | – | 28.9–33.9 |
| gen26 | background | h1-bg1 → h4-bg1 | udp | 5.23 | – | 29–59 |
| gen27 | background | h1-bg2 → h4-bg1 | udp | 2.10 | – | 31.2–37.2 |
| gen28 | background | h4-bg1 → h1-bg2 | udp | 1.54 | – | 31.8–36.8 |
| gen29 | background | h4-bg1 → h1-bg2 | udp | 1.53 | – | 32–39 |
| gen30 | background | h1-bg2 → h3-bg1 | udp | 3.69 | – | 32.2–38.2 |
| gen31 | background | h2-bg1 → h4-bg2 | udp | 2.18 | – | 33–38 |
| gen32 | background | h4-bg2 → h3-bg2 | udp | 5.19 | – | 33.1–59.1 |
| gen33 | background | h4-bg2 → h3-bg2 | udp | 2.60 | – | 34.7–40.7 |
| gen34 | background | h2-bg2 → h3-bg2 | udp | 1.75 | – | 34.7–59.7 |
| gen35 | background | h4-bg2 → h2-bg1 | udp | 5.89 | – | 35.5–54.5 |
| gen36 | background | h4-bg2 → h3-bg1 | udp | 4.62 | – | 35.9–49.9 |
| gen37 | background | h1-bg2 → h2-bg2 | udp | 4.50 | – | 36.6–50.6 |
| gen38 | background | h2-bg1 → h4-bg1 | udp | 4.23 | – | 37.9–58.9 |
| gen39 | background | h1-bg2 → h4-bg2 | udp | 5.93 | – | 39.5–44.5 |
| gen40 | background | h1-bg1 → h3-bg1 | udp | 5.99 | – | 40.5–45.5 |
| gen41 | background | h1-bg2 → h3-bg1 | udp | 4.47 | – | 41–50 |
| gen42 | background | h1-bg2 → h3-bg1 | udp | 2.82 | – | 41.7–48.7 |
| gen43 | background | h4-bg2 → h2-bg1 | udp | 4.98 | – | 43.2–49.2 |
| gen44 | background | h4-bg2 → h1-bg2 | udp | 5.97 | – | 43.5–50.5 |
| gen45 | background | h3-bg1 → h4-bg1 | udp | 5.74 | – | 43.8–58.8 |
| gen46 | background | h2-bg1 → h1-bg2 | udp | 1.89 | – | 44.1–49.1 |
| gen47 | background | h2-bg2 → h3-bg1 | udp | 2.94 | – | 46.9–59.9 |
| gen48 | background | h3-bg1 → h1-bg1 | udp | 3.58 | – | 47.7–59.7 |
| gen49 | background | h4-bg1 → h2-bg1 | udp | 5.93 | – | 47.8–57.8 |
| gen50 | background | h4-bg1 → h1-bg1 | udp | 3.20 | – | 47.9–54.9 |
| gen51 | background | h4-bg2 → h3-bg1 | udp | 1.53 | – | 48.5–59.5 |
| gen52 | background | h4-bg2 → h2-bg2 | udp | 2.44 | – | 49.7–59.7 |

![Harmonogram](timeline.png)

## 2. Wideo: QoS według wariantu

Wartości: średnia ± odchylenie standardowe z powtórzeń.

| przepływ | wariant | przepływność [Mb/s] | jitter [ms] | utrata [%] | RTT mediana [ms] | RTT p95 [ms] |
|---|---|---|---|---|---|---|
| vid1 | ecmp | 2.59 ± 0.37 | 0.404 ± 0.191 | 13.79 ± 12.29 | 9.348 ± 21.483 | 63.598 ± 36.822 |
| vid2 | ecmp | 2.59 ± 0.35 | 0.426 ± 0.204 | 13.75 ± 11.51 | 24.778 ± 35.405 | 78.930 ± 50.383 |

RTT z `ping` co 0,1 s między hostami wideo (osobny przepływ ICMP z tym samym DSCP - w SDN może iść inną ścieżką niż strumień UDP).

![video_vid1.png](video_vid1.png)

![video_vid2.png](video_vid2.png)

## 3. Ruch tła


Agregat tła w obrębie powtórzenia, potem średnia ± odchylenie standardowe po powtórzeniach (utrata = Σ utraconych / Σ wysłanych datagramów; dostarczone = Σ przepływności / Σ zadanych; przepływy trwające nie dłużej niż warmup pominięte).

| wariant | strumieni tła / powt. | dostarczone / zadane [%] | jitter [ms] | utrata [%] |
|---|---|---|---|---|
| ecmp | 38 | 88.5 ± 5.5 | 0.302 ± 0.068 | 12.06 ± 6.16 |

## 4. Obciążenie łączy fabricu

Średnia i maksimum z próbek co 1 s w oknie 0–60 s; MLU = maksymalne obciążenie łącza; drops = pakiety odrzucone przez `tbf` na wyjściu łącza.

| wariant | rep | średnie obciążenie łączy [%] | MLU [%] | łącza > 90% | drops tbf | CPU VM śr./maks. [%] |
|---|---|---|---|---|---|---|
| ecmp | 1 | 31.4 | 105.1 | 14/24 | 34253 | 14 / 27 |
| ecmp | 2 | 38.7 | 104.1 | 14/24 | 33609 | 16 / 28 |
| ecmp | 3 | 45.6 | 105.0 | 12/24 | 54572 | 18 / 29 |
| ecmp | 4 | 33.8 | 103.2 | 14/24 | 6539 | 15 / 40 |
| ecmp | 5 | 35.3 | 103.7 | 10/24 | 36208 | 15 / 34 |
| ecmp | 6 | 29.2 | 106.8 | 13/24 | 9689 | 14 / 27 |
| ecmp | 7 | 37.8 | 102.3 | 15/24 | 16237 | 14 / 24 |
| ecmp | 8 | 34.3 | 102.5 | 13/24 | 21257 | 13 / 22 |
| ecmp | 9 | 34.5 | 102.8 | 11/24 | 39184 | 13 / 18 |
| ecmp | 10 | 38.4 | 103.0 | 13/24 | 35409 | 14 / 26 |
| ecmp | 11 | 34.7 | 102.6 | 14/24 | 53495 | 13 / 20 |
| ecmp | 12 | 28.4 | 102.5 | 11/24 | 3772 | 12 / 15 |
| ecmp | 13 | 35.6 | 103.1 | 15/24 | 34939 | 13 / 17 |
| ecmp | 14 | 35.2 | 103.5 | 15/24 | 38775 | 13 / 19 |
| ecmp | 15 | 41.3 | 103.1 | 15/24 | 45214 | 15 / 21 |
| ecmp | 16 | 34.8 | 102.4 | 14/24 | 15360 | 12 / 16 |
| ecmp | 17 | 39.8 | 102.2 | 14/24 | 25419 | 14 / 18 |
| ecmp | 18 | 30.6 | 102.1 | 11/24 | 24333 | 12 / 16 |
| ecmp | 19 | 39.5 | 102.1 | 15/24 | 17739 | 12 / 22 |
| ecmp | 20 | 39.2 | 102.4 | 15/24 | 57900 | 14 / 23 |

Łącza z obciążeniem > 10% (maksimum [%] / drops, powtórzenie 1):

| łącze | ecmp |
|---|---|
| leaf1→spine1 | 94 / 46 |
| leaf1→spine2 | 101 / 2293 |
| leaf1→spine3 | 102 / 1574 |
| leaf2→spine1 | 101 / 1652 |
| leaf2→spine2 | 52 / 0 |
| leaf2→spine3 | 31 / 0 |
| leaf3→spine1 | 0 / 0 |
| leaf3→spine2 | 98 / 29 |
| leaf3→spine3 | 102 / 2176 |
| leaf4→spine1 | 103 / 19213 |
| leaf4→spine2 | 39 / 6 |
| leaf4→spine3 | 102 / 1970 |
| spine1→leaf1 | 1 / 0 |
| spine1→leaf2 | 61 / 0 |
| spine1→leaf3 | 101 / 540 |
| spine1→leaf4 | 105 / 3141 |
| spine2→leaf1 | 86 / 0 |
| spine2→leaf2 | 82 / 0 |
| spine2→leaf3 | 62 / 0 |
| spine2→leaf4 | 100 / 17 |
| spine3→leaf1 | 102 / 1504 |
| spine3→leaf2 | 99 / 92 |
| spine3→leaf3 | 93 / 0 |
| spine3→leaf4 | 45 / 0 |

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
| gen13 | ECMP (hash L4), nieobserwowana bezpośrednio |
| vid1 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen14 | ECMP (hash L4), nieobserwowana bezpośrednio |
| vid2 | ECMP (hash L4), nieobserwowana bezpośrednio |
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
| gen35 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen36 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen37 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen38 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen39 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen40 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen41 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen42 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen43 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen44 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen45 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen46 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen47 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen48 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen49 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen50 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen51 | ECMP (hash L4), nieobserwowana bezpośrednio |
| gen52 | ECMP (hash L4), nieobserwowana bezpośrednio |

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
- ecmp rep1, gen16: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen22: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen28: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep1, gen40: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen44: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep10, gen57: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen13: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen19: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen20: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen32: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen37: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep11, gen53: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen07: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen33: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep12, gen34: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen06: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen12: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen14: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen26: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen41: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen42: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen46: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep13, gen53: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen13: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen41: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen45: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen50: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen51: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep14, gen52: klient: unable to read from stream socket: Resource temporarily unavailable
- ecmp rep14, gen52: BRAK WYNIKU - przepływ odrzucony z tabel
- ecmp rep14, gen53: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen17: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen27: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep15, gen43: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen06: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen11: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen15: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen32: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen40: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen41: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep16, gen44: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen01: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen06: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen08: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen15: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen24: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen45: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen51: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep17, gen57: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen20: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen33: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen34: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep18, gen44: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen01: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen12: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen14: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen16: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen21: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep19, gen53: klient: unable to read from stream socket: Resource temporarily unavailable
- ecmp rep2, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen12: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen27: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep2, gen51: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen11: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen12: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen15: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen29: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen31: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep20, gen48: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen01: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen03: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen09: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen11: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen13: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen15: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen30: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen33: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep3, gen39: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen22: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen28: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen40: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen41: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen46: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep4, gen49: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen02: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen14: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen21: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen25: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen42: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep5, gen55: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen07: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen10: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen15: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen21: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep6, gen28: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen07: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen11: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen23: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen24: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen28: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen34: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen43: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep7, gen49: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen05: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen12: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen33: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen34: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen36: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen37: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen40: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen42: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep8, gen47: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen04: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen14: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen35: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen37: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen41: przepływ krótszy niż warmup - statystyki z całości
- ecmp rep9, gen42: przepływ krótszy niż warmup - statystyki z całości
