# Status projektu (ostatnia aktualizacja: 2026-11-01)

## Pliki topologii (od 2026-11-01)
| Plik | Co | Lab (`name:`) |
|---|---|---|
| `topologies/clos-frr.clab.yml` | wariant A, Clos 3 spine × 4 leaf, FRR (OSPF + ECMP) | `spine-leaf-3x4` |
| `topologies/clos-sdn.clab.yml` | warianty B/C, Clos, OVS + Ryu (mgmt kontrolera 172.20.20.100) | `sdn` |
| `topologies/mesh-frr.clab.yml` | wariant A, mesh (4 edge + 3 core), FRR | `mesh-frr` |
| `topologies/mesh-sdn.clab.yml` | warianty B/C, mesh, OVS + Ryu (mgmt kontrolera 172.20.20.101) | `mesh-sdn` |

Konfiguracje OSPF: `configs/frr/clos/{leafs,spines}/`, `configs/frr/mesh/{edge1-4,core1-3}.conf`.
Wszystkie cztery topologie mają po 7 przełączników/routerów, 12 hostów (h1..h4 × video/bg1/bg2,
10.1.L.10/11/12) i 12 łączy fabric 10 Mb/s (`burst 100kbit`) oraz 12 łączy hostów 100 Mb/s
(`burst 320kbit`). Zbiór łączy i numery `ethN` są identyczne w parach SDN/FRR (sprawdzone
skryptem). Mesh: edge1–edge2, edge3–edge4, edge↔core (po 2), core1–core3, core2–core3;
przełączniki brzegowe dpid 1–4, core 0x11–0x13. **Mesh nie był jeszcze wdrażany w labie ani
mierzony** (sprawdzone tylko parsowanie `mesh-sdn` przez `topo.py`, np. edge1→edge4: 1 ścieżka
2-hopowa przez core2 + trzy 3-hopowe, oraz spójność /31, router-id i bindów w `mesh-frr`).
W mesh najkrótsza ścieżka bywa jedna, więc OSPF-ECMP ma tam mniej równoważnych ścieżek niż
SDN (`slack=1`) — różnica wynika z natury algorytmów.

## Działa — wariant A (OSPF + ECMP)
- Topologia 3 spine × 4 leaf, 3 hosty/leaf wdrożona
(`topologies/clos-frr.clab.yml`)
- Adresacja IP (fabric /31, hosty /24, loopbacki /32) ustawiona przez `exec`
- Bridge host-side na leafach — zweryfikowany (ping h1-video ↔ h1-bg1)
- Bramy domyślne na hostach (`ip route replace default via 10.1.L.1`; `add` pada na
konflikcie z trasą mgmt eth0)
- OSPF area 0 na wszystkich 7 routerach (`configs/frr/clos/`, ospfd.conf per węzeł,
bind-mount do /etc/frr):
sąsiedzi FULL, interfejsy p2p, timery ~1 s (dead-interval minimal hello-multiplier
4)
- ECMP: maximum-paths 3, hash L4 (fib_multipath_hash_policy=1) — rozrzut przepływów
potwierdzony na licznikach (8 strumieni UDP → wszystkie 3 uplinki leaf1, rozkład
nierównomierny)
- Limity `tc tbf` w exec topologii: leaf↔spine 10mbit/burst **100kbit** (wyrównane z SDN
2026-10-30; wcześniej 32kbit), host↔leaf 100mbit/burst 320kbit, po obu końcach łącza
- Test (jeszcze przy burst 32kbit): wideo UDP 3 Mb/s DSCP EF bezstratnie, jitter 0.216 ms
- Wariant A uczestniczy w pomiarach jako `ecmp` (patrz „Wyniki pomiarów”); ścieżki ECMP nie
są obserwowane bezpośrednio (hash L4)

## Działa — SDN (warianty B/C, infrastruktura)
- Topologia `topologies/clos-sdn.clab.yml` (wcześniej `sdn.clab.yaml`): ten sam układ 3×4 +
hosty, przełączniki OVS 3.1.0 (`kathara/sdn`), OpenFlow 1.3
- Jednolity exec na wszystkich 7 OVS, w tej kolejności: `fail-mode secure` →
`protocols=OpenFlow13` → stały `datapath-id` → `add-port … ofport_request=N` →
`tc tbf` → `set-controller` na końcu (łączy się dopiero z gotową konfiguracją)
- datapath-id: leaf1–4 = `0x01`–`0x04`, spine1–3 = `0x11`–`0x13`
- Numer portu OpenFlow = numer interfejsu: leaf uplinki 1–3 (eth1→spine1, eth2→spine2,
eth3→spine3), hosty 10/11/12 (video/bg1/bg2); spine porty 1–4 = leaf1–4
- Limity `tc tbf` w SDN: leaf↔spine 10mbit/burst **100kbit** (obie strony łącza),
host↔leaf 100mbit/burst 320kbit
- Zweryfikowane po deployu na wszystkich 7 przełącznikach: poprawne dpid i numery
portów, porty LIVE, `fail_mode: secure`, `is_connected: true`, tbf burst 12800b
- Własny obraz kontrolera `sdn-ryu:4.34` (`images/ryu/Dockerfile`, z `pbr`):
`docker build -t sdn-ryu:4.34 images/ryu/`
- Stałe MAC hostów w `clos-sdn.clab.yml` (exec: `ip link set dev eth1 address`):
`02:00:0L:00:00:HH` (L = numer leafa, HH = ostatni oktet IP hex: 0a/0b/0c)
- Kontroler (mgmt 172.20.20.100:6653) uruchamia własną aplikację
`controllers/controller_ryu.py` (klasa `Fabric`); binds: `../controllers:/controllers`
i `../topologies:/topologies:ro`, plik topologii wskazuje `env: TOPO_FILE` (musi zgadzać się
z nazwą pliku, razem z rozszerzeniem `.yml`); zmiana kodu → `docker restart clab-sdn-ryu-controller`;
`env:` kontrolera: `POLICY: ${POLICY:=lllb}`, `RESERVE_PCT: ${RESERVE_PCT:=100}` (Containerlab
podstawia zmienne powłoki przy deployu)
- **Kontroler uniwersalny (niezależny od topologii)** — 2026-10-22:
  - `controllers/topo.py` (klasa `Topology`): wczytuje plik clab i z komend exec + `links`
  buduje model sieci: przełączniki (dpid z `datapath-id`, porty z `ofport_request`),
  graf `adj` (dpid → {sąsiad: port}), hosty (IP, MAC, podsieć, brama, przełącznik, port),
  bramy per przełącznik brzegowy; `next_hops_to(dst)` = drzewo najkrótszych ścieżek (BFS
  od celu, remis → najmniejszy dpid) — wolne od pętli w każdej topologii (Clos, mesh)
  - w `controller_ryu.py` brak założeń o Clos (usunięte `LEAVES`, `SPINES`, `HOST_PORTS`,
  `UP_LINK`, `gw_ip()`, `leaf_of()`, `self.hosts`); jedyna stała: `GW_MAC`
  02:00:00:00:00:fe (wirtualny MAC bramy)
  - reguły proaktywne przy połączeniu przełącznika (nieznany dpid → ostrzeżenie, pomijany):
  prio 100 drop IPv6/LLDP; prio 60 reguła hosta (`ipv4_dst=host → eth_src=GW_MAC,
  eth_dst=MAC hosta, dec_ttl, port hosta`) na jego przełączniku; prio 50 trasa domyślna
  do podsieci każdego innego przełącznika brzegowego (port z `next_hops_to`); prio 0
  table-miss → kontroler
  - proxy ARP z topologii: brama (z `default via` hostów) → `GW_MAC`; host z tego samego
  przełącznika → jego MAC; Packet-In obsługiwany tylko z portów hostów
  - `_learn` tylko weryfikuje ruch względem topologii (ostrzeżenie „Unexpected host” przy
  złym przełączniku/porcie, „MAC … changed” + nowa reguła przy zmianie MAC)
  - test w labie (2026-10-22): ping w obrębie leafa (h1-video → 10.1.1.11) i między
  leafami (h1-video → 10.1.4.10, → 10.1.3.12) — 0% strat; brak błędów w logu;
  `traceroute` pokazuje `1 *`, `2 10.1.4.10` (patrz pułapki)
  - trasa domyślna w Clos zawsze przez spine1 — po kroku 6 używana tylko na tranzycie
  jako zapas dla pierwszego pakietu
- **Wielościeżkowość: wybór ścieżki per przepływ** — 2026-10-26:
  - `topo.py`: `hop_count(src, dst)` (BFS), `paths(src, dst, k=4, slack=1)` — ścieżki
  proste (DFS) o długości ≤ najkrótsza + slack, sortowane (długość, dpid); `path_ports(path)`
  → `[(dpid, port wyjściowy), …]` bez ostatniego przełącznika. Clos: `paths(1, 4)` =
  `[[1,17,4], [1,18,4], [1,19,4]]`; `slack=2` daje tranzyt przez leaf (dlatego slack=1);
  test na sztucznym mesh: 2 najkrótsze + 2 o hop dłuższe
  - `controller_ryu.py`: `self.paths[(src, dst)]` liczone raz w `__init__` dla każdej pary
  przełączników brzegowych (Clos: 12 par)
  - przełącznik brzegowy: obca podsieć (prio 50) → CONTROLLER; tranzyt: trasa domyślna
  - `_route_flow`: klucz 5-tuple `(proto, src, dst, sport, dport)` (porty `None` dla ICMP),
  `select_path` (polityka wg `POLICY`, patrz krok 8), reguły prio 70 z 5-tuple na każdym
  hopie od końca ścieżki, `idle_timeout=10`, Packet-Out pierwszego pakietu wprost na port
  uplinku; log `Flow (…) -> leaf1 -> spine2 -> leaf4 (loads 0% 52% 0%)`
  - test (2026-10-26, round-robin): 48/48 pingów (4 hosty źródłowe × 12 celów), trzy pingi
  do 10.1.4.10/11/12 → spine1, spine2, spine3; odpowiedzi z leaf4 własnym licznikiem
  (asymetria jak w ECMP); reguły 70 z rosnącym `n_packets` na leaf1, spine'ach, leaf4
- **Krok 7: monitor obciążenia łączy** — 2026-10-27:
  - wątek `_monitor` (`hub.spawn`): co 1 s `OFPPortStatsRequest(dp, 0, OFPP_ANY)` do każdego
  połączonego przełącznika; log `Links: leaf1:2->spine2 5.15Mb/s 52%, …` dla łączy > 100 kb/s
  - `port_stats_handler` (`EventOFPPortStatsReply`): tylko porty z `link_peer` ((dpid, port)
  → sąsiad; 24 kierunki łączy w Clos, bez hostów i `LOCAL`); `link_bps[(dpid, port)] =
  Δtx_bytes·8/Δt`, czas z `duration_sec + duration_nsec/1e9` (zegar przełącznika); pierwszy
  odczyt i ujemna różnica pomijane. `tx_bytes` = ruch wychodzący → każdy kierunek łącza osobno
  - `path_load(path)` = wykorzystanie najbardziej obciążonego łącza ścieżki (wąskie gardło),
  względem 10 Mb/s wpisanych na sztywno (`/ 10_000_000` w `path_load` i w logu `_monitor`)
  - test: iperf3 UDP 5 Mb/s → `leaf1:2->spine2 5.15Mb/s 52%` (narzut ramki 1442/1400 B)
- **Krok 8: wariant B (LLLB)** — 2026-10-28:
  - zmienna `POLICY` (env w `clos-sdn.clab.yml`, domyślnie `lllb`): `rr` = round-robin per para
  (zostaje do porównań), `lllb` = `min(paths, key=path_load)`; remis → pierwsza ścieżka
  z listy (sortowanie z `topo.paths`, w Clos spine1); log `Path selection policy: …` przy starcie
  - rezerwacja tymczasowa: po wyborze +0,5 Mb/s w `link_bps` na łączach wybranej ścieżki —
  kolejne przepływy w tej samej sekundzie widzą, że ścieżka nie jest pusta (ochrona przed
  „herdingiem”); następny pomiar nadpisuje ją prawdziwą wartością
  - `self.active` (piątka → (ścieżka, czas)): duplikat Packet-In tego samego przepływu
  w ciągu 2 s dostaje tę samą ścieżkę bez ponownego wyboru (patrz pułapki); czyszczenie
  w `_monitor`
  - `loads` w logu `Flow` liczone **przed** `select_path` (bez własnej rezerwacji), w kolejności
  `self.paths[(src, dst)]`
- **Testy LLLB** (2026-10-28, Clos, leaf1 → leaf4, iperf3 UDP):
  - test 1 — pusta sieć, 3 przebiegi po 3 Mb/s z przerwą 15 s: za każdym razem TCP sterujący
  → spine1 (`0% 0% 0%`), UDP → spine2 (`5% 0% 0%` — działa rezerwacja); deterministyczne;
  każda piątka w logu dokładnie raz (po poprawce duplikatów)
  - test 2 — omijanie obciążenia: strumień 6 Mb/s (spine2, 60%), po ~3 s drugi 3 Mb/s →
  TCP spine1, UDP **spine3** (`loads 5% 61% 0%`); oba 0% strat (0/2382, 0/397). Uwaga:
  test bez `-l 1400` (datagramy ~9,2 KB) → jitter 2,5 ms / 0,29 ms nieporównywalny
  - test 3 — 3 strumienie po 3 Mb/s startujące jednocześnie (`-l 1400`): rezerwacja działa
  (loads rosną 0→5→10%, 6 przepływów = po 2 na spine), ale UDP .11 i .12 trafiły razem na
  spine3 (6,18 Mb/s, 62%), a na spine2 poszły dwa kanały sterujące TCP — patrz ograniczenie
  LLLB w sekcji „Nie działa”
  - kierunek powrotny liczony osobno (`loads 0% 0% 0%` przy UDP w jedną stronę) — poprawne
- **Krok 9: wariant C (QoS-Aware)** — 2026-10-30/31:
  - klasyfikacja przy Packet-In: `video = (ip_pkt.tos >> 2) == VIDEO_DSCP` (46, EF); klasa
  zapamiętana w `self.flow_class[flow]`; log `Flow (…) -> leaf1 -> spine1 -> leaf4 (video|be, loads …)`.
  Kanał sterujący TCP iperf3 nie ma DSCP (best-effort); `ping -Q 184` jest wideo, więc
  w C idzie ścieżką rezerwową (RTT opisuje wtedy drogę wideo)
  - `POLICY=qos`: ścieżka rezerwowa = `paths[0]` (w Clos zawsze spine1, dla każdej pary);
  wideo → rezerwa, o ile `path_load(rezerwa) < SPILL` (0,9), inaczej LLLB po wszystkich;
  best-effort → pozostałe ścieżki (LLLB wśród nich) + rezerwa tylko gdy udział best-effort na
  rezerwie `class_load(rezerwa, "be") < (100 - RESERVE_PCT) / 100`. `RESERVE_PCT` (env,
  domyślnie 100) = część łącza rezerwowego dla wideo; 100 = best-effort nigdy na rezerwie
  - pomiar per klasa: co 1 s `OFPFlowStatsRequest`, `flow_stats_handler` liczy z liczników
  bajtów reguł prio 70 przepływność każdego przepływu i sumuje ją po (przełącznik, port
  wyjściowy) w `class_bps[(dpid, port)] = {"video": b/s, "be": b/s}`; `class_load(path, cls)`
  = wąskie gardło ścieżki dla klasy; rezerwacja 0,5 Mb/s trafia do `link_bps` i `class_bps`
  - **błąd znaleziony w pomiarach i naprawiony (2026-10-31):** pierwotny „zawór” SPILL
  wpuszczał best-effort na rezerwę, gdy wszystkie inne ścieżki miały ≥ 90% (wtedy kandydatem
  była pełna lista i LLLB wybierał rezerwę z samym wideo); w serii z zaworem 27 z 276
  przepływów best-effort w qos100 trafiło na spine1, a straty wideo korelowały z ilością
  best-effort na rezerwie. Teraz best-effort wybiera zawsze spośród `allowed`; zawór zostaje
  tylko dla wideo
  - test offline (`select_path` bez labu): `R=100` → best-effort `[18, 19, 18, 19, …]`, nigdy
  17 (nawet przy 95% na spine2/3); `R=70` → `[17×6, 18, 19]` (rezerwa do limitu 30%)
  - literówki w nazwie zdarzenia Ryu (`EventOFPFlowStatsReplay` zamiast `Reply`) wywalają
  import kontrolera od razu przy starcie
- **Narzędzie pomiarowe** (lokalny skill `.claude/skills/sdn-test-runner/`, poza repozytorium —
  `.claude` w `.gitignore`; scenariusze w `scenarios/*.yml`, kopia scenariusza w każdym wyniku):
  - `run_scenario.py scenarios/<nazwa>.yml [--only a,b] [--dry-run]`: dla każdego powtórzenia
  i wariantu: sprawdzenie labu, odtworzenie kontrolera z env wariantu (`containerlab deploy
  --reconfigure`, bo containerlab 0.79 nie pozwala na `--node-filter` na wdrożonym labie),
  iperf3 (serwer `-s -1 -J` + klient wg harmonogramu), ping wideo z DSCP, liczniki łączy co
  1 s, `dump-flows`, log kontrolera; przerwa 15 s (> `idle_timeout`); kolejność wariantów
  ABBA
  - warianty: `ecmp` (lab FRR), `lllb`, `rr`, `qos`, `{name: qos90, policy: qos,
  reserve_pct: 90}`; zmienne env muszą być w pliku topologii jako `KLUCZ: ${KLUCZ:=domyślna}`
  - `vary_per_repetition: true` w scenariuszu: inny losowy harmonogram tła w każdym
  powtórzeniu (`seed + nr`), wspólny dla wszystkich wariantów w danym powtórzeniu
  - `analyze.py results/<scenariusz>/<czas>`: `report.md` (wideo, tło, obciążenie łączy,
  ścieżki, wnioski, wiarygodność), CSV i wykresy. Tło liczone jako agregat per powtórzenie
  (utrata = Σ utraconych / Σ wysłanych; przepływy ≤ warmup pominięte), potem średnia ± sd
  - uruchamianie bez sudo (użytkownik w grupie `clab_admins` i `docker`); matplotlib tylko
  w `.venv` (analizę puszczać `.venv/bin/python`)
- **Wyniki pomiarów** (Clos, UDP `-l 1400`, wideo 3 Mb/s DSCP 46; pełne raporty w `results/`):
  - `lllb-vs-rr-basic` (5 pow., scenariusz deterministyczny): wideo LLLB 3,04 ± 2,10% strat,
  RR 0,00%; tło LLLB 0,07 / 0,03 / 0,01 / 3,53%, RR 30,5 / 44,2 / 6,3 / 44,6%; odrzuceń
  `tbf`: LLLB ok. 0,8 tys., RR ok. 32 tys. na przebieg
  - `random-ecmp-lllb-rr` (5 pow., losowe tło, wspólne dla wariantów): utrata tła ECMP
  11,74 ± 4,59%, RR 9,10 ± 4,63%, LLLB 4,63 ± 2,99% (LLLB najlepszy w 5/5 powtórzeń); wideo
  bez rozstrzygnięcia (sd ≈ średnia)
  - `lllb-vs-qos-basic` (5 pow., deterministyczny): wideo qos 0,00% vs LLLB 2,52 ± 1,78%;
  jitter 0,065 vs 0,439 ms; RTT 0,031 vs 58,3 ms; koszt: tło 8,29% vs 0,51% strat,
  odrzuceń `tbf` ok. 11× więcej
  - `reserve-sweep` 20261030_224134 (6 wariantów, 5 pow., z błędnym zaworem SPILL): brak
  efektu R, bo best-effort wchodził na rezerwę — wynik unieważniony poprawką powyżej
  - `reserve-sweep-quick` (1 pow., po poprawce): qos100 — 0 przepływów best-effort na spine1,
  wideo 0,00% strat
  - **`reserve-sweep` 20261101_180238 (wynik właściwy: lllb, qos100/90/70/50, 5 pow., 2 wideo
  + losowe tło, silne przeciążenie, MLU 102–125%):** wideo (śr. 2 strumieni): LLLB 7,93 ± 6,42%,
  **qos100 0,00 ± 0,00% (5/5)**, qos90 5,51 ± 3,94%, qos70 5,76 ± 4,27%, qos50 5,70 ± 6,77%;
  jitter wideo 0,458 ms (LLLB) vs 0,088 ms (qos100); RTT p95 96,7 vs 0,06 ms. Tło: LLLB 4,45%,
  qos100 12,52%, qos90 6,95%, qos70 5,86%, qos50 5,58%; odrzuceń `tbf` (suma): LLLB 68,8 tys.,
  qos100 157 tys. (×2,3), qos90/70/50 80–91 tys.
  - **wniosek:** pełna rezerwa (R = 100%) chroni wideo całkowicie kosztem ruchu tła; R < 100%
  w tej konstrukcji praktycznie nie chroni wideo, bo limit udziału best-effort to bramka
  wejścia (rozmiar nowego przepływu nieznany): w qos90 udział best-effort na rezerwie
  sięgał średnio 17–26% i do 40% (zamiast 10%)
- Podmiana samego kontrolera: `containerlab deploy -t clos-sdn.clab.yml --reconfigure`
(pełny redeploy ok. 30 s; `destroy` kontrolera + `deploy --node-filter` działa tylko na labie
bez pozostałych węzłów — containerlab 0.79 zgłasza błąd na wdrożonym labie)
- Ryu 4.34 także na hoście w `.venv` (Python 3.9) — do podpowiedzi i lintowania w IDE;
uruchamianie i pomiary w kontenerze:
  ```bash
  uv venv --seed -p 3.9 .venv && source .venv/bin/activate
  pip install setuptools==58.2.0 wheel pbr
  pip install --no-build-isolation eventlet==0.30.2 dnspython==1.16.0 ryu==4.34
  ```
- Ściągawka Ryu (dekorator `@set_ev_cls`, fazy, zdarzenia, skróty): `docs/ryu-sciagawka.md`

## Nie działa / nie zrobione
- **Kolejki priorytetowe (macierz 2×2)** — zaplanowane, nie wykonane: {LLLB, qos100} ×
{`tbf`, `htb` z priorytetem DSCP}; patrz „Następny krok”
- **Miękka rezerwa (R < 100%) nie działa jako ochrona** — limit udziału best-effort jest
bramką wejścia (rozmiar przepływu nieznany, brak przenoszenia po przyjęciu), więc best-effort
zapełnia rezerwę ponad limit (qos90: średnio 17–26%, maks. 40% zamiast 10%). Faktycznie
działa tylko R = 100%. To ograniczenie koncepcji, do opisania w pracy; rozwiązaniem są kolejki
na łączu (gwarancja `rate` klasy wideo w `htb`)
- Poziomy obciążenia tła 50/70/90% **nie są sterowane**: generator ma tylko `arrival_rate`,
`duration_mean`, `rate`; losowe tło daje silne przeciążenie (MLU 102–125%, 8–19 z 24 łączy
> 90% w powtórzeniu). Brak parametru „docelowe obciążenie” w runnerze
- Mesh (`mesh-sdn`, `mesh-frr`) nie był wdrażany ani mierzony; brak sprawdzenia, że OSPF
w `configs/frr/mesh/` zestawia sąsiadów Full
- Pomiary tylko na Clos; n = 5 powtórzeń, bez testów istotności — do pracy potrzeba więcej
powtórzeń (15–20)
- **Ograniczenie LLLB (cecha algorytmu, nie błąd):** przy Packet-In rozmiar przepływu jest
nieznany, rezerwacja jest jednakowa (0,5 Mb/s) dla wideo i kanału sterującego, a decyzja
zapada raz. Przy jednoczesnym starcie LLLB równoważy **liczbę** przepływów, nie pasmo —
dwa strumienie danych mogą trafić na jeden spine (test 3). Świadomie nie poprawiane w B
(rezerwacja tylko dla UDP = dopasowanie pod iperf3; przenoszenie przepływów = inny
algorytm); motywacja dla C (DSCP mówi przy pierwszym pakiecie, że to wideo). W pomiarach:
starty strumieni rozsunięte o ~2 s, jednoczesny start jako osobny scenariusz najgorszego
przypadku
- Przepustowość łącza w kontrolerze wpisana na sztywno (10 Mb/s w trzech miejscach:
`path_load`, `class_load` i log `_monitor`) — musi zgadzać się z `tbf rate` w YAML; przy
łączach o różnych prędkościach do zrobienia parsowanie `rate` w `topo.py` (lub stała
`LINK_BPS`)
- Domyślna wartość `TOPO_FILE` w `controller_ryu.py` wskazuje stary plik
(`/topologies/sdn.clab.yaml`); nie przeszkadza, bo topologie podają `env: TOPO_FILE`
- Pierwsza linia `Links` po nowych przepływach pokazuje same rezerwacje (0,50 Mb/s na
łączach wybranych ścieżek) — `_monitor` wypisuje `link_bps` przed nadejściem odpowiedzi;
tylko kosmetyka logu
- Ruch w obrębie jednego przełącznika przechodzi przez regułę hosta (eth_src=GW_MAC,
TTL−1 — traktowany jak routowany)
- Test TCP ~10 Mb/s — niezaliczony (TSO/GRO, patrz pułapki); wszystkie pomiary to UDP

## Znane pułapki (żeby nie odkrywać ponownie)
- `rate:` pod `links` w Containerlab nie istnieje — limity przez `tc`
- Web UI na porcie 8090 bywa nieaktualny — weryfikować przez `containerlab inspect` /
`docker exec`
- Obraz frr:9.0.1 NIE ładuje /etc/frr/frr.conf (docker-start bez vtysh -b) — config
przez ospfd.conf
- Host ma trasę default od dockera (eth0 mgmt) — bramę dodawać przez `ip route
replace`
- ECMP z hashem L3 (domyślny) nie rozrzuca przepływów między parą podsieci — wymagany
sysctl L4
- iperf3 UDP: domyślny datagram ~8 kB ginie na `tc tbf` (veth w clab ma MTU 9500 → brak
fragmentacji, a tbf odrzuca pakiet większy niż `burst`; widoczne jako dropped w `tc -s qdisc`).
Wszystkie testy UDP z `-l 1400` (zgodne z realnym RTP). W SDN (burst 12800 B) datagramy
~9 KB przechodzą bez strat, ale zawyżają jitter (9 KB na 10 Mb/s = ~7,4 ms nadawania) —
brak `-l 1400` łatwo przeoczyć (zdarzyło się w teście 2 LLLB).
- Metryki UDP (loss/jitter) wyłącznie z raportu serwera (linia `receiver` / JSON serwera) —
sender pokazuje 0% loss nawet przy 100% strat.
- TCP zamiera do ~0 na `tc tbf` z małym burstem: TSO/GRO skleja segmenty w super-pakiety
większe niż burst, odrzucane w całości (cwnd zamrożone, retransmisje w rytmie RTO ~1/s).
- tc liczy 1 kbit = 1024 bity: `burst 100kbit` = 12800 B, `32kbit` = 4096 B
- Ryu 4.34 (ostatnie wydanie, 2020) nie instaluje się na nowym toolchainie: wymaga
`setuptools==58.2.0` + `pbr` + `pip install --no-build-isolation` (inaczej
`get_script_args` AttributeError albo wersja `0.0.0`) oraz `eventlet==0.30.2`,
`dnspython==1.16.0` (inaczej `ALREADY_HANDLED`). Python ≤ 3.9.
- `uv pip install ryu` nie działa (odrzuca metadane pbr) — w venv używać zwykłego `pip`;
`uv venv` bez `--seed` nie instaluje pip
- `ryu.app.simple_switch_13` na Clos = burza broadcastów (pętle leaf-spine-leaf, brak
STP; hosty same wysyłają multicast IPv6 po podniesieniu interfejsu) — nie uruchamiać
- `ryu-manager --verbose` loguje eventy tylko, gdy jakaś aplikacja je konsumuje — sam
`ofp_handler` nie pokaże `EventOFPSwitchFeatures`; połączenia sprawdzać przez
`ovs-vsctl list controller` lub `ofctl_rest` (`/stats/switches`)
- `cmd:` w YAML clab nadpisuje `CMD` z Dockerfile
- `ovs-vsctl other-config:datapath-id=…` bez `set bridge br0` nie działa — poprawnie:
`ovs-vsctl set bridge br0 other-config:datapath-id=…`
- `speed: 10000 Mbps` w `ovs-ofctl show` / PortDesc to prędkość veth, nie limit tbf —
obciążenie łączy liczyć względem stałych 10 Mb/s (uplink) i 100 Mb/s (host), nie `curr_speed`
- Port `LOCAL(br0)` (`OFPP_LOCAL`) w stanie `PORT_DOWN`/`LINK_DOWN` jest normalny —
pomijać w statystykach portów
- `miss_send_len` w `ovs-ofctl show` dotyczy połączenia samego `ovs-ofctl`
(konfiguracja per połączenie), nie Ryu
- OVS pokazuje DSCP w `dump-flows` jako `nw_tos` = DSCP×4 (EF 46 → 184, AF41 34 → 136)
- Bez reguły table-miss przełącznik w `fail-mode secure` odrzuca wszystko i nie wysyła
Packet-In
- containerlab: klucz to `binds:` (nie `bind:`), ścieżka względem katalogu pliku
topologii; zmiana `binds`/`cmd`/`env` wymaga odtworzenia kontenera, zmiana samego `.py` —
tylko `docker restart`. W containerlab 0.79 `deploy --node-filter` na już wdrożonym labie
kończy się błędem („Node filter is not supported when reconciling deployed lab”), więc
odtwarzanie kontrolera = `deploy --reconfigure` (cały lab)
- Po przeniesieniu/zmianie nazwy plików pilnować: `env: TOPO_FILE` w topologii SDN
(rozszerzenie `.yml`!), ścieżki `binds` do `configs/frr/...` w topologiach FRR,
`DEFAULT_TOPOLOGIES` w `common.py` skilla i `topology_files` w scenariuszach — każdy z tych
błędów przerywa albo uruchomienie kontrolera, albo dry-run
- `containerlab` działa bez `sudo` dla użytkownika z grupy `clab_admins`; `sudo -n true` nie
jest dobrym testem (reguła NOPASSWD nie istnieje), a bilet `sudo -v` z jednego terminala nie
działa w drugim (osobne TTY)
- Dwa laby naraz (SDN + FRR) podnoszą średnie CPU maszyny do ok. 50% (maks. 96%) i zniekształcają
jitter; w seriach bez wariantu `ecmp` zatrzymać lab FRR
- Podczas serii SDN lab FRR może stać (kontenery bez ruchu); po restarcie maszyny oba są martwe
- OVS ma `n_buffers:0`, a table-miss używa `OFPCML_NO_BUFFER` → `buffer_id` w FlowMod
jest zbędny (zawsze `OFP_NO_BUFFER`); pierwszy pakiet trzeba odesłać Packet-Out
- Kontroler bez routingu zalewa log: każdy pakiet IPv4 to Packet-In (log na poziomie
info przy każdym pakiecie) — po dodaniu reguł IP problem znika
- `traceroute` przez fabric SDN: `1 *`, potem cel — `dec_ttl` jest tylko w regule hosta
(cały fabric = jeden logiczny router), a OVS przy TTL 0 nie odsyła ICMP Time Exceeded,
tylko Packet-In `OFPR_INVALID_TTL` z uplinku, który kontroler ignoruje. Na pomiary nie
wpływa; w wariancie A traceroute pokaże 3 hopy
- Ryu wczytuje kod tylko przy starcie — po każdej zmianie `.py` restart kontenera;
porównać `stat -c %y controller_ryu.py` z `docker inspect … StartedAt` (UTC!)
- `ipv4_dst` z maską w Ryu: krotka `(adres, maska)`, np.
`(str(net.network_address), str(net.netmask))`
- Test `__init__` kontrolera bez labu (z katalogu `controllers/`, ścieżki względne!):
`TOPO_FILE=../topologies/clos-sdn.clab.yml ../.venv/bin/python -c "import controller_ryu as c; c.Fabric()"`
(z `POLICY=qos RESERVE_PCT=70` przed poleceniem i wywołaniami `c.Fabric().select_path(None, 1, 4, True)`
można sprawdzić politykę bez labu);
bez aktywnego venv nie ma polecenia `python` (tylko systemowy `python3` 3.14)
- git: puste pliki w `.git/objects` po nagłym wyłączeniu VM (2026-10-21) — naprawa:
kopia `.git`, `find .git/objects -type f -empty -delete`, `git fetch origin`, `git fsck --full`.
Powtórka 2026-10-28: 5 pustych obiektów, w tym commit wskazywany przez `main`
(`148cda4`, zapisany tuż przed wyłączeniem) → `fatal: bad object HEAD`. Commit, który nie
był wypchnięty, przepada — pliki w katalogu roboczym zostają, trzeba go zrobić ponownie.
Przed wyłączeniem VM: `sync` (albo `git push` od razu po commicie)
- **Po restarcie maszyny lab jest martwy**: Docker sam podnosi kontenery, ale bez łączy
veth i bez `exec` (brak eth1+, OVS nie działa — `db.sock: Connection refused`, kontroler
bez połączeń). Zawsze `containerlab deploy -t clos-sdn.clab.yml --reconfigure`
(albo `destroy` przed wyłączeniem VM). Zdarzyło się 2026-10-12, 2026-10-26 i 2026-11-01;
objaw: host bez `eth1`, `ovs-vsctl` zgłasza `Connection refused`, runner przerywa przy
sprawdzaniu labu
- Po deployu odczekać, aż przełączniki się połączą — ping w pierwszych sekundach daje
100% strat; sprawdzenie: `docker logs clab-sdn-ryu-controller 2>&1 | grep -c "connected from"` = 7
- Wymagania matcha OF1.3: `tcp_*`/`udp_*` tylko razem z `eth_type=0x0800` i `ip_proto`
(inaczej `OFPBMC_BAD_PREREQ`); OVS pokazuje to jako `udp,…,tp_src=…,tp_dst=…`
- Packet-Out pierwszego pakietu wprost na port, nie `OFPP_TABLE` — reguła 70 może jeszcze
nie być wgrana, pakiet wróciłby do kontrolera; tranzyt ma trasy domyślne jako zapas,
bo reguły na różnych przełącznikach mogą dojść w dowolnej kolejności
- Przepływy w praktyce: `ping` do tego samego hosta = jeden przepływ (ICMP bez portów),
kolejne pingi w ciągu `idle_timeout` idą tą samą ścieżką bez Packet-In; `iperf3` = co
najmniej 2 przepływy (TCP sterujący + UDP/TCP dane) w każdą stronę — kanał sterujący też
zużywa krok round-robin
- **Duplikat Packet-In = dwa wybory ścieżki dla jednego przepływu** (znalezione w teście 1
LLLB, 2026-10-28): ta sama piątka dwa razy w logu, np. `leaf4 -> spine1 -> leaf1 (loads 0% 0% 0%)`
i zaraz potem `leaf4 -> spine2 -> leaf1 (loads 5% 0% 0%)`. Przyczyna: wyścig — kolejny pakiet
przepływu dociera do leafa brzegowego, zanim kontroler wgra regułę (reguły instalowane od
końca ścieżki, brzegowy leaf ostatni), więc trafia jako drugi Packet-In. Drugi wybór widzi
rezerwację pierwszego, wybiera inną ścieżkę i FlowMod (ten sam match i priorytet) nadpisuje
regułę → przepływ przeskakuje w trakcie (ryzyko reorderingu TCP / jittera wideo) + podwójna,
fantomowa rezerwacja psuje kolejne decyzje (w RR — przeskok licznika). Poprawka: słownik
`self.active` (piątka → ścieżka, czas wyboru); Packet-In tej samej piątki w ciągu 2 s
dostaje zapamiętaną ścieżkę bez ponownego `select_path`, wpisy starsze niż 2 s czyszczone
w `_monitor` (okno krótsze niż `idle_timeout`, żeby po wygaśnięciu reguł przepływ dostał
świeży wybór). Weryfikacja: każda piątka dokładnie raz w logu `Flow`
- Ten sam przepływ ponownie w logu po > 10 s ciszy (np. kanał sterujący iperf3 na końcu
testu) — to nie duplikat: reguła wygasła (`idle_timeout=10`), następny pakiet dostaje
świeży wybór. Bez ryzyka reorderingu, bo w tym czasie nic nie płynęło
- Zmiana `env:` kontrolera (np. `POLICY`) w YAML wymaga odtworzenia kontenera (destroy/deploy
`--node-filter ryu-controller`) — `docker restart` zostawia stare zmienne; sprawdzenie:
`docker exec clab-sdn-ryu-controller env | grep POLICY` i linia `Path selection policy` w logu
- Wywołanie loggera z większą liczbą argumentów niż `%s` w formacie → `TypeError: not all
arguments converted` (traceback w logu, linia nie zostaje wypisana, ruch działa dalej)
- Przepustowość łączy jest pewna tylko z `tc`: `docker exec clab-sdn-leaf1 tc qdisc show dev eth1`
→ `rate 10Mbit burst 12800b`; empirycznie iperf3 `-b 15M` → receiver ~9,5 Mb/s, `Links` ~100%
- Statystyki przepływów w Ryu: `dict(stat.match.items())` daje pola dopasowania, a port
wyjściowy to `stat.instructions[0].actions[0].port`; `OFPFlowStatsRequest(datapath)` bez
argumentów pyta o wszystkie reguły (prio 70 = przepływy kontrolera, 60 = hosty, 50 = trasy)
- Float: `1 - R / 100` daje `0.30000000000000004` dla R = 70 i zafałszowuje porównanie
z `0.3`; używać `(100 - R) / 100`
- Przepływy ≤ warmup (losowe, 5 s) mają statystyki z całości (z fazą startu iperf3): zawyżone
„dostarczone/zadane” > 100%; w agregacie tła pomijane. Ok. 110 z 145 zastrzeżeń automatycznych
w seriach losowych to właśnie te przepływy
- Linia `Flow` w logu kontrolera ma od kroku 9 postać `(video|be, loads …)`; parser w `analyze.py`
akceptuje obie (`\((?:\w+, )?loads …\)`) — inaczej tabela ścieżek w raporcie jest pusta
- Ping z `-Q 184` (DSCP 46) jest w C klasyfikowany jako wideo: w wariancie z rezerwą RTT wideo
jest bliskie 0,03 ms, w pozostałych 58–118 ms (ICMP trafia w pełną kolejkę `tbf`, `latency 50ms`)

## Ustalenia ze spotkania z promotorem (2026-10-21)
- Sieć może być **statyczna** — topologia i rozmieszczenie hostów nie zmieniają się
w trakcie eksperymentu
- Kontroler **może znać z góry całą sieć** (gdzie jest każdy host: IP, MAC, leaf, port) —
uczenie z ruchu i aktywne odpytywanie ARP nie są wymagane
- Warianty A (OSPF+ECMP), B (SDN+LLLB), C (SDN+QoS-Aware) — zaakceptowane bez zmian

## Otwarte (nieomówione na spotkaniu)
- Fix TSO/GRO (`ethtool -K <ethX> tso off gso off gro off` na wszystkich interfejsach
labowych; do utrwalenia w exec obu topologii, żeby A/B/C miały identyczne warunki).
Obowiązkowy, jeśli tło będzie TCP; przy tle UDP nieblokujący.
- Ostateczne prędkości łączy / parametry `tc tbf` (rate, burst): obecnie 10 Mb/s fabric
(`burst 100kbit`), 100 Mb/s hosty (`burst 320kbit`), wyrównane między A a SDN; poziomy
obciążenia 50/70/90% — patrz „Następny krok”.
- Decyzje projektowe algorytmu C (przeanalizowane zalety/wady, bez rozstrzygnięć):
  1. Klasyfikacja: **rozstrzygnięte** — samo DSCP 46 (EF), bez granicy zaufania na portach
  hostów (zaufane hosty w laboratorium)
  2. Kolejki priorytetowe: **rozstrzygnięte** — macierz 2×2 {LLLB, qos100} × {bez kolejek
  (`tbf`), z kolejkami (`htb` + filtr DSCP)}; kolejki robione w `tc` na portach fabric, nie
  w OpenFlow (kontroler bez zmian); `rate` klasy wideo w `htb` może odzwierciedlać R
  3. Rezerwa ścieżki wideo: **zaimplementowana** jako miękka z limitem R i zaworem dla
  wideo; pomiar pokazał, że działa tylko R = 100% (patrz „Nie działa”)
  4. Przenoszenie istniejących przepływów (rerouting): **rozstrzygnięte** — decyzja tylko
  przy starcie przepływu (spójne z B)
- Awarie łączy/węzłów — **poza zakresem pracy** (decyzja autora, zapisana w AGENTS.md);
PortStatus / fast-failover nie są implementowane

## Następny krok
- Commit i `git push` (kontroler z wariantem C, topologie `clos-*`/`mesh-*`, `configs/frr/clos`
i `mesh`, wyniki bez `raw/`, dokumentacja); przed wyłączeniem VM zawsze `git push`
- **Macierz 2×2 z kolejkami:** skrypt `shape.sh <iface> <rate> <tbf|prio>` (w trybie `prio`:
`htb` z klasami wideo/reszta, filtr `u32 match ip dsfield 0xb8 0xfc`, kolejki `bfifo limit
62500` ≈ 50 ms przy 10 Mb/s), zmienna `QDISC` w topologiach (env kontrolera `${QDISC:=tbf}`
+ wywołanie skryptu w `exec` portów fabric), scenariusz z wariantami lllb / qos100 /
lllb+kolejki / qos100+kolejki (+ `ecmp` jako odniesienie); najpierw sprawdzić w labie, że
obrazy mają `tc htb`
- Sterowane poziomy obciążenia tła 50/70/90% (parametr docelowego obciążenia w generatorze
albo dobór `arrival_rate`); jedna seria na poziom
- Pomiary na mesh: deploy `mesh-sdn` / `mesh-frr`, sprawdzenie OSPF Full, scenariusz
`topology: mesh` (domyślne pliki w `common.py`)
- Więcej powtórzeń (15–20) dla końcowych wyników i opis ograniczeń (n, przeciążenie, brak testu
istotności)
- Drobne porządki w kodzie: sprawdzenie `pkt_arp is None`, literówki w komentarzach
(„zapytaniam”, „obciązenia”, „miedzy”, „ściezki”), docstring `_install_host_rule`
(„w danym leafie”), spacje na końcu linii; stała `LINK_BPS` zamiast trzech `10_000_000`;
domyślny `TOPO_FILE` w kontrolerze
- Przypiąć `kathara/sdn` do digestu
(`sha256:19cb5b383367e1d204e76f7e6e65753fbc947647747879f24883558a5c3fd8c5`)
- Fix TSO/GRO, jeśli tło ma obejmować TCP (obecnie wszystkie pomiary UDP)
