# Status projektu (ostatnia aktualizacja: 2026-10-11)

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
3.1.0 (`kathara/sdn`), OpenFlow 1.3, `fail-mode secure` ustawiany przed `add-port`,
limity `tc tbf` jak w wariancie A
- Własny obraz kontrolera `sdn-ryu:4.34` (`images/ryu/Dockerfile`):
`docker build -t sdn-ryu:4.34 images/ryu/`
- Kontroler (mgmt 172.20.20.100:6653) uruchomiony z `ryu.app.ofctl_rest` (bez
forwardingu) — 7/7 przełączników `is_connected: true`, 7 sesji TCP po stronie kontrolera
- Podmiana samego kontrolera bez ruszania labu:
`containerlab destroy/deploy -t sdn.clab.yaml --node-filter ryu-controller`

## Nie działa / nie zrobione
- Własna aplikacja Ryu (statyczna mapa topologii, ARP proxy bramy 10.1.L.1,
proaktywne Flow Mods) — brak, więc brak łączności host↔host w SDN
- Warianty B (LLLB) i C (QoS-Aware) — nierozpoczęte
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
- Ryu 4.34 (ostatnie wydanie, 2020) nie instaluje się na nowym toolchainie: wymaga
`setuptools==58.2.0` + `pip install --no-build-isolation` (inaczej `get_script_args`
AttributeError) oraz `eventlet==0.30.2`, `dnspython==1.16.0` (inaczej `ALREADY_HANDLED`)
- `ryu.app.simple_switch_13` na Clos = burza broadcastów (pętle leaf-spine-leaf, brak
STP; hosty same wysyłają multicast IPv6 po podniesieniu interfejsu) — nie uruchamiać
- `ryu-manager --verbose` loguje eventy tylko, gdy jakaś aplikacja je konsumuje — sam
`ofp_handler` nie pokaże `EventOFPSwitchFeatures`; połączenia sprawdzać przez
`ovs-vsctl list controller` lub `ofctl_rest` (`/stats/switches`)
- `cmd:` w YAML clab nadpisuje `CMD` z Dockerfile

## Odłożone na po spotkaniu z promotorem
- Fix TSO/GRO (`ethtool -K <ethX> tso off gso off gro off` na wszystkich interfejsach
labowych; do utrwalenia w exec obu topologii, żeby A/B/C miały identyczne warunki).
Obowiązkowy, jeśli tło będzie TCP; przy tle UDP nieblokujący.
- Ostateczne prędkości łączy / parametry `tc tbf` (rate, burst) — do ustalenia.

## Następny krok
- Bazowa aplikacja Ryu `controllers/fabric_base.py`: stałe datapath-id w exec OVS,
statyczna mapa dpid→porty, ARP proxy bramy, proaktywne Flow Mods
host→leaf→spine→leaf→host, ECMP przez group table `select` (punkt odniesienia dla B/C)
- Przypiąć `kathara/sdn` do digestu
(`sha256:19cb5b383367e1d204e76f7e6e65753fbc947647747879f24883558a5c3fd8c5`)
- Usunąć zagnieżdżony, nieaktualny klon `sdn-traffic-engineering/`
