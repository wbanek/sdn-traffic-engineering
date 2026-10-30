# sdn-traffic-engineering

Praca inżynierska (Teleinformatyka): **Porównanie wydajności routingu wielościeżkowego i mechanizmów inżynierii ruchu dla strumieni wideo: tradycyjne sieci OSPF a architektura SDN.**

Repozytorium zawiera całe środowisko badawcze jako kod: topologie Containerlab, konfiguracje FRR i kontroler Ryu. Skrypty generowania ruchu i analiza wyników są w przygotowaniu.

## Cel

Sprawdzenie, jak trzy podejścia do rozkładania ruchu zachowują się w sieci Spine-Leaf pod rosnącym obciążeniem, ze szczególnym uwzględnieniem ochrony priorytetowego ruchu wideo (znacznik DSCP).

| Wariant | Opis |
|---|---|
| **A** | OSPF + ECMP (FRRouting) |
| **B** | SDN + LLLB, czyli Least Loaded Link Balancing (Ryu + Open vSwitch) |
| **C** | SDN + autorski algorytm QoS-Aware z rezerwą pasma dla wideo (Ryu + Open vSwitch) |

Mierzone parametry: jitter, packet loss, latency, throughput. Poziomy obciążenia tła: 50%, 70%, 90%.

## Topologia

- Spine-Leaf: 3 spine × 4 leaf, 3 hosty na leaf
- Łącza leaf-spine: 10 Mb/s, host-leaf: 100 Mb/s (`tc tbf`, po obu końcach łącza)
- Planowana druga topologia: mesh (kontroler SDN jest niezależny od topologii)

## Struktura repozytorium

| Ścieżka | Zawartość |
|---|---|
| `topologies/spine-leaf-3x4.clab.yml` | wariant A: FRR (OSPF + ECMP) |
| `topologies/sdn.clab.yaml` | warianty B/C: Open vSwitch + kontroler Ryu |
| `configs/frr/` | konfiguracje OSPF dla wariantu A |
| `controllers/controller_ryu.py` | aplikacja Ryu `Fabric` (wybór ścieżki: `POLICY=rr` lub `lllb`) |
| `controllers/topo.py` | model sieci wczytywany z pliku Containerlab |
| `images/ryu/Dockerfile` | obraz kontrolera `sdn-ryu:4.34` |

## Dokumentacja

- [docs/status.md](docs/status.md): aktualny stan prac, wyniki testów, znane pułapki, kolejne kroki
- [docs/ryu-sciagawka.md](docs/ryu-sciagawka.md): ściągawka z Ryu (zdarzenia, dispatchery, skróty)
