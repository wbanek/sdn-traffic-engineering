# AGENTS.md — Kontekst Projektu i Instrukcje Wykonawcze

## 1. Rola i Zasady Działania (STRICT ADVISORY MODE)
- **TRYB PRACY:** Działasz wyłącznie w trybie planowania i doradztwa technicznego (Architect / Advisor).
- **ZAKAZ EDYCJI PLIKÓW:** Pod żadnym pozorem nie modyfikuj, nie twórz ani nie usuwaj plików bezpośrednio w systemie plików (zakaz używania narzędzi zapisu/edycji).
- **FORMAT ODPOWIEDZI:** 
  - Wszystkie propozycje kodu podawaj w blokach Markdown w odpowiedzi na czacie.
  - Skupiaj się na architekturze, punktowych krokach implementacji i kluczowych fragmentach logiki.
  - Unikaj zbędnego lania wody i powtarzalnego kodu boilerplate, chyba że wyraźnie o to poproszę.

## 2. Temat i Cel Projektu Badawczego
- **Tematyka:** Porównanie wydajności routingu wielościeżkowego (Multipath Routing) i mechanizmów inżynierii ruchu (Traffic Engineering) dla strumieni wideo: tradycyjne sieci OSPF a architektura SDN.
- **Główny cel:** Empiryczne zmierzenie i porównanie metryk jakości transmisji wideo (QoS/QoE: jitter, packet loss, throughput, delay) w scenariuszach równomiernego obciążenia łączy oraz przeciążenia ścieżek.
- **Poza zakresem:** awarie łączy/węzłów i mechanizmy reakcji na nie (failover, PortStatus, fast-failover) — nie są częścią pracy.
- **Warianty porównawcze:**
  - A: OSPF + ECMP (FRRouting)
  - B: SDN + LLLB (Least Loaded Link Balancing)
  - C: SDN + autorski algorytm QoS-Aware — rezerwa pasma na jednej ścieżce dla ruchu wideo (DSCP), pozostałe ścieżki dla best-effort
  - D (punkt odniesienia z literatury): SDN + OpenQoS (Egilmez i in., APSIPA 2012) — reaktywny routing QoS dla wideo (CSP, przenoszenie przy przeciążeniu łącza > 70%), bez rezerwacji pasma i bez kolejek; `POLICY=openqos`

## 3. Środowisko i Stos Technologiczny
- **Platforma bazowa:** Maszyna wirtualna z systemem Linux, Containerlab.
- **Topologia:** Clos 3 spine × 4 leaf, 3 hosty/leaf (video, bg1, bg2) oraz mesh (4 edge + 3 core, 3 hosty/edge; przygotowana, jeszcze niemierzona). Kontroler SDN jest niezależny od topologii.
  - wariant A: `topologies/clos-frr.clab.yml`, `topologies/mesh-frr.clab.yml`
  - warianty B/C: `topologies/clos-sdn.clab.yml`, `topologies/mesh-sdn.clab.yml`
- **Adresacja:** hosty /24 (10.1.L.0/24, brama 10.1.L.1, hosty .10/.11/.12). Tylko A: fabric /31 (10.10.S.x/31), loopbacki /32 (10.255.x.x). SDN: stałe MAC hostów `02:00:0L:00:00:HH`, wirtualny MAC bramy `02:00:00:00:00:fe`, dpid leaf1–4 = 0x01–0x04, spine1–3 = 0x11–0x13. Szczegóły: `docs/status.md`.
- **Łącza:** `tc tbf` w `exec` — leaf↔spine 10 Mb/s, host↔leaf 100 Mb/s (po obu końcach łącza).
- **Obrazy:** `quay.io/frrouting/frr:9.0.1` (FRR), `kathara/sdn` (Open vSwitch 3.1), `sdn-ryu:4.34` (własny, `images/ryu/Dockerfile`), `wbitt/network-multitool` (hosty).
- **Architektura tradycyjna:** OSPF area 0 + ECMP (FRRouting, `configs/frr/clos/`, `configs/frr/mesh/`, hash L4).
- **Architektura SDN:** OpenFlow 1.3, kontroler Ryu 4.34 (Python): `controllers/controller_ryu.py` (aplikacja `Fabric`) + `controllers/topo.py` (model sieci z pliku clab). Wybór ścieżki per przepływ, polityka przez zmienną `POLICY` (`rr`, `lllb`, `qos`, `openqos`); wariant C (`qos`): klasyfikacja po DSCP 46, ścieżka rezerwowa dla wideo (`paths[0]`), udział best-effort na rezerwie ograniczony przez `RESERVE_PCT`, pomiar obciążenia per klasa z `FlowStats`.
- **Generowanie i analiza ruchu:** iperf3 (UDP z `-l 1400`, metryki z raportu serwera), ping wideo z DSCP. Lokalny skill `.claude/skills/sdn-test-runner/` (poza repozytorium) uruchamia scenariusze z `scenarios/` i generuje raporty do `results/`. Wyniki i stan prac: `docs/status.md`.

## 4. Oczekiwania Wobec Odpowiedzi
- Projektując rozwiązania dla OSPF, uwzględniaj metryki kosztu interfejsów i zachowanie mechanizmów ECMP.
- Projektując logikę dla kontrolera Ryu, skupiaj się na instalacji reguł przepływów (Flow Mods), obsłudze zdarzeń Packet-In oraz monitorowaniu statystyk portów do dynamicznego sterowania ruchem wideo.
- Podawaj polecenia CLI dla środowiska Linux/Containerlab w sposób zwięzły, gotowy do skopiowania i uruchomienia w terminalu.

## 5. Aktualny stan projektu
Źródło prawdy: `docs/status.md`. Zawsze sprawdź ten plik przed zaproponowaniem kolejnych kroków.