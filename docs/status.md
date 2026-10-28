# Status projektu (ostatnia aktualizacja: 2026-10-28)

## Działa — wariant A (OSPF + ECMP)
- Topologia 3 spine × 4 leaf, 3 hosty/leaf wdrożona
(`topologies/spine-leaf-3x4.clab.yml`)
- Adresacja IP (fabric /31, hosty /24, loopbacki /32) ustawiona przez `exec`
- Bridge host-side na leafach — zweryfikowany (ping h1-video ↔ h1-bg1)
- Bramy domyślne na hostach (`ip route replace default via 10.1.L.1`; `add` pada na
konflikcie z trasą mgmt eth0)
- OSPF area 0 na wszystkich 7 routerach (`configs/frr/`, ospfd.conf per węzeł,
bind-mount do /etc/frr):
sąsiedzi FULL, interfejsy p2p, timery ~1 s (dead-interval minimal hello-multiplier
4)
- ECMP: maximum-paths 3, hash L4 (fib_multipath_hash_policy=1) — rozrzut przepływów
potwierdzony na licznikach (8 strumieni UDP → wszystkie 3 uplinki leaf1, rozkład
nierównomierny)
- Limity `tc tbf` w exec topologii: leaf↔spine 10mbit/burst 32kbit, host↔leaf
100mbit/burst 320kbit, po obu końcach łącza
- Test: wideo UDP 3 Mb/s DSCP EF bezstratnie, jitter 0.216 ms

## Działa — SDN (warianty B/C, infrastruktura)
- Topologia `topologies/sdn.clab.yaml`: ten sam układ 3×4 + hosty, przełączniki OVS
3.1.0 (`kathara/sdn`), OpenFlow 1.3
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
- Stałe MAC hostów w `sdn.clab.yaml` (exec: `ip link set dev eth1 address`):
`02:00:0L:00:00:HH` (L = numer leafa, HH = ostatni oktet IP hex: 0a/0b/0c)
- Kontroler (mgmt 172.20.20.100:6653) uruchamia własną aplikację
`controllers/controller_ryu.py` (klasa `Fabric`); binds: `../controllers:/controllers`
i `../topologies:/topologies:ro`, plik topologii wskazuje `env: TOPO_FILE`;
zmiana kodu → `docker restart clab-sdn-ryu-controller`
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
  `select_path` (na razie round-robin per para), reguły prio 70 z 5-tuple na każdym hopie
  od końca ścieżki, `idle_timeout=10`, Packet-Out pierwszego pakietu wprost na port
  uplinku; log `Flow (…) -> leaf1 -> spine2 -> leaf4`
  - test (2026-10-26): 48/48 pingów (4 hosty źródłowe × 12 celów), trzy pingi do
  10.1.4.10/11/12 → spine1, spine2, spine3; odpowiedzi z leaf4 własnym licznikiem
  (asymetria jak w ECMP); reguły 70 z rosnącym `n_packets` na leaf1, spine'ach, leaf4
- Podmiana samego kontrolera bez ruszania labu:
`containerlab destroy/deploy -t sdn.clab.yaml --node-filter ryu-controller`
- Ryu 4.34 także na hoście w `.venv` (Python 3.9) — do podpowiedzi i lintowania w IDE;
uruchamianie i pomiary w kontenerze:
  ```bash
  uv venv --seed -p 3.9 .venv && source .venv/bin/activate
  pip install setuptools==58.2.0 wheel pbr
  pip install --no-build-isolation eventlet==0.30.2 dnspython==1.16.0 ryu==4.34
  ```
- Ściągawka Ryu (dekorator `@set_ev_cls`, fazy, zdarzenia, skróty): `docs/ryu-sciagawka.md`

## Nie działa / nie zrobione
- Monitoring obciążenia łączy — brak; wybór ścieżki to na razie round-robin, który nie
patrzy na obciążenie
- Warianty B (LLLB) i C (QoS-Aware) — nierozpoczęte; logika C w fazie analizy
(decyzje otwarte, patrz niżej)
- Topologia mesh (sugestia promotora) — kontroler już ją obsłuży, ale samej topologii
(clab dla FRR i OVS, konfiguracje FRR) jeszcze nie ma
- Ruch w obrębie jednego przełącznika przechodzi przez regułę hosta (eth_src=GW_MAC,
TTL−1 — traktowany jak routowany)
- **Niespójny burst tbf na łączach leaf↔spine: A = 32kbit, SDN = 100kbit** — do
wyrównania przed pomiarami porównawczymi
- Test TCP ~10 Mb/s — niezaliczony (TSO/GRO, patrz pułapki)

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
Wszystkie testy UDP z `-l 1400` (zgodne z realnym RTP).
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
topologii; zmiana `binds`/`cmd` wymaga odtworzenia kontenera (destroy/deploy
`--node-filter`), zmiana samego `.py` — tylko `docker restart`
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
`TOPO_FILE=../topologies/sdn.clab.yaml ../.venv/bin/python -c "import controller_ryu as c; c.Fabric()"`;
bez aktywnego venv nie ma polecenia `python` (tylko systemowy `python3` 3.14)
- git: puste pliki w `.git/objects` po nagłym wyłączeniu VM (2026-10-21) — naprawa:
kopia `.git`, `find .git/objects -type f -empty -delete`, `git fetch origin`, `git fsck --full`
- **Po restarcie maszyny lab jest martwy**: Docker sam podnosi kontenery, ale bez łączy
veth i bez `exec` (brak eth1+, OVS nie działa — `db.sock: Connection refused`, kontroler
bez połączeń). Zawsze `sudo containerlab deploy -t sdn.clab.yaml --reconfigure`
(albo `destroy` przed wyłączeniem VM). Zdarzyło się 2026-10-12 i 2026-10-26
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
- Ostateczne prędkości łączy / parametry `tc tbf` (rate, burst) — do ustalenia
(i wyrównania między A a SDN).
- Decyzje projektowe algorytmu C (przeanalizowane zalety/wady, bez rozstrzygnięć):
  1. Klasyfikacja: samo DSCP czy DSCP + granica zaufania na portach hostów; EF czy AF41
  2. Kolejki priorytetowe: tylko w C, we wszystkich A/B/C, czy macierz 2×2
  (C z kolejkami / bez); uwaga: OVS QoS (htb) koliduje z root qdisc tbf
  3. Rezerwa ścieżki wideo: twarda / miękka (work-conserving) / obie jako podwarianty
  4. Przenoszenie istniejących przepływów (rerouting) czy decyzja tylko przy starcie
  5. Awaria: PortStatus czy też group fast-failover; scenariusz link down czy netem loss

## Następny krok
- Krok 7: monitor obciążenia — wątek `hub.spawn`, `OFPPortStatsRequest` co 1 s do
wszystkich przełączników, handler `EventOFPPortStatsReply`: wykorzystanie każdego łącza
(przełącznik, port) z Δtx_bytes względem 10 Mb/s
- Krok 8: wariant B (LLLB) — `select_path` wybiera ścieżkę o najmniejszym
max(wykorzystanie łączy na ścieżce)
- Krok 9: wariant C (QoS-Aware) — po rozstrzygnięciu decyzji otwartych
- Drobne porządki w kodzie: sprawdzenie `pkt_arp is None`, literówka w komentarzu
`_handle_arp` („zapytaniam”), docstring `_install_host_rule` („w danym leafie”),
spacje na końcu linii
- Wyrównać burst tbf leaf↔spine między A a SDN
- Przypiąć `kathara/sdn` do digestu
(`sha256:19cb5b383367e1d204e76f7e6e65753fbc947647747879f24883558a5c3fd8c5`)
