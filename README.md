# sdn-traffic-engineering

Praca inżynierska (Teleinformatyka): **Porównanie wydajności routingu wielościeżkowego i mechanizmów inżynierii ruchu dla strumieni wideo: tradycyjne sieci OSPF a architektura SDN.**

Repozytorium zawiera całe środowisko badawcze jako kod: topologie Containerlab (Clos i mesh), konfiguracje FRR, kontroler Ryu oraz wyniki pomiarów (`results/`).

## Cel

Sprawdzenie, jak trzy podejścia do rozkładania ruchu zachowują się w sieci Spine-Leaf pod rosnącym obciążeniem, ze szczególnym uwzględnieniem ochrony priorytetowego ruchu wideo (znacznik DSCP).

| Wariant | Opis |
|---|---|
| **A** | OSPF + ECMP (FRRouting) |
| **B** | SDN + LLLB, czyli Least Loaded Link Balancing (Ryu + Open vSwitch) |
| **C** | SDN + autorski algorytm QoS-Aware z rezerwą pasma dla wideo (Ryu + Open vSwitch) |
| **D** | punkt odniesienia z literatury: SDN + OpenQoS (Egilmez i in. 2012), reaktywny routing QoS bez rezerwacji |

Mierzone parametry: jitter, packet loss, latency, throughput. Poziomy obciążenia tła: intensywność losowych przepływów tła (`arrival_rate` 0,4 / 0,7 / 1,0).

## Topologie

- **Clos:** 3 spine × 4 leaf, 3 hosty na leaf (video, bg1, bg2)
- **Mesh:** 4 edge + 3 core, 3 hosty na edge; krawędzie łączą się też ze sobą, a rdzenie między sobą (wyniki oficjalne: 20 powtórzeń, jak dla Clos)
- Łącza przełączników: 10 Mb/s, host–przełącznik: 100 Mb/s (`tc tbf`, po obu końcach łącza)
- Kontroler SDN jest niezależny od topologii (model sieci czyta z pliku Containerlab)

## Struktura repozytorium

| Ścieżka | Zawartość |
|---|---|
| `topologies/clos-frr.clab.yml`, `mesh-frr.clab.yml` | wariant A: FRR (OSPF + ECMP) |
| `topologies/clos-sdn.clab.yml`, `mesh-sdn.clab.yml` | warianty B/C: Open vSwitch + kontroler Ryu |
| `configs/frr/clos/`, `configs/frr/mesh/` | konfiguracje OSPF dla wariantu A |
| `controllers/controller_ryu.py` | aplikacja Ryu `Fabric`; polityka wyboru ścieżki przez `POLICY` (`rr`, `lllb`, `qos`) i `RESERVE_PCT` |
| `controllers/topo.py` | model sieci wczytywany z pliku Containerlab |
| `images/ryu/Dockerfile` | obraz kontrolera `sdn-ryu:4.34` |
| `results/` | wyniki pomiarów: raporty, CSV, wykresy (bez surowych danych `raw/`); wyniki oficjalne w `results/official/<topologia>/` |
| `analysis/` | `summary_charts.py` (wykresy zbiorcze), `export_excel.py` (dane do Excela) |

## Wyniki (skrót)

Wyniki oficjalne, Clos (`results/official/`, dwa strumienie wideo 3 Mb/s DSCP 46 + losowe tło, 20 powtórzeń, seed 42, średnia ± sd):

| wariant | utrata wideo | utrata tła |
|---|---|---|
| OSPF + ECMP (A) | 13,8 ± 9,6% | 12,1 ± 6,2% |
| LLLB (B) | 4,9 ± 4,6% | **4,9 ± 3,1%** |
| OpenQoS (D, baseline z literatury) | 4,5 ± 3,3% | 11,3 ± 4,9% |
| QoS-Aware, pełna rezerwa (C, R = 100%) | **0,00%** | 12,9 ± 6,1% |
| QoS-Aware, L3 z zapasem H = 1,5 Mb/s (C) | 0,01 ± 0,04% | 8,7 ± 4,4% |

Mesh (te same harmonogramy, 20 powtórzeń):

| wariant | utrata wideo | utrata tła |
|---|---|---|
| OSPF + ECMP (A) | 10,9 ± 8,0% | 10,4 ± 5,5% |
| LLLB (B) | 10,2 ± 6,2% | **8,5 ± 4,4%** |
| OpenQoS (D, baseline z literatury) | 10,6 ± 7,6% | 10,2 ± 5,5% |
| QoS-Aware, pełna rezerwa (C, R = 100%) | 0,05 ± 0,24% | 26,0 ± 7,5% |
| QoS-Aware, L3 z zapasem H = 1,5 Mb/s (C) | **0,01 ± 0,02%** | 12,5 ± 5,1% |

Rezerwa ścieżki eliminuje utratę wideo; adaptacyjny limit tła (L3) zmniejsza jej koszt dla ruchu tła (na Clos o ok. 4 pkt proc., na mesh o ok. 13 pkt proc. względem pełnej rezerwy). Stały limit (L1/L2) chroni wideo tylko dla R ≥ 70%. Na mesh LLLB nie poprawia wideo względem ECMP. Wariant D (OpenQoS: reaktywny routing QoS bez rezerwacji) chroni wideo słabiej niż C: na Clos na poziomie LLLB, na mesh na poziomie ECMP. Szczegóły, ograniczenia i różnice sparowane: [docs/status.md](docs/status.md).

## Dokumentacja

- [docs/status.md](docs/status.md): aktualny stan prac, wyniki testów, znane pułapki, kolejne kroki
- [docs/ryu-sciagawka.md](docs/ryu-sciagawka.md): ściągawka z Ryu (zdarzenia, dispatchery, skróty)
