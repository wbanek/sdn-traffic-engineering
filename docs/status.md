# Status projektu (ostatnia aktualizacja: 2026-10-17)

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
- Kontroler (mgmt 172.20.20.100:6653) uruchamia własną aplikację
`controllers/controller_ryu.py` (klasa `Fabric`), montowaną bindem
`../controllers:/controllers`; zmiana kodu → `docker restart clab-sdn-ryu-controller`
- Aplikacja `Fabric` — zaimplementowane i przetestowane (2026-10-15):
  - table-miss (prio 0 → CONTROLLER) na wszystkich przełącznikach
  - drop IPv6 i LLDP (prio 100) — usuwa szum ND/MLD (63 pakiety odrzucone na leaf1
  zamiast Packet-In)
  - uczenie hostów z ruchu (ARP i IPv4) tylko na portach hostów leafów (10–12),
  z walidacją podsieci (IP z 10.1.L.0/24 przyjmowany tylko z leafa L); pomijane 0.0.0.0
  - proxy ARP: zapytanie o bramę 10.1.L.1 → odpowiedź wirtualnym `GW_MAC`
  02:00:00:00:00:fe; zapytanie o znany host z tego samego leafa → jego prawdziwy MAC
  - test: h1-video dostał MAC bramy, kontroler nauczył się h1-video
  (10.1.1.10, leaf1, port 10); ping 10.1.1.10 → 10.1.3.10 dociera do kontrolera
  jako Packet-In IPv4 (dalej brak forwardingu — zgodnie z oczekiwaniem)
- Routing IP — część zrobiona (commit 464ddcf, 2026-10-17):
  - spine'y: proaktywnie przy połączeniu `ipv4_dst=10.1.L.0/24 → port L` (prio 50);
  zweryfikowane w `dump-flows` spine1 (4 reguły)
  - leaf docelowy: przy nauczeniu hosta (`_learn` → `_install_host_rule`) reguła
  `ipv4_dst=host → eth_src=GW_MAC, eth_dst=MAC hosta, dec_ttl, output port hosta`
  (prio 50); zweryfikowane: reguła dla 10.1.3.10 na leaf3 port 10
  - słownik `datapaths` (dpid → datapath) uzupełniany przy połączeniu; log
  „Switch dpid=… connected” — 7/7 przełączników
  - stałe `SPINES = {0x11, 0x12, 0x13}`, `UP_LINK` (spine → port uplinku na leafie)
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
- Aktywne odpytywanie ARP przez kontroler — brak: zapytanie o nieznany host jest
ignorowane (host musi najpierw sam coś wysłać). Do zrobienia: `_resolve()` (who-has od
„bramy” na porty hostów leafa docelowego, limit 1/s) + lista oczekujących (`pending`)
odpowiadanych po nauczeniu; to samo dla IPv4 do nieznanego hosta
- Routing IP — brak wyboru uplinku na leafie źródłowym: pakiet do 10.1.D.0/24
(D ≠ lokalny leaf) trafia na table-miss i kończy w kontrolerze → brak łączności
między leafami (`UP_LINK` zdefiniowany, jeszcze nieużywany)
- Ruch w obrębie jednego leafa przechodzi przez regułę hosta (eth_src=GW_MAC, TTL−1 —
traktowany jak routowany); jeszcze nie przetestowany pingiem
- Reguła hosta istnieje tylko dla hostów nauczonych w bieżącym uruchomieniu kontrolera
(restart kasuje `hosts`; host pojawia się ponownie dopiero, gdy sam coś wyśle)
- Warianty B (LLLB) i C (QoS-Aware) — nierozpoczęte; logika C w fazie analizy
(decyzje otwarte, patrz niżej)
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

## Odłożone na po spotkaniu z promotorem
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
- Leaf źródłowy: wybór uplinku dla `ipv4_dst=10.1.D.0/24` (D ≠ lokalny) — najpierw ECMP
przez group table `select` z bucketami na porty 1–3 (punkt odniesienia dla B/C);
reguła prio niższy niż reguły hostów (np. 40), żeby ruch lokalny nie szedł w górę
- Test end-to-end: ping h1-video ↔ h1-bg1 (ten sam leaf) i h1-video ↔ h4-video
(przez spine), `dump-flows` z licznikami n_packets na leafach i spine'ach
- `controller_ryu.py`: aktywne odpytywanie ARP (`_resolve` + `pending`)
- Drobne porządki w kodzie: nieużywane importy (`hub`, `tcp`, `udp` — te dwa pod
przyszłe reguły 5-tuple), nieaktualne komentarze/docstringi („Ignorowanie pakietów ARP”,
`_send_arp` „Wysyłanie zapytania”), brak sprawdzenia `ipv4_pkt is None`
- Wyrównać burst tbf leaf↔spine między A a SDN
- Przypiąć `kathara/sdn` do digestu
(`sha256:19cb5b383367e1d204e76f7e6e65753fbc947647747879f24883558a5c3fd8c5`)
