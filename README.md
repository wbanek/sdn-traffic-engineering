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

Mierzone parametry: jitter, packet loss, latency, throughput. Poziomy obciążenia tła: 50%, 70%, 90%.

## Topologie

- **Clos:** 3 spine × 4 leaf, 3 hosty na leaf (video, bg1, bg2)
- **Mesh:** 4 edge + 3 core, 3 hosty na edge; krawędzie łączą się też ze sobą, a rdzenie między sobą (wstępne pomiary lllb i qos100; wyniki oficjalne jeszcze nie wykonane)
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
| QoS-Aware, pełna rezerwa (C, R = 100%) | **0,00%** | 12,9 ± 6,1% |
| QoS-Aware, L3 z zapasem H = 1,5 Mb/s (C) | 0,01 ± 0,04% | 8,7 ± 4,4% |

Rezerwa ścieżki eliminuje utratę wideo; adaptacyjny limit tła (L3) zmniejsza jej koszt dla ruchu tła o ok. 4 pkt proc. względem pełnej rezerwy. Stały limit (L1/L2) chroni wideo tylko dla R ≥ 70%. Szczegóły, ograniczenia i różnice sparowane: [docs/status.md](docs/status.md).

## Dokumentacja

- [docs/status.md](docs/status.md): aktualny stan prac, wyniki testów, znane pułapki, kolejne kroki
- [docs/ryu-sciagawka.md](docs/ryu-sciagawka.md): ściągawka z Ryu (zdarzenia, dispatchery, skróty)
