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
- **Główny cel:** Empiryczne zmierzenie i porównanie metryk jakości transmisji wideo (QoS/QoE: jitter, packet loss, throughput, delay) w scenariuszach równomiernego obciążenia łączy oraz w stanach awarii/przeciążenia ścieżek.
- **Warianty porównawcze:**
  - A: OSPF + ECMP (FRRouting)
  - B: SDN + LLLB (Least Loaded Link Balancing)
  - C: SDN + autorski algorytm QoS-Aware — rezerwa pasma na jednej ścieżce dla ruchu wideo (DSCP), pozostałe ścieżki dla best-effort

## 3. Środowisko i Stos Technologiczny
- **Platforma bazowa:** Maszyna wirtualna z systemem Linux.
- **Topologia:** 3 spine × 4 leaf, 3 hosty/leaf (video, bg1, bg2). Plik: `topologies/spine-leaf-3x4.clab.yml`
- **Adresacja:** fabric /31 (10.10.S.0/31), hosty /24 (10.1.L.0/24), loopbacki /32 (10.255.x.x). Szczegóły: `docs/adresacja.md`
- **Obrazy:** `quay.io/frrouting/frr:9.0.1` (FRR), `wbitt/network-multitool` (hosty)
- **Architektura tradycyjna:** Dynamiczny routing OSPF (np. demony FRRouting / Bird w kontenerach).
- **Architektura SDN:** Protokół OpenFlow kontrolowany przez aplikacje napisane dla kontrolera Ryu (Python).
- **Generowanie i analiza ruchu:** Narzędzia strumieniowania wideo oraz pomiaru metryk sieciowych

## 4. Oczekiwania Wobec Odpowiedzi
- Projektując rozwiązania dla OSPF, uwzględniaj metryki kosztu interfejsów i zachowanie mechanizmów ECMP.
- Projektując logikę dla kontrolera Ryu, skupiaj się na instalacji reguł przepływów (Flow Mods), obsłudze zdarzeń Packet-In oraz monitorowaniu statystyk portów do dynamicznego sterowania ruchem wideo.
- Podawaj polecenia CLI dla środowiska Linux/Containerlab w sposób zwięzły, gotowy do skopiowania i uruchomienia w terminalu.

## 5. Aktualny stan projektu
Źródło prawdy: `docs/status.md`. Zawsze sprawdź ten plik przed zaproponowaniem kolejnych kroków.