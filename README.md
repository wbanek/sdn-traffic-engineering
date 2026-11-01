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
- **Mesh:** 4 edge + 3 core, 3 hosty na edge; krawędzie łączą się też ze sobą, a rdzenie między sobą (dotąd tylko przygotowana, nie mierzona)
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
| `results/` | wyniki pomiarów: raporty, CSV, wykresy (bez surowych danych `raw/`) |

## Wyniki (skrót)

Seria `results/reserve-sweep/20261101_180238` (Clos, dwa strumienie wideo 3 Mb/s DSCP 46 + losowe tło, 5 powtórzeń, silne przeciążenie):

| wariant | utrata wideo | utrata tła |
|---|---|---|
| LLLB (B) | 7,93 ± 6,42% | 4,45 ± 3,23% |
| QoS-Aware, pełna rezerwa (C, R = 100%) | **0,00 ± 0,00%** | 12,52 ± 5,91% |
| QoS-Aware, miękka rezerwa (R = 90 / 70 / 50%) | 5,5–5,8% | 5,6–7,0% |

Pełna rezerwa ścieżki chroni wideo całkowicie kosztem ruchu tła; miękka rezerwa w obecnej konstrukcji tego nie robi. Szczegóły, ograniczenia i pozostałe serie: [docs/status.md](docs/status.md).

## Dokumentacja

- [docs/status.md](docs/status.md): aktualny stan prac, wyniki testów, znane pułapki, kolejne kroki
- [docs/ryu-sciagawka.md](docs/ryu-sciagawka.md): ściągawka z Ryu (zdarzenia, dispatchery, skróty)
