# sdn-traffic-engineering

Praca inżynierska (Teleinformatyka): **Porównanie wydajności routingu wielościeżkowego i mechanizmów inżynierii ruchu dla strumieni wideo: tradycyjne sieci OSPF a architektura SDN.**

Repozytorium zawiera całe środowisko badawcze jako kod: topologie Containerlab, konfiguracje FRR, kontrolery Ryu, skrypty generowania ruchu oraz analizę wyników.

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
- Szczegóły ustaleń: [docs/notatka_ustalenia_projekt.md](docs/notatka_ustalenia_projekt.md)
