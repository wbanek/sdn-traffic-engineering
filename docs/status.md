# Status projektu (ostatnia aktualizacja: 2026-11-09)

## Pliki topologii (od 2026-11-01)
| Plik | Co | Lab (`name:`) |
|---|---|---|
| `topologies/clos-frr.clab.yml` | wariant A, Clos 3 spine × 4 leaf, FRR (OSPF + ECMP) | `clos-frr` |
| `topologies/clos-sdn.clab.yml` | warianty B/C, Clos, OVS + Ryu (mgmt kontrolera 172.20.20.100) | `clos-sdn` |
| `topologies/mesh-frr.clab.yml` | wariant A, mesh (4 edge + 3 core), FRR | `mesh-frr` |
| `topologies/mesh-sdn.clab.yml` | warianty B/C, mesh, OVS + Ryu (mgmt kontrolera 172.20.20.101) | `mesh-sdn` |

Konfiguracje OSPF: `configs/frr/clos/{leafs,spines}/`, `configs/frr/mesh/{edge1-4,core1-3}.conf`.
Wszystkie cztery topologie mają po 7 przełączników/routerów, 12 hostów (h1..h4 × video/bg1/bg2,
10.1.L.10/11/12) i 12 łączy fabric 10 Mb/s (`burst 100kbit`) oraz 12 łączy hostów 100 Mb/s
(`burst 320kbit`). Zbiór łączy i numery `ethN` są identyczne w parach SDN/FRR (sprawdzone
skryptem). Mesh: edge1–edge2, edge3–edge4, edge↔core (po 2), core1–core3, core2–core3;
przełączniki brzegowe dpid 1–4, core 0x11–0x13. **Mesh ma wyniki oficjalne** (2026-11-05, patrz „Wyniki
pomiarów”): `mesh-frr` zweryfikowany (OSPF: krawędzie 3, rdzenie 4 sąsiadów Full po ok. 1,5 min,
pingi 12/12, hash L4) i zmierzony razem z wariantami SDN; wcześniejsze serie na mesh z meterami
(wadliwy kontroler) są unieważnione. Ścieżki wg `topo.py`, np. edge1→edge4: 1 ścieżka 2-hopowa
przez core2 + trzy 3-hopowe; OSPF z równymi kosztami daje tam 1 ścieżkę (koszt 30).
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
z nazwą pliku, razem z rozszerzeniem `.yml`); zmiana kodu → `docker restart clab-clos-sdn-ryu-controller`;
`env:` kontrolera: `POLICY: ${POLICY:=lllb}`, `RESERVE_PCT: ${RESERVE_PCT:=100}`,
`LAYERS: ${LAYERS:=1}`, `MARGIN: ${MARGIN:=0.1}`, `HEADROOM_MBPS: ${HEADROOM_MBPS:=0}`,
`OPENQOS_BE: ${OPENQOS_BE:=hash}`, `DMAX_SLACK: ${DMAX_SLACK:=1}`, `CONG_WEIGHT: ${CONG_WEIGHT:=1}`
(Containerlab podstawia zmienne powłoki przy deployu; trzy ostatnie dotyczą kroku 11)
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
- **Krok 10: drzewo wideo, metery OpenFlow i warstwy L1–L3 wariantu C** — 2026-11-01/02:
  - rezerwa = **drzewo wideo** (`topo.video_tree()`, liczone raz w `__init__`): drzewo BFS
  zakorzenione w węźle tranzytowym (Clos: spine, mesh: core), przycięte do przełączników
  brzegowych; korzeń wybierany wg kryterium (max min/suma ścieżek best-effort omijających
  rezerwę, min rozciągnięcie ścieżek wideo, min dpid). `topo.reserved` = skierowane pary
  (dpid, port) łączy drzewa, `topo.video_path(src, dst)` = ścieżka wideo po drzewie
  (zastępuje `paths[0]` z kroku 9). Pojemność łączy z `tbf rate` w pliku clab (`topo.capacity`,
  `cap(hop)`) — koniec ze stałą 10 Mb/s. Mesh: reguły do kontrolera (prio 55) także na
  przełączniku brzegowym tranzytu. Zmiana kształtu drzewa (korzeń tranzytowy) nie zmieniła
  strat tła — wąskie gardło przeniosło się tylko w inne miejsce
  - **L1** (`LAYERS=1`, domyślne): meter OpenFlow typu drop na każdym łączu rezerwy
  (`meter_id` = numer portu, `OFPMeterMod ADD` przy połączeniu przełącznika, `burst_size=50`),
  stawka `(100 − R)%` pojemności; reguły best-effort (prio 70) przechodzące przez łącze rezerwy
  mają `OFPInstructionMeter`, wideo bez metera; bramka wejścia i rezerwacja +0,5 Mb/s jak
  w kroku 9
  - **L2** (`LAYERS=2`): bramka `fits(path)`: (zmierzone obciążenie best-effort + rezerwacje
  oczekujące) + szacunek nowego przepływu ≤ limit na każdym łączu rezerwy. `pending`
  (hop → [(klasa, b/s, wygasa)], TTL 2,5 s — przepływ pojawia się w `FlowStats` po dwóch
  próbkach) zastępuje +0,5 Mb/s; szacunek best-effort `est_be` = EWMA 0,98/0,02 przepływności
  best-effort z pierwszego przełącznika ścieżki (start 2 Mb/s), wideo 3 Mb/s (`VIDEO_EST_BPS`),
  ICMP 0; `path_load` i `class_load` uwzględniają `pending`
  - **L3** (`LAYERS=3`): limit best-effort na łączu rezerwy dynamiczny:
  `max(C − wideo·(1 + MARGIN) − H, 0,3 Mb/s)` (wideo = zmierzone + oczekujące);
  `_update_meters` co 1 s zmienia stawkę metera (`OFPMC_MODIFY`), gdy różnica ≥ 250 kb/s.
  `MARGIN` (env, domyślnie 0,1) i `HEADROOM_MBPS` (env, H) = zapas na nowe wideo w czasie
  opóźnienia reakcji (do ok. 2 s); `RESERVE_PCT` nie ma wpływu. Log:
  `Meter <sw> port N: BE limit X kb/s`
  - spill wideo sprawdza tylko obciążenie przez wideo: `class_load(vpath, "video") < SPILL`
  - **błędy znalezione i naprawione (2026-11-02):**
    1. `flow_stats_handler` czytał `stat.instructions[0].actions[0]`, a reguła z meterem ma
    instrukcję metera na pierwszym miejscu → `AttributeError` w każdej odpowiedzi FlowStats z
    przełączników z regułami best-effort na rezerwie; `class_bps` nie był odświeżany, a liczniki
    rezerwacji nie malały. Serie `meter-sweep-clos`/`meter-sweep-mesh` (m90/m80/m70)
    z tym błędem (1,0–1,6 tys. wyjątków na serię) są **nieważne**
    2. spill wideo liczył `path_load` (całe łącze, razem z `pending` best-effort), więc drugi
    strumień wideo uciekał z rezerwy (L2: utrata wideo 2–18% w 3–4 z 5 powtórzeń)
    3. pingi wideo (ICMP, DSCP 46) liczyły się w `pending` jak 3 Mb/s i wywoływały spill —
    teraz szacunek 0
- **Krok 11: wariant D — baseline OpenQoS** (`POLICY=openqos`) — 2026-11-08, kod w kontrolerze,
  **zmierzony oficjalnie 2026-11-09 (wyniki na końcu tego kroku)**. Reimplementacja wg artykułu Egilmez, Dane, Bagci, Tekalp, „OpenQoS: An
  OpenFlow Controller Design for Multimedia Delivery with End-to-End QoS over SDN”, APSIPA ASC 2012
  (plik `OpenQoS.pdf` w katalogu głównym, poza gitem). Cel: punkt odniesienia z literatury dla wariantu C
  w tych samych warunkach (te same harmonogramy, porównania sparowane). OpenQoS = **reaktywny routing
  QoS bez rezerwacji i bez kolejek** („we use neither resource reservation nor priority queuing”, s. 2),
  czyli przeciwieństwo C; nowsze prace (ARVS 2015, VQoSRR 2022) też porównują się z OpenQoS
  - **Wierne artykułowi:** wideo (DSCP 46) dostaje trasę z CSP (wzór 3): min `Σ c_ij` przy liczbie hopów
  ≤ `Dmax`; koszt łącza `c_ij = g_ij + 1` (wzór 4, `d_ij = 1` = hop, bo OpenFlow nie mierzy opóźnień);
  miara przeciążenia `g_ij = (T − 0,7·B) / T` dla `T > 0,7·B`, inaczej 0 (wzór 5; `T` = `link_bps`,
  `B` = `cap()`); stan łączy co 1 s z PortStats (jak `_monitor`); łącze przeciążone od **70%**;
  **przenoszenie wideo = usunięcie reguł QoS** (`OFPFC_DELETE` prio 70 na wszystkich przełącznikach,
  `_flush_video_flows`), następny pakiet → Packet-In → świeży wybór; wyzwalacze (`_congestion_events`):
  (1) łącze luźne staje się przeciążone, (2) łącze przeciążone jest luźne przez **3 kolejne okresy**;
  tło na najkrótszej ścieżce; brak rezerwacji tymczasowej i `pending` (artykuł nic takiego nie ma)
  - **Odstępstwa (do opisania w pracy):** Ryu + OF 1.3 zamiast Floodlight + OF 1.0; klasyfikacja po
  DSCP zamiast portu docelowego (artykuł dopuszcza pole TOS, s. 3); CSP rozwiązany **dokładnie** przez
  przegląd ścieżek z `topo.paths` zamiast heurystyki LARAC (≤ 4 kandydatów; na korzyść baseline'u);
  `Dmax` = najkrótsza + `DMAX_SLACK` (1) hop; tło: `OPENQOS_BE=hash` (domyślnie) = jedna z najkrótszych
  ścieżek po `crc32` piątki, odpowiednik ECMP z wariantu A; `OPENQOS_BE=single` = dosłownie `paths[0]`
  (Floodlight 2012 liczył jedną najkrótszą ścieżkę; w Clos całe tło na spine1)
  - **Cecha wzoru (5), znaleziona w teście offline:** `g < 0,3` (maksimum przy `T = B`), a dodatkowy hop
  kosztuje 1, więc przy wadze 1 **wideo nigdy nie zejdzie na dłuższą ścieżkę**. W Clos (ścieżki równej
  długości) bez znaczenia: przeciążenie spine1 ≥ 70% → spine2/3. W **mesh** (1 ścieżka 2-hopowa + 3-hopowe)
  OpenQoS dosłownie = statyczna najkrótsza ścieżka dla wideo (flush przenosi na tę samą trasę). Dlatego
  `CONG_WEIGHT` (env, domyślnie 1 = dosłownie): przy 5 ścieżka 3-hopowa wygrywa od ok. 93% obciążenia
  (test: 9,5 Mb/s na core2 → `edge1->edge2->core3->edge4`, 8 Mb/s → zostaje). Uwaga: w testbedzie autorów
  (trójkąt, 1 vs 2 hopy) wzór też nie przenosi, choć artykuł raportuje przenoszenie — opis w artykule
  jest prawdopodobnie niepełny; w pracy podawać obie wersje (w = 1 i w = 5)
  - Konsekwencja wzoru w Clos: poniżej 70% wszystkie ścieżki mają koszt 2, `min` bierze pierwszą → oba
  strumienie wideo idą przez spine1 (60%, „nieprzeciążone”) do czasu, aż tło dociśnie łącze > 70%
  - Pozostałe zmiany w kodzie: `flow_last` + `FLOW_CLASS_TTL` (15 s) czyści `flow_class` z przepływów
  nieobecnych w FlowStats (żeby flush nie wysyłał DELETE dla dawno wygasłych); `_hop_name` do logu.
  Log: `OpenQoS reroute: leaf1:1->spine1 congested 78% -> 2 QoS flows flushed` (liczba flushy i powtórnych
  linii `Flow (…) (video, …)` per powtórzenie = liczba przeniesień; artykuł: średni czas odzyskania
  jakości 0,76 s w 20 powtórzeniach UDP — punkt odniesienia)
  - Test offline (2026-11-08, `select_path`/`qos_route` bez labu, Clos i mesh): pusta sieć → `paths[0]`;
  80% na spine1 → spine2; 65% → spine1; hash tła rozrzuca 8 przepływów na 3 spine'y; maszyna stanów po
  2 tikach przeciążenia i 4 luzu wraca do `congested=False`; YAML topologii poprawny. **Nie testowane
  w labie** (flush → Packet-In → nowa reguła, ruch przez trasy domyślne prio 50 na tranzycie w przerwie)
  - Odniesienie w artykule: testbed 3 × Pronto 3290 (trójkąt), 1 wideo 1,8 Mb/s RTP/UDP, cross-traffic 10 s,
  metryka PSNR; call admission i traffic policing — future work (s. 5), niezaimplementowane
  - **Test w labie (2026-11-09, mesh, 1 powt., `scenarios/openqos-test.yml`,
  `results/openqos-test/20261109_023841`, harmonogram = powt. 1 serii oficjalnych):** 0 `Traceback`;
  25 (w=1) / 29 (w=5) zmian stanu przeciążenia na 60 s, każda = flush wszystkich przepływów wideo →
  19–25 decyzji na strumień (raport zgłasza to w sekcji 7 jako „wygasła reguła albo duplikat” — to
  przenoszenie, nie błąd); trasy po flushu zgodne z `dump-flows`. **w = 1: wideo zawsze wraca na tę
  samą 2-hopową trasę** (vid1 22× `edge1->core2->edge4` przy 102% na `edge1→core2`): vid1 15,44%,
  vid2 3,78% utraty — **praktycznie równe `ecmp` z tego samego powtórzenia (15,22% / 3,80%)**, bo w mesh
  OSPF też ma jedną najkrótszą ścieżkę. **w = 5: przenoszenie działa** (vid1 15/7/3 decyzji na 3 trasach),
  vid1 2,36%, ale vid2 6,98% (3-hopowe trasy też przeciążone); tło 6,63% vs 9,34%. Dla porównania
  (powt. 1): lllb 5,25/1,89%, qos100 0,54/1,59%, L3H1.5 0/0%
  - **Test w labie, Clos (2026-11-09, 1 powt., `scenarios/openqos-test-clos.yml`,
  `results/openqos-test-clos/20261109_024508`, w = 1, lab `clos-sdn` wdrożony obok mesh):** 0 `Traceback`;
  35 zmian stanu (13 „clear”), vid1 26 decyzji (18× spine1, 3× spine2, 5× spine3), vid2 22 (16/3/3) —
  **przenoszenie między spine'ami działa**, spine1 dominuje (poniżej 70% koszt wszystkich ścieżek = 2).
  Wideo: vid1 2,92%, vid2 0,63% (ecmp 6,65/12,75, lllb 10,83/0, qos100 0/0 w tym samym powt.);
  **jitter 0,96/0,99 ms** — 2–20× więcej niż inne warianty (każde przeniesienie = przerwa + zmiana
  kolejki); tło 11,03% (≈ qos100). CPU VM maks. 60% przy dwóch labach — przed serią oficjalną zatrzymać
  nieużywany lab
  - **WYNIKI OFICJALNE wariantu D (2026-11-09, 20 powtórzeń, seed 42, `arrival_rate` 1,0)**, harmonogramy
  identyczne z `clos-frr`/`mesh-frr` (20/20), skrót kodu `81a760eb…` bez zmian, 0 `Traceback`. Katalogi:
  `results/official/openqos/clos-sdn/20261109_025456` (openqos, openqos_single + kotwice qos100_ref,
  L3H1.5_ref) i `results/official/openqos/mesh-sdn/20261109_045801` (+ openqos_w5). Warianty: `openqos`
  (w = 1, tło hash 5-tki), `openqos_w5` (`CONG_WEIGHT=5`, tylko mesh — w Clos waga nie zmienia wyboru),
  `openqos_single` (`OPENQOS_BE=single`, tło dosłownie na `paths[0]`). **Kotwice potwierdzają, że zmiany
  kodu z kroku 11 nie zmieniły B/C** (różnice sparowane względem wyników oficjalnych sprzed zmian, ± połowa
  CI95): Clos `qos100_ref − qos100` wideo +0,03 ± 0,06, tło −0,70 ± 0,84; `L3H1.5_ref − L3H1.5` wideo
  −0,01 ± 0,02, tło −0,03 ± 1,16; mesh `qos100_ref − qos100` −0,05 ± 0,11 / −0,05 ± 0,84,
  `L3H1.5_ref − L3H1.5` 0,00 ± 0,01 / +1,06 ± 1,27 — wszystkie przedziały zawierają 0. Zatem
  `load-0.7/mesh-sdn` (część przebiegów na zmienionym kodzie, patrz „Seria niższego obciążenia”) jest
  wiarygodny. Średnia ± sd (w nawiasie powt. z utratą wideo > 1%):

    | wariant | Clos: wideo | Clos: tło | Clos jitter / RTT p95 med. | mesh: wideo | mesh: tło | mesh jitter / RTT p95 med. |
    |---|---|---|---|---|---|---|
    | ecmp (A) | 13,8 ± 9,6% (18) | 12,1% | 0,41 / 59 ms | 10,9 ± 8,0% (19) | 10,4% | 0,27 / 67 ms |
    | lllb (B) | 4,9 ± 4,6% (16) | 4,9% | 0,24 / 70 ms | 10,2 ± 6,2% (18) | 8,5% | 0,36 / 118 ms |
    | qos100 (C) | 0,00% (0) | 12,9% | 0,08 / 0,05 ms | 0,05 ± 0,24% (1) | 26,0% | 0,08 / 0,05 ms |
    | L3H1.5 (C) | 0,01% (0) | 8,7% | 0,07 / 0,05 ms | 0,01% (0) | 12,5% | 0,06 / 0,05 ms |
    | **openqos (D)** | 4,5 ± 3,3% (18) | 11,3 ± 4,9% | 0,33 / 59 ms | 10,6 ± 7,6% (18) | 10,2 ± 5,5% | 0,30 / 60 ms |
    | openqos_w5 | — | — | — | 5,7 ± 4,7% (16) | 10,0 ± 5,4% | **1,34** / 60 ms |
    | openqos_single | 0,51 ± 0,61% (5) | **39,1 ± 7,5%** | 0,11 / 15 ms | 8,6 ± 7,2% (17) | 10,6 ± 5,4% | 0,31 / 59 ms |

  - **wnioski D** (różnice sparowane ± połowa CI95, pkt proc.): (1) D nie chroni wideo jak C: openqos −
    L3H1.5 wideo +4,46 ± 1,54 (Clos) i +10,64 ± 3,56 (mesh); (2) Clos: openqos − ecmp wideo −9,3 ± 3,8
    (tło −0,8 ± 2,4, bez różnicy), openqos − lllb wideo −0,4 ± 2,0 (bez różnicy), tło +6,4 ± 1,5 —
    zysk wideo na poziomie LLLB kosztem tła; (3) **mesh: openqos ≈ ecmp** (wideo −0,25 ± 0,97, tło −0,22 ±
    0,96) — przy w = 1 wzór (5) nie przenosi wideo na dłuższą ścieżkę, więc to statyczna najkrótsza
    ścieżka (cecha algorytmu); (4) `openqos_w5` (rozszerzenie, nie z artykułu) poprawia wideo na mesh
    (−4,97 ± 3,40 względem openqos, tło bez zmian) za cenę jittera 1,34 ms (+1,04 ± 0,91); nadal
    +5,66 ± 2,21 wideo względem L3H1.5; (5) `openqos_single` w Clos: całe tło na spine1, więc wideo
    ucieka na spine2/3 (0,51%, jitter 0,11), ale tło traci 39% (+27,8 ± 2,7 względem openqos) — wariant
    skrajny, dosłowny wg artykułu; na mesh bez istotnej różnicy względem openqos (wideo −2,0 ± 1,1);
    (6) mesh: openqos − L3H1.5 w tle −2,4 ± 2,1 — D traci o ok. 2 pkt proc. mniej tła, ale bez ochrony
    wideo
  - Liczba przeniesień wideo (zdarzeń `OpenQoS reroute`) na powtórzenie: Clos openqos 34 (52 decyzje trasy
    wideo UDP), openqos_single 20; mesh openqos 23, openqos_w5 28, openqos_single 23; każde zdarzenie
    kasuje reguły wszystkich przepływów wideo (przerwa + zmiana kolejek), stąd wyższy jitter. CSV:
    `results/official/wykresy-<topologia>/dane_<topologia>_openqos_przeniesienia.csv` (z lokalnych logów
    `raw/`)
  - Ograniczenia: reimplementacja (Ryu + OF 1.3, DSCP zamiast portu, CSP dokładnie zamiast LARAC,
    `Dmax` = najkrótsza + 1), `openqos_w5` i `openqos_single` to badanie czułości na wybory niedookreślone
    w artykule; D niezmierzony przy `arrival_rate` 0,4 / 0,7
  - **WYNIKI OFICJALNE, niższe obciążenie tła (2026-11-05/09, `arrival_rate` 0,4 i 0,7; ecmp, lllb, qos100, L3H1.5;
  Clos i mesh; 20 powtórzeń, seed 42)**: katalogi `results/official/load-0.4/` i `load-0.7/`
  (`clos-frr`, `clos-sdn`, `mesh-frr`, `mesh-sdn`), harmonogramy identyczne we wszystkich czterech katalogach danego
  poziomu (średnio 24 / 40 przepływów na powtórzenie wobec 54 przy 1,0), 0 `Traceback`. Seria została
  przerwana restartem maszyny (06.11 ok. 01:34, `mesh-frr` 0,7 w powt. 15) i dokończona 08–09.11 (nowe katalogi
  `mesh-frr`/`mesh-sdn`; niekompletny katalog usunięty). **Adnotacja:** `load-0.7/mesh-sdn` — w trakcie serii
  zmienił się kod kontrolera (krok 11; qos100/L3H1.5 od powt. 11, lllb od 12 na nowym kodzie; `PROVENANCE.txt`:
  „UWAGA”); kotwice z serii OpenQoS (różnice 0 w obu topologiach) wskazują, że B/C się nie zmieniły. Średnie
  obciążenie łączy fabric (ecmp): Clos 17,5 / 27,7 / 35,9%, mesh 14,7 / 23,0 / 29,6% (dla 0,4 / 0,7 / 1,0).
  Średnia ± sd; utrata wideo (powt. z utratą > 1%) / utrata tła:

    | topologia, wariant | 0,4: wideo | 0,4: tło | 0,7: wideo | 0,7: tło | 1,0: wideo | 1,0: tło |
    |---|---|---|---|---|---|---|
    | Clos ecmp | 2,2 ± 2,9% (12) | 3,5% | 8,4 ± 9,5% (18) | 7,5% | 13,8 ± 9,6% (18) | 12,1% |
    | Clos lllb | 0,19 ± 0,75% (1) | 0,4% | 1,3 ± 1,9% (7) | 1,5% | 4,9 ± 4,6% (16) | 4,9% |
    | Clos qos100 | 0,00% (0) | 2,4% | 0,00% (0) | 6,6% | 0,00% (0) | 12,9% |
    | Clos L3H1.5 | 0,05 ± 0,16% (0) | 2,2% | 0,03 ± 0,11% (0) | 4,0% | 0,01 ± 0,04% (0) | 8,7% |
    | mesh ecmp | 1,5 ± 4,0% (5) | 2,5% | 6,1 ± 6,2% (16) | 6,8% | 10,9 ± 8,0% (19) | 10,4% |
    | mesh lllb | 0,55 ± 1,1% (3) | 1,0% | 3,0 ± 3,3% (13) | 3,7% | 10,2 ± 6,2% (18) | 8,5% |
    | mesh qos100 | 0,00% (0) | 6,9% | 0,01% (0) | 16,6% | 0,05 ± 0,24% (1) | 26,0% |
    | mesh L3H1.5 | 0,41 ± 1,65% (1) | 4,5% | 0,00% (0) | 7,3% | 0,01% (0) | 12,5% |

  - **wnioski, obciążenie** (różnice sparowane ± połowa CI95, pkt proc.): (1) straty wideo w ecmp i lllb rosną
    z obciążeniem (Clos ecmp 2,2 → 8,4 → 13,8%, lllb 0,19 → 1,3 → 4,9%), a w qos100/L3H1.5 pozostają ≈ 0 na
    wszystkich poziomach; (2) **przy niskim obciążeniu rezerwa się nie opłaca**: Clos 0,4 lllb − L3H1.5 wideo
    +0,14 ± 0,36 (bez różnicy), tło −1,8 ± 1,3 (lllb lepszy); mesh 0,4 lllb − L3H1.5 wideo +0,15 ± 0,97 (bez
    różnicy), tło −3,5 ± 1,8; zysk wideo z C względem lllb staje się istotny od 0,7 (Clos +1,26 ± 0,88, mesh
    +3,02 ± 1,56) i duży przy 1,0 (+4,9 / +10,2); (3) koszt rezerwy dla tła rośnie z obciążeniem: qos100
    Clos 2,4 → 6,6 → 12,9%, mesh 6,9 → 16,6 → 26,0%; (4) przewaga L3H1.5 nad qos100 w tle pojawia się dopiero
    przy większym obciążeniu: Clos 0,4 −0,2 ± 1,2 (bez różnicy), 0,7 −2,6 ± 1,7, 1,0 −4,2 ± 1,6; mesh 0,4
    −2,4 ± 3,2 (bez różnicy), 0,7 −9,3 ± 2,4, 1,0 −13,4 ± 2,6; (5) ecmp − lllb: Clos lllb lepszy na każdym
    poziomie (wideo +2,0 ± 1,1 / +7,1 ± 4,2 / +8,9 ± 4,8), mesh różnice w wideo mieszczą się w szumie
    (+1,0 ± 1,6 / +3,0 ± 3,0 / +0,7 ± 3,3); (6) L3H1.5 − ecmp w tle: Clos −1,4 ± 1,8 / −3,5 ± 2,3 / −3,4 ± 2,1
    (L3 lepszy od ecmp także w tle przy ≥ 0,7), mesh +2,0 ± 2,0 / +0,5 ± 1,5 / +2,1 ± 2,0 (L3 nie poprawia
    tła względem ecmp, poprawia wideo: −1,1 ± 2,0 / −6,1 ± 2,9 / −10,9 ± 3,7)
  - **Incydent: mesh 0,4, L3H1.5, powt. 8** (wideo 7,4%: vid1 5,9%, vid2 8,8%; jedyna taka powtórzenie, reszta ≈ 0):
    oba strumienie na standardowej trasie wideo (vid2 `edge2→core3→core2→edge4`), straty na wspólnym łączu
    `core2→edge4`; w logu przy starcie wideo ścieżki mają 61–72% obciążenia — hipoteza: best-effort już obecny
    na łączu rezerwy w chwili startu wideo, a meter L3 reaguje z opóźnieniem do ok. 2 s (znane ograniczenie
    z kroku 10), analogicznie do 1 powt. qos100 przy 1,0 na mesh (1,1%); niewyjaśnione do końca
  - Wykresy i dane: `results/official/wykresy-obciazenie/` (`obciazenie_utrata_wideo.png`,
    `obciazenie_utrata_tla.png`, `dane_obciazenie.csv`); generuje je `analysis/summary_charts.py`
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
  - `analysis/summary_charts.py` (w repozytorium): wykresy zbiorcze (każdy osobnym PNG) i CSV z
  danymi w `results/official/wykresy-clos/`, `wykresy-mesh/` i `wykresy-porownanie-topologii/`
  (Clos vs mesh: utrata wideo i tła) z wyników oficjalnych (`.venv/bin/python
  analysis/summary_charts.py [katalog_bazowy]`); metody: słupkowe, krzywe R i H, kompromis wideo/tło,
  przebiegi czasowe. Wzorzec `results/official/clos-sdn/*` obejmuje wszystkie części serii
  (katalogi bez `flows.csv` są pomijane; wariant w dwóch katalogach = błąd); porównanie „z meterem
  / bez” wyłączone (`NO_METER = None`: dane bez metera to 5 powtórzeń sprzed poprawek)
  - `analysis/export_excel.py` (w repozytorium): `.venv/bin/python analysis/export_excel.py <katalog>
  [<katalog> …] -o plik.xlsx` — jeden plik .xlsx z arkuszami: opis, podsumowanie (n, średnia, sd,
  CI95 z rozkładu t, mediana, min, maks), sparowane (różnice wariant − ecmp/lllb/qos100/L3H1.5 w
  parach; ta sama nazwa wariantu w dwóch katalogach, np. kotwica `qos100_ref`, dostaje przyrostek `_2`), powtorzenia, strumienie, przebiegi_usrednione, timeseries_surowe, lacza, harmonogram;
  liczby jako liczby (polski Excel). Wymaga `openpyxl` w `.venv`
  - **Wyniki oficjalne** w `results/official/<topologia>/<znacznik czasu>/` (`clos-frr`,
  `clos-sdn`, `mesh-frr`, `mesh-sdn`; seria niższego obciążenia w `results/official/load-<arrival_rate>/<topologia>/`): 20 powtórzeń, seed 42, każdy katalog ma
  `PROVENANCE.txt` (czas, hash kodu `controllers/*.py` + topologii, wersje i digesty obrazów, CPU),
  `report.md`, CSV, wykresy i `dane_excel.xlsx` (surowe `raw/` poza gitem: `results/**/raw/` w
  `.gitignore`). Zbiorcze pliki do Excela: `results/official/dane_clos_wszystko.xlsx`, `dane_mesh_wszystko.xlsx` (z wariantem D i kotwicami; polecenie:
  `export_excel.py results/official/<t>-frr/* results/official/<t>-sdn/* results/official/openqos/<t>-sdn/* -o …`)
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
  - `mesh-lllb-vs-qos` 20261101_223056 (mesh, lllb i qos100, 5 pow., bez meterów): wideo lllb
  9,56%, qos100 0,00%; tło lllb 6,55%, qos100 24,4% (koszt rezerwy w mesh większy niż w Clos);
  20261101_220240 (starszy kształt drzewa) — podobnie
  - **WYNIKI OFICJALNE, Clos, 20 powtórzeń (2026-11-04/05)**, seed 42, identyczne harmonogramy tła
  we wszystkich wariantach (sprawdzone: `schedule.json` == `clos-frr` w 20/20 powtórzeń obu
  części SDN), ABBA, kontroler odtwarzany per przebieg, ten sam hash kodu przez cały czas
  (`177f924a…`), 0 `Traceback` w `controller.log` (300 przebiegów). Katalogi:
  `results/official/clos-frr/20261104_222207` (ecmp),
  `results/official/clos-sdn/20261104_235910` (część 1: lllb, qos100, m70, L2r70, L3H1.5),
  `results/official/clos-sdn/20261105_023134` (część 2: m90, m50, m30, L2r90, L2r50, L2r30, L3H0,
  L3H3 + kotwica `qos100_ref`). Kotwica vs `qos100` (para po powtórzeniach): wideo −0,01 ± 0,02 pp,
  tło +0,28 ± 1,45 pp — brak dryfu między częściami. Średnia ± sd z powtórzeń:

    | wariant | wideo: utrata | powt. z utratą > 1% | tło: utrata | jitter wideo [ms] | RTT p95 wideo, mediana [ms] |
    |---|---|---|---|---|---|
    | ecmp (A) | 13,8 ± 9,6% | 18/20 | 12,1 ± 6,2% | 0,41 | 59 |
    | lllb (B) | 4,9 ± 4,6% | 16/20 | 4,9 ± 3,1% | 0,24 | 70 |
    | qos100 | 0,00% | 0/20 | 12,9 ± 6,1% | 0,08 | 0,05 |
    | L1 m90 / m70 / m50 / m30 | 0 / 0 / 1,8 / 3,6% | 0 / 0 / 9 / 12 | 20,4 / 14,5 / 11,2 / 7,4% | 0,07 / 0,07 / 0,21 / 0,26 | 0,06 / 0,05 / 58 / 59 |
    | L2 r90 / r70 / r50 / r30 | 0 / 0,02 / 2,4 / 3,5% | 0 / 0 / 13 / 13 | 14,4 / 13,0 / 9,6 / 7,7% | 0,07 / 0,08 / 0,26 / 0,26 | 0,06 / 0,05 / 59 / 59 |
    | L3 H=0 / 1,5 / 3 Mb/s | 0,07 / 0,01 / 0,00% | 0 / 0 / 0 | 6,7 / 8,7 / 10,2% | 0,11 / 0,07 / 0,07 | 9,6 / 0,05 / 0,05 |

  - **WYNIKI OFICJALNE, mesh, 20 powtórzeń (2026-11-05)**, seed 42, harmonogramy identyczne z Clos
  (20/20), skrót kodu `abf842d8…` bez zmian przez obie części, 0 `Traceback` w kontrolerach.
  Katalogi: `results/official/mesh-frr/20261105_080732` (ecmp), `results/official/mesh-sdn/
  20261105_123304` (część 1) i `20261105_150652` (część 2 + kotwica). Kotwica vs `qos100`: wideo
  +0,05 ± 0,11 pp, tło −0,62 ± 1,12 pp (brak dryfu). 68 strumieni tła bez raportu serwera iperf3
  (`Bad file descriptor`, głównie qos100 przy utracie tła ok. 26%): pominięte w statystykach
  tła, więc utrata tła w qos100 może być lekko niedoszacowana. Średnia ± sd:

    | wariant | wideo: utrata | powt. z utratą > 1% | tło: utrata | RTT p95 wideo, mediana [ms] |
    |---|---|---|---|---|
    | ecmp (A) | 10,9 ± 8,0% | 19/20 | 10,4 ± 5,5% | 67 |
    | lllb (B) | 10,2 ± 6,2% | 18/20 | 8,5 ± 4,4% | 118 |
    | qos100 | 0,05 ± 0,24% | 1/20 | 26,0 ± 7,5% | 0,05 |
    | L1 m90 / m70 / m50 / m30 | 0 / 0 / 2,6 / 4,0% | 0 / 0 / 12 / 13 | 32,8 / 22,5 / 15,3 / 12,1% | 0,05 / 0,05 / 59 / 59 |
    | L2 r90 / r70 / r50 / r30 | 0 / 0 / 1,9 / 6,6% | 0 / 0 / 11 / 15 | 26,8 / 21,7 / 15,3 / 11,0% | 0,05 / 0,05 / 59 / 60 |
    | L3 H=0 / 1,5 / 3 Mb/s | 0,08 / 0,01 / 0,00% | 0 / 0 / 0 | 10,2 / 12,5 / 14,6% | 15,6 / 0,05 / 0,05 |

  - **wnioski, mesh** (różnice sparowane ± połowa CI95, pkt proc.): (1) na mesh SDN LLLB nie
  poprawia wideo względem ecmp (ecmp − lllb: wideo +0,7 ± 3,3, tło +1,9 ± 1,5); na Clos było
  +8,9 pp (hipoteza, niesprawdzona: mało równoważnych ścieżek, oba strumienie wideo trafiają na
  wspólne łącza do edge4); (2) rezerwa działa jak na Clos: R ≥ 70 → wideo 0% (wyjątek: 1 powt.
  qos100 z utratą 1,1%; przyczyna niewyjaśniona — `vid2` idzie w mesh zawsze `edge2→core3→core2→edge4` (20/20 powt., to standardowa trasa wideo C), więc to nie ucieczka z rezerwy; hipoteza: best-effort już obecny na łączu `core2→edge4` w chwili startu wideo, patrz „Seria niższego obciążenia”), R ≤ 50 → 1,9–6,6%;
  (3) koszt rezerwy dla tła na mesh jest znacznie większy niż na Clos (qos100: 26,0% vs 12,9%;
  lllb − qos100: tło −17,5 ± 2,3); (4) L3 jest tu jeszcze cenniejszy: L3H1.5 − qos100 tło
  −13,4 ± 2,6 (Clos: −4,2), L3H1.5 − m70 −10,0 ± 1,8, L3H1.5 − L2r70 −9,2 ± 2,5; względem lllb
  wideo −10,2 ± 2,9 za +4,05 ± 1,4 tła (Clos: +3,8); (5) L1/L2 przy R = 70 niewiele: m70 − qos100
  tło −3,5 ± 2,0, L2r70 − m70 −0,8 ± 2,0; L2 pomaga tylko przy R = 90 (L2r90 − m90 −6,0 ± 2,4);
  m90 − qos100: +6,9 ± 2,3 (jak na Clos); (6) H = 0: najmniej tła (10,2%) kosztem śladowych strat
  wideo (max 0,4%) i RTT 15,6 ms; H = 3 − H = 1,5: +2,1 ± 1,6 tła
  - **mesh − Clos** (sparowane po powtórzeniach): ecmp wideo −2,9 ± 5,4, tło −1,7 ± 2,7 (bez
  różnicy); lllb wideo +5,3 ± 3,0, tło +3,6 ± 1,4; qos100 tło +13,1 ± 2,2; L3H1.5 tło +3,9 ± 1,4,
  wideo bez różnicy — topologia mocno wpływa na koszt rezerwy, słabo na ecmp

  - **wnioski oficjalne** (różnice sparowane na tych samych harmonogramach, ± połowa CI95 w pkt
  proc.): (1) ecmp − lllb: wideo +8,9 ± 4,8, tło +7,2 ± 2,3 — ecmp gorszy w obu metrykach;
  (2) lllb − L3H1.5: wideo +4,9 ± 2,2, tło −3,8 ± 1,2 — rezerwa usuwa utratę wideo za cenę
  3,8 pp tła; (3) rezerwa działa dla R ≥ 70 (wideo 0 w 20/20), dla R ≤ 50 wideo traci 1,8–3,6% i
  RTT p95 mediana ≈ 59 ms (wideo trafia na przeciążoną ścieżkę); (4) m70 − qos100: tło +1,7 ± 1,8
  (bez różnicy), L2r70 − m70: −1,5 ± 1,7 (bez różnicy), L2r50 − m50: −1,6 ± 1,5, L2r30 − m30:
  +0,3 ± 1,3 — L2 daje istotny zysk tylko dla R = 90 (L2r90 − m90: −5,9 ± 2,8); m90 − qos100:
  +7,5 ± 3,0 (wyższe R w L1 pogarsza tło); (5) L3 jest najlepszą rodziną: L3H1.5 − m70 tło −5,9 ± 1,7
  przy tym samym wideo, L3H1.5 − L2r70 −4,4 ± 1,4, L3H1.5 − qos100 −4,2 ± 1,6; H = 0 ma najmniej
  strat tła (6,7%), ale wideo traci śladowo (max 0,4%) i RTT p95 mediana 9,6 ms (L3H0 − L3H1.5:
  −1,9 ± 1,2); H = 3 ≈ pełna rezerwa (L3H3 − L3H1.5: +1,5 ± 1,3). Ostrzeżenia: 16 przepływów tła
  bez raportu serwera iperf3 (`Bad file descriptor`), pominięte w statystykach; utrata wideo
  ma rozkład skośny (lllb: średnia 4,9, mediana 3,4) — podawać medianę i odsetek powtórzeń > 1%
  - **Wyniki wstępne na Clos z meterami** (5 pow.; zastąpione przez oficjalne 20 pow. powyżej; kontroler po poprawkach z kroku 10; ten sam
  seed i harmonogramy tła we wszystkich seriach, więc porównania są sparowane;
  `results/clos-full/20261102_053107`, `results/clos-layers/20261102_062444`; wykresy i CSV
  w `results/summary/`):

    | wariant | wideo: utrata | tło: utrata ± sd | jitter wideo [ms] | RTT p95 wideo [ms] |
    |---|---|---|---|---|
    | ecmp (A) | 9,5% | 13,2 ± 6,1% | 0,26 | 88 |
    | lllb (B) | 3,5% | 3,9 ± 3,3% | 0,24 | 89 |
    | qos100 | 0,00% | 11,1 ± 4,5% | 0,09 | 0,06 |
    | L1 m90 / m70 / m50 / m30 | 0 / 0 / 3,6 / 6,0% | 19,7 / 13,8 / 10,3 / 7,3% | 0,10 / 0,09 / 0,38 / 0,34 | 0,05 / 0,05 / 59 / 59 |
    | L2 r90 / r70 / r50 / r30 | 0 / 0 / 2,7 / 3,9% | 14,2 / 12,7 / 9,4 / 7,1% | 0,12 / 0,12 / 0,36 / 0,42 | 0,06 / 0,08 / 59 / 59 |
    | L3 H=0 / 1,5 / 3 Mb/s | 0,13 / 0 / 0% | 7,3 / 8,6 / 11,2% | 0,16 / 0,14 / 0,09 | 44 / 0,06 / 0,06 |

  - **wnioski:** (1) metery chronią wideo, ale stały limit (L1/L2) ma wąskie okno: przy R ≥ 70
  limit tła ≤ 3 Mb/s mieści się z wideo (6 Mb/s) na łączu 10 Mb/s; przy R ≤ 50 wideo traci
  2,7–6,0% (kolejka, RTT p95 59 ms); (2) w L1 wyższe R pogarsza tło (m90: +8,7 ± 3,1 pkt proc.
  względem qos100, 5/5 powtórzeń) — bramka wpuszcza przepływy, które meter potem dławi;
  (3) L2 poprawia to względem L1 przy wysokim R (r90 − m90: −5,6 ± 2,8 pkt proc., 5/5), przy
  niższym R różnica mieści się w szumie; (4) L3 z H = 1,5 Mb/s: wideo 0%, tło 8,6% (−2,5 ± 2,0
  pkt proc. względem qos100, +4,6 ± 3,0 względem lllb); H = 0 daje najmniej strat tła, ale
  wideo traci 0,13%, RTT p95 44 ms (reakcja metera do ok. 2 s); H = 3 ≈ pełna rezerwa;
  (5) ecmp najgorszy dla wideo (9,5%), lllb pośredni (3,5%), każda rezerwa 0%, kosztem tła
  (lllb ma najmniej strat tła)
  - powtarzalność: ta sama konfiguracja zmierzona dwa razy (np. L1 R = 70, L3 H = 0/1,5/3) daje
  różnice do ok. 2,6 pkt proc. utraty tła na powtórzenie; utrata wideo w lllb jest zmienna
  (średnio 7,9% i 3,5% w dwóch seriach tych samych harmonogramów)
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
- **Kolejki priorytetowe (macierz 2×2)** — nie wykonane; zastąpione przez metery OpenFlow
(warstwy L1–L3, decyzja 2026-11-01). Zostają jako opcjonalne porównanie
- **Miękka rezerwa bez egzekwowania (sama bramka wejścia) nie chroni wideo** (qos90/70/50 bez
metera: 5,5–5,8% utraty wideo, 2026-11-01). Z meterem chroni, ale stały limit ma wąskie okno:
L1/L2 chronią wideo tylko dla R ≥ 70, przy R ≤ 50 wideo traci 2,7–6,0%; L3 (limit dynamiczny,
H ≥ 1,5 Mb/s) chroni wideo i ma najmniej strat tła spośród wariantów z pełną ochroną.
Ograniczenia: opóźnienie reakcji metera (do ok. 2 s), brak przenoszenia przepływów już
przyjętych (tło dławione meterem zamiast przekierowane), dobór H pod scenariusz 2 × 3 Mb/s
- Poziomy obciążenia tła 50/70/90% **nie są sterowane**: generator ma tylko `arrival_rate`,
`duration_mean`, `rate`; losowe tło daje silne przeciążenie (MLU 102–125%, 8–19 z 24 łączy
> 90% w powtórzeniu). Brak parametru „docelowe obciążenie” w runnerze
- Wyniki oficjalne (20 powtórzeń, CI95 i różnice sparowane) dla Clos i mesh przy `arrival_rate` 1,0;
niższe obciążenie (0,4 i 0,7: ecmp, lllb, qos100, L3H1.5) w `results/official/load-*` (zmierzone i przeanalizowane);
jeden profil wideo (2 × 3 Mb/s), tylko UDP.
Skalowanie 10 Mb/s ≙ 10 Gb/s (3 Mb/s ≙ ~3 Gb/s ≈ nieskompresowane 1080p60) to hipoteza do
sprawdzenia w źródłach; opóźnienia bezwzględne w ms nie skalują się (`tbf latency 50ms`)
- **Ograniczenie LLLB (cecha algorytmu, nie błąd):** przy Packet-In rozmiar przepływu jest
nieznany, rezerwacja jest jednakowa (0,5 Mb/s) dla wideo i kanału sterującego, a decyzja
zapada raz. Przy jednoczesnym starcie LLLB równoważy **liczbę** przepływów, nie pasmo —
dwa strumienie danych mogą trafić na jeden spine (test 3). Świadomie nie poprawiane w B
(rezerwacja tylko dla UDP = dopasowanie pod iperf3; przenoszenie przepływów = inny
algorytm); motywacja dla C (DSCP mówi przy pierwszym pakiecie, że to wideo). W pomiarach:
starty strumieni rozsunięte o ~2 s, jednoczesny start jako osobny scenariusz najgorszego
przypadku
- Przepustowość łączy kontroler czyta z `tbf rate` w pliku clab (`topo.capacity`); łącza spoza
mapy mają zapasową wartość 10 Mb/s w `cap()`
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
- Prefiks kontenerów to `clab-<name>-<węzeł>`, gdzie `name:` to pierwsza linia pliku topologii
(nie nazwa pliku): `clab-clos-sdn-leaf1`, `clab-clos-frr-leaf1`, `clab-mesh-sdn-…`. Zmiana `name:` w pliku
działającego labu zostawia stary lab „osierocony”: `destroy -t` szuka już nowej nazwy, a `destroy --all`
go pomija; usunąć trzeba po etykiecie: `docker rm -f $(docker ps -aq --filter label=containerlab=<stara_nazwa>)`.
Przy takiej zmianie najpierw `destroy`, potem edycja, potem `deploy`
- Po przeniesieniu/zmianie nazwy plików pilnować: `env: TOPO_FILE` w topologii SDN
(rozszerzenie `.yml`!), ścieżki `binds` do `configs/frr/...` w topologiach FRR,
`DEFAULT_TOPOLOGIES` w `common.py` skilla i `topology_files` w scenariuszach — każdy z tych
błędów przerywa albo uruchomienie kontrolera, albo dry-run
- `containerlab` działa bez `sudo` dla użytkownika z grupy `clab_admins`; `sudo -n true` nie
jest dobrym testem (reguła NOPASSWD nie istnieje), a bilet `sudo -v` z jednego terminala nie
działa w drugim (osobne TTY)
- Dwa laby naraz (SDN + FRR) podnoszą średnie CPU maszyny: ecmp 15% (sam lab FRR) vs 23% (oba
laby), SDN 26–33% niezależnie od drugiego labu; szczyty 92–98% w każdym przebiegu (wcześniejsze
„ok. 50%” nie wynika z danych). W seriach bez wariantu `ecmp` zatrzymać lab FRR; w trakcie serii
nie uruchamiać ciężkich zadań
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
100% strat; sprawdzenie: `docker logs clab-clos-sdn-ryu-controller 2>&1 | grep -c "connected from"` = 7
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
- Zmiana `env:` kontrolera (np. `POLICY`) wymaga odtworzenia kontenera
(`containerlab deploy --reconfigure`; runner robi to sam) — `docker restart` zostawia stare
zmienne; sprawdzenie:
`docker exec clab-clos-sdn-ryu-controller env | grep POLICY` i linia `Path selection policy` w logu
- Wywołanie loggera z większą liczbą argumentów niż `%s` w formacie → `TypeError: not all
arguments converted` (traceback w logu, linia nie zostaje wypisana, ruch działa dalej)
- Przepustowość łączy jest pewna tylko z `tc`: `docker exec clab-clos-sdn-leaf1 tc qdisc show dev eth1`
→ `rate 10Mbit burst 12800b`; empirycznie iperf3 `-b 15M` → receiver ~9,5 Mb/s, `Links` ~100%
- Statystyki przepływów w Ryu: `dict(stat.match.items())` daje pola dopasowania, a port
wyjściowy trzeba wziąć z instrukcji `OFPInstructionActions` (reguła z meterem ma na pierwszym
miejscu `OFPInstructionMeter` — `instructions[0].actions` kończy się `AttributeError`, który
po cichu blokuje odświeżanie `class_bps`); `OFPFlowStatsRequest(datapath)` bez
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
- Meter w OVS: stawkę zmienia `OFPMC_MODIFY` na tym samym `meter_id` (reguły się nie zmieniają);
stan: `ovs-ofctl -O OpenFlow13 dump-meters br0`, liczniki: `meter-stats`
- Pingi wideo (ICMP, DSCP 46) w `pending` nie mogą liczyć się jak strumień danych (szacunek 0),
inaczej drugi strumień wideo ucieka z rezerwy (spill) — patrz krok 10
- Wariant `ecmp` w runnerze wymaga labu FRR stojącego razem z SDN. Po `deploy` OSPF potrzebuje
1–2 minut; wcześniej runner przerywa z komunikatem „OSPF niegotowy: … (0/3 FULL)” — poczekać
(sprawdzenie: `docker exec clab-clos-frr-leaf1 vtysh -c "show ip ospf neighbor"`) i puścić ponownie
- Zatrzymywanie serii: `pkill -f run_scenario.py` pasuje do własnej powłoki (kod 144 i ubity
terminal) — używać `ps -eo pid,cmd | grep [r]un_scenario` i `kill <PID>`; serie w tle uruchamiać
przez `setsid nohup … &`, żeby przeżyły zamknięcie terminala
- Niedokończone katalogi w `results/` (przerwana seria, brak `flows.csv`) są pomijane przez
`summary_charts.py`, ale wariant występujący w dwóch katalogach pasujących do wzorca przerywa
skrypt błędem — przy powtórkach usuwać stary katalog
- `controllers/__pycache__` należy do roota (kontener): `py_compile` na hoście kończy się
`PermissionError`; składnię sprawdzać `python3 -c "import ast; ast.parse(open(…).read())"`
- Odchylenie standardowe z powtórzeń zawiera różnice obciążenia między powtórzeniami (51–59
strumieni tła); porównania sparowane (ten sam harmonogram) są dokładniejsze niż same średnie

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
  2. Kolejki priorytetowe: **zastąpione** meterami OpenFlow (warstwy L1–L3, 2026-11-01);
  macierz 2×2 z `htb` nie wykonana
  3. Rezerwa ścieżki wideo: **zaimplementowana** jako drzewo wideo z limitem tła egzekwowanym
  meterem (L1), bramką „mieści się” (L2) i limitem dynamicznym (L3); wyniki w „Wyniki pomiarów”
  4. Przenoszenie istniejących przepływów (rerouting): **rozstrzygnięte** — decyzja tylko
  przy starcie przepływu (spójne z B)
- Awarie łączy/węzłów — **poza zakresem pracy** (decyzja autora, zapisana w AGENTS.md);
PortStatus / fast-failover nie są implementowane

## Następny krok
- Zacommitować: `results/official/mesh-*`, wykresy (`wykresy-*`), `dane_mesh_wszystko.xlsx`,
`analysis/summary_charts.py`, `docs/status.md`, `README.md`, usunięcie `results/layers-clos*`;
potem wyniki serii `results/official/load-*`; przed wyłączeniem VM zawsze `git push`
- Porządki: wyniki wstępne (5 pow.) `clos-full`, `clos-layers`, `results/summary`, `reserve-sweep`,
`mesh-lllb-vs-qos` do usunięcia po zatwierdzeniu wyników oficjalnych (usunięte 2026-11-05:
`layers-clos*`, `mesh-test`, puste katalogi po dry-runach; lokalne `raw/` starych serii zostały)
- **Seria niższego obciążenia** (`arrival_rate` 0,4 i 0,7): zakończona i przeanalizowana (patrz „Wyniki
  pomiarów”); do zrobienia: wyjaśnienie incydentów (mesh 0,4 L3H1.5 powt. 8 i mesh 1,0 qos100 powt. 1)
  na logach, ewentualnie powtórzenie `load-0.7/mesh-sdn` na zamrożonym kodzie (tylko dla porządku —
  kotwice wskazują na równoważność)
- **Wariant D (OpenQoS)**: zmierzony i przeanalizowany przy `arrival_rate` 1,0 (patrz krok 11); do
  zrobienia opcjonalnie D przy 0,4 i 0,7 (openqos, openqos_w5 na mesh; ok. 2 h na topologię) oraz
  jitter wokół przeniesień wideo
- Czułość na tempo wideo (np. 1,5 / 3 / 4,5 Mb/s; `VIDEO_EST_BPS` obecnie stałe 3 Mb/s —
  uczynić zmienną env lub adaptacyjną) i poziomy obciążenia tła (patrz niżej)
- Zbadać powtórzenia z długim RTT w L3H1.5 (średnia 2,8 ms, mediana 0,05 ms)
- Opcjonalnie: macierz 2×2 z kolejkami (`shape.sh <iface> <rate> <tbf|prio>`, `htb` z klasami
wideo/reszta, filtr `u32 match ip dsfield 0xb8 0xfc`, zmienna `QDISC` w topologiach) jako
porównanie z meterami
- Poziomy obciążenia tła: zrealizowane przez dobór `arrival_rate` (0,4 / 0,7 / 1,0; wyniki w „Wyniki pomiarów”),
nie przez docelowe 50/70/90% łącza (nie ma takiego parametru w generatorze); niezmierzony: D przy 0,4 / 0,7
oraz obciążenia > 1,0
- Opis ograniczeń w pracy: jeden poziom obciążenia, jeden profil wideo, ecmp zależny od portów
źródłowych iperf3 (hash L4, wynik nie jest powtarzalny per harmonogram), wiele porównań naraz
bez poprawki
- Drobne porządki w kodzie: sprawdzenie `pkt_arp is None`, literówki w komentarzach
(„zapytaniam”, „obciązenia”, „miedzy”, „ściezki”), docstring `_install_host_rule`
(„w danym leafie”), spacje na końcu linii
- Przypiąć `kathara/sdn` do digestu
(`sha256:19cb5b383367e1d204e76f7e6e65753fbc947647747879f24883558a5c3fd8c5`)
- Fix TSO/GRO, jeśli tło ma obejmować TCP (obecnie wszystkie pomiary UDP)
