import os, time, zlib

from topo import Topology
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4, tcp, udp, in_proto
from ryu.lib import hub

TOPO_FILE = os.environ.get("TOPO_FILE", "/topologies/clos-sdn.clab.yml")
POLICY = os.environ.get("POLICY", "lllb")
VIDEO_DSCP = 46
SPILL = 0.9   # powyżej tego obciążenia rezerwa "przelewa się"
RESERVE_PCT = float(os.environ.get("RESERVE_PCT", "100"))   # % łącza rezerwowego dla wideo
GW_MAC = "02:00:00:00:00:fe"  # Stały adres MAC bramy


LAYERS = int(os.environ.get("LAYERS", "1"))   # 1 = meter, 2 = + "mieści się", 3 = + limit dynamiczny
MARGIN = float(os.environ.get("MARGIN", "0.1"))   # zapas na wahania wideo
HEADROOM_BPS = float(os.environ.get("HEADROOM_MBPS", "0")) * 1_000_000
VIDEO_EST_BPS = 3_000_000       # szacunek nowego strumienia wideo do czasu pomiaru
BE_EST_INIT_BPS = 2_000_000
PENDING_TTL = 2.5               # s; tyle zajmuje pojawienie się przepływu w FlowStats (2 próbki)
METER_STEP_KBPS = 250           # histereza zmiany metera
MIN_BE_BPS = 300_000            # dolna granica limitu BE na rezerwie

# Wariant D (baseline): OpenQoS, Egilmez i in., APSIPA ASC 2012 - reaktywny routing QoS
# bez rezerwacji i bez kolejek. Wideo: CSP min sum(c_ij) przy liczbie hopów <= Dmax,
# c_ij = g_ij + 1, g_ij = (T - 0,7 B) / T dla T > 0,7 B (wzory 3-5). Tło: najkrótsza ścieżka.
# Przenoszenie wideo = usunięcie reguł QoS przy zmianie stanu przeciążenia łącza (sekcja III-B.1).
CONG_THRESH = 0.7               # łącze przeciążone od 70% wykorzystania
DECONG_PERIODS = 3              # tyle okresów luzu przed uznaniem łącza za odciążone
DMAX_SLACK = int(os.environ.get("DMAX_SLACK", "1"))        # Dmax = najkrótsza + slack [hopy]
OPENQOS_BE = os.environ.get("OPENQOS_BE", "hash")          # hash = ECMP-podobnie, single = paths[0]
CONG_WEIGHT = float(os.environ.get("CONG_WEIGHT", "1"))    # waga g_ij w koszcie; 1 = dosłownie wg (4)-(5)
FLOW_CLASS_TTL = 15             # s; po tym czasie bez FlowStats klasa przepływu jest zapominana



class Fabric(app_manager.RyuApp):
    # Określenie używanej wersji protokołu OpenFlow (OpenFlow 1.3)
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Fabric, self).__init__(*args, **kwargs)
        self.logger.info("Path selection policy: %s", POLICY)
        self.topo = Topology(TOPO_FILE)
        self.logger.info("Topology %s: %d switches, %d hosts",
                        TOPO_FILE, len(self.topo.switches), len(self.topo.hosts))

        # Trasy domyślne: dla każdego przełącznika brzegowego drzewo najkrótszych ścieżek do niego
        self.routes = {edge: self.topo.next_hops_to(edge) for edge in self.topo.gateways}

        # k ścieżek między każdą parą przełączników brzegowych
        edges = sorted(self.topo.gateways)
        self.paths = {(src, dst): self.topo.paths(src, dst)
                      for src in edges for dst in edges if src != dst}
        self.rr = {} # licznik round-robin

        # Słownik przechowujący informacje o przełącznikach
        self.datapaths = {}

        # flow -> (ścieżka, czas wyboru); ochrona przed duplikatami Packet-In
        self.active = {}

        # Monitor obciązenia łączy miedzy przełącznikami
        self.link_peer = {(dpid, port): nb
                          for dpid, nbs in self.topo.adj.items()
                          for nb, port in nbs.items()}  # (dpid, port) -> sąsiad
        self.port_prev = {} # (dpid, port) -> (tx_bytes, czas w sekundach)
        self.link_bps = {} # (dpid, port) -> zmierzona przepływność [b/s]
        self.flow_class = {}    # flow -> "video" | "be"
        self.flow_prev = {}     # (dpid, flow) -> (bajty, czas) do liczenia przepływności reguły
        self.class_bps = {}     # (dpid, port) -> {"video": b/s, "be": b/s}
        self.pending = {}       # (dpid, port) -> [(klasa, b/s, wygasa)]  przepływy jeszcze niewidoczne w statystykach
        self.est_be = BE_EST_INIT_BPS   # EWMA przepływności nowego przepływu best-effort
        self.meter_rate = {}    # (dpid, port) -> ostatnia stawka metera [kb/s]
        self.flow_last = {}     # flow -> czas ostatniego widzenia (wybór lub FlowStats)
        self.cong = {}          # openqos: (dpid, port) -> {"congested": bool, "clear": okresy luzu}


        hub.spawn(self._monitor)

    # ---------- reguły startowe ----------
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        dpid = datapath.id

        if dpid not in self.topo.names:
            self.logger.warning("Unknown switch dpid=%#x - not in %s", dpid, TOPO_FILE)
            return
        self.datapaths[dpid] = datapath
        self.logger.info("Switch %s (dpid=%#x) connected from %s",
                         self.topo.names[dpid], dpid, datapath.address)

        # Tworzenie reguły domyślnej (table-miss flow entry)
        match = parser.OFPMatch()  # Dopasowanie do wszystkich pakietów
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

        for eth_type in (ether_types.ETH_TYPE_IPV6, ether_types.ETH_TYPE_LLDP):
            match = parser.OFPMatch(eth_type=eth_type)
            actions = []  # Brak akcji (pakiety zostaną odrzucone)
            self.add_flow(datapath, 100, match, actions)


        # Trasy domyślne do podsieci wszystkich innych przełączników brzegowych
        for edge, next_hops in self.routes.items():
            # Wykrycie własnej podsieci
            if edge == dpid:
                continue
            _, net = self.topo.gateways[edge]
            net_match = {"eth_type": ether_types.ETH_TYPE_IP,
                         "ipv4_dst": (str(net.network_address), str(net.netmask))}

            # Trasa domyślna na każdym przełączniku
            self.add_flow(datapath, 50, parser.OFPMatch(**net_match),
                          [parser.OFPActionOutput(next_hops[dpid])])

            # Nowy przepływ od hosta tego przełącznika → decyzja kontrolera
            for port in self.topo.host_ports(dpid):
                self.add_flow(datapath, 55, parser.OFPMatch(in_port=port, **net_match),
                              [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                                      ofproto.OFPCML_NO_BUFFER)])

        # Wariant C: jeden wspólny meter dla całego best-effort na każdym łączu rezerwy
        # (egzekwuje limit (100 - R)% pojemności łącza, wideo nie ma meteru)
        if POLICY == "qos":
            for (sw, port) in self.topo.reserved:
                if sw != dpid:
                    continue
                rate_kbps = max(int(self.be_limit((sw, port)) / 1000), 1)
                self.meter_rate[(sw, port)] = rate_kbps
                band = parser.OFPMeterBandDrop(rate=rate_kbps, burst_size=50)
                datapath.send_msg(parser.OFPMeterMod(
                    datapath=datapath, command=ofproto.OFPMC_ADD,
                    flags=ofproto.OFPMF_KBPS | ofproto.OFPMF_BURST,
                    meter_id=port, bands=[band]))

        # Doręczenie do lokalnych hostów (MAC znany z topologii)
        for host in self.topo.hosts.values():
            if host.dpid == dpid and host.mac:
                self._install_host_rule(dpid, host.ip, host.mac, host.port)


    def add_flow(self, datapath, priority, match, actions, idle_timeout=0, meter_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Tworzenie instrukcji (instructions) dla przepływu
        inst = []
        if meter_id is not None:
            inst.append(parser.OFPInstructionMeter(meter_id))
        inst.append(parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions))
        mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                match=match, instructions=inst,
                                idle_timeout=idle_timeout)
        datapath.send_msg(mod)

    def _install_host_rule(self, dpid, ip, mac, port):
        """Instalowanie reguły dla hosta w danym leafie"""
        datapath = self.datapaths.get(dpid)
        if datapath is None:
            self.logger.warning("Datapath for switch %s not found. Cannot install flow for host %s", dpid, ip)
            return

        parser = datapath.ofproto_parser
        match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_dst=ip)
        actions = [
            parser.OFPActionSetField(eth_src=GW_MAC),
            parser.OFPActionSetField(eth_dst=mac),
            parser.OFPActionDecNwTtl(),  # Decrement TTL
            parser.OFPActionOutput(port)
        ]
        self.add_flow(datapath, 60, match, actions)
        self.logger.info("Host rule: %s (mac=%s) on %s port %d",
                         ip, mac, self.topo.names[dpid], port)

    # ---------- Packet-In ----------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath

        # Pobranie informacji o porcie wejściowym
        in_port = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)

        if eth is None:
            return  # Ignorowanie pakietów, które nie zawierają nagłówka Ethernet

        if in_port not in self.topo.host_ports(datapath.id):
            return  # Obsługujemy tylko ruch wprost od hostów

        # Sprawdzenie typu pakietu
        if eth.ethertype == ether_types.ETH_TYPE_ARP:
            self._handle_arp(datapath, in_port, pkt.get_protocol(arp.arp))
            return

        if eth.ethertype == ether_types.ETH_TYPE_IP:
            ipv4_pkt = pkt.get_protocol(ipv4.ipv4)
            if ipv4_pkt is None:
                return
            self._learn(ipv4_pkt.src, eth.src, datapath.id, in_port)

            dst_edge = self.topo.edge_of(ipv4_pkt.dst)
            if dst_edge is not None and dst_edge != datapath.id:
                self._route_flow(datapath, in_port, pkt, ipv4_pkt, msg.data, dst_edge)
                return

            self.logger.debug("Unrouted IPv4 on %s port %d: %s -> %s",
                              self.topo.names[datapath.id], in_port, ipv4_pkt.src, ipv4_pkt.dst)

    # ---------- Monitoring portów ----------
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_handler(self, ev):
        dpid = ev.msg.datapath.id
        for stat in ev.msg.body:
            key = (dpid, stat.port_no)
            if key not in self.link_peer:
                continue
            now = stat.duration_sec + stat.duration_nsec / 1e9
            prev = self.port_prev.get(key)
            self.port_prev[key] = (stat.tx_bytes, now)

            if prev is None:
                continue

            d_bytes = stat.tx_bytes - prev[0]
            d_t = now - prev[1]
            if d_bytes < 0 or d_t <= 0:
                continue

            self.link_bps[key] = d_bytes * 8 / d_t

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_handler(self, ev):
        dpid = ev.msg.datapath.id
        per_link = {}
        for stat in ev.msg.body:
            if stat.priority != 70:
                continue
            m = dict(stat.match.items())
            flow = (m["ip_proto"], m["ipv4_src"], m["ipv4_dst"],
                    m.get("tcp_src", m.get("udp_src")), m.get("tcp_dst", m.get("udp_dst")))
            # reguły z meterem mają instrukcję metera przed akcjami
            port = next(a.port for i in stat.instructions
                        if isinstance(i, ev.msg.datapath.ofproto_parser.OFPInstructionActions)
                        for a in i.actions)
            now = stat.duration_sec + stat.duration_nsec / 1e9
            prev = self.flow_prev.get((dpid, flow))
            self.flow_prev[(dpid, flow)] = (stat.byte_count, now)
            self.flow_last[flow] = time.time()

            if prev is None:
                continue
            d_bytes = stat.byte_count - prev[0]
            d_t = now - prev[1]
            if d_bytes < 0 or d_t <= 0:
                continue    # reguła wgrana ponownie 

            cls = self.flow_class.get(flow, "be")
            link = per_link.setdefault((dpid, port), {"video": 0.0, "be": 0.0})
            rate = d_bytes * 8 / d_t
            link[cls] += rate
            if cls == "be" and dpid == self.topo.edge_of(flow[1]):   # próbka z pierwszego hopa
                self.est_be = 0.98 * self.est_be + 0.02 * rate

        for key in [k for k in self.class_bps if k[0] == dpid]:
            del self.class_bps[key]
        self.class_bps.update(per_link)

    def class_load(self, path, cls):
        """Wykorzystanie najbardziej obciążonego łącza ścieżki przez daną klasę ruchu"""
        return max((self.class_load_bps(hop, cls) / self.cap(hop)
                    for hop in self.topo.path_ports(path)), default=0.0)

    def pending_bps(self, hop, cls=None):
        now = time.time()
        return sum(bps for c, bps, exp in self.pending.get(hop, [])
                   if exp > now and (cls is None or c == cls))

    def link_load(self, hop):
        """Pomiar + przepływy wybrane przed chwilą [b/s]"""
        return self.link_bps.get(hop, 0.0) + self.pending_bps(hop)

    def class_load_bps(self, hop, cls):
        return self.class_bps.get(hop, {}).get(cls, 0.0) + self.pending_bps(hop, cls)

    def be_limit(self, hop):
        """Ile best-effort może zająć na łączu rezerwy [b/s]"""
        cap = self.cap(hop)
        if LAYERS < 3:
            return (100 - RESERVE_PCT) / 100 * cap
        video = self.class_load_bps(hop, "video")
        return max(cap - video * (1 + MARGIN) - HEADROOM_BPS, MIN_BE_BPS)

    def fits(self, path):
        """Czy best-effort zmieści się na łączach rezerwy tej ścieżki"""
        for hop in self.topo.path_ports(path):
            if hop not in self.topo.reserved:
                continue
            used = self.class_load_bps(hop, "be")
            if LAYERS < 2:
                if used / self.cap(hop) >= (100 - RESERVE_PCT) / 100:   # stary próg (warstwa 1)
                    return False
            elif used + self.est_be > self.be_limit(hop):
                return False
        return True
    
    def touches_reserved(self, path):
        """Czy ścieżka używa łącza rezerwy wideo"""
        return any(hop in self.topo.reserved for hop in self.topo.path_ports(path))

    def path_load(self, path):
        """Wykorzystanie najbardziej obciązonego łącza ściezki"""
        return max((self.link_load(hop) / self.cap(hop)
                    for hop in self.topo.path_ports(path)), default=0.0)

    def select_path(self, flow, src, dst, video=False):
        """Wybór ściezki dla przepływu wg POLICY """
        paths = self.paths[(src, dst)]

        if POLICY == "rr":
            i = self.rr.get((src, dst), 0)
            self.rr[(src, dst)] = i + 1
            return paths[i % len(paths)]

        if POLICY == "openqos":
            # bez rezerwacji tymczasowej i bez pending - artykuł nie ma takich mechanizmów
            if video:
                return self.qos_route(src, dst)
            if OPENQOS_BE == "single":
                return paths[0]      # dosłownie: jedna najkrótsza ścieżka (Floodlight 2012)
            shortest = [p for p in paths if len(p) == len(paths[0])]
            return shortest[zlib.crc32(repr(flow).encode()) % len(shortest)]

        candidates = paths
        if POLICY == "qos":
            if video:
                vpath = self.topo.video_path(src, dst)
                if self.class_load(vpath, "video") < SPILL:   # tło jest policjowane meterem
                    candidates = [vpath]
            else:
                free = [p for p in paths if not self.touches_reserved(p)]
                # miękka rezerwa: best-effort wchodzi na rezerwę do (100 - R)% łącza
                shared = [p for p in paths if self.touches_reserved(p) and self.fits(p)]
                candidates = (free + shared) or paths

        # LLLB: ściezka z najmniej obciązonym wąskim gardłem
        best = min(candidates, key=self.path_load)

        cls = "video" if video else "be"
        if LAYERS < 2:
            for hop in self.topo.path_ports(best):   # dotychczasowy hack (baseline warstwy 1)
                self.link_bps[hop] = self.link_bps.get(hop, 0.0) + 500_000
                self.class_bps.setdefault(hop, {"video": 0.0, "be": 0.0})[cls] += 500_000
        else:
            est = VIDEO_EST_BPS if video else self.est_be
            if flow[0] == in_proto.IPPROTO_ICMP:   # ping: pomijalna przepływność
                est = 0
            exp = time.time() + PENDING_TTL
            for hop in self.topo.path_ports(best):
                self.pending.setdefault(hop, []).append((cls, est, exp))
        return best

    # ---------- wariant D: OpenQoS ----------
    def link_cost(self, hop):
        """c_ij = g_ij + d_ij; d_ij = 1 (hop), g_ij wg wzoru (5) z T = zmierzony ruch, B = pojemność"""
        traffic, cap = self.link_bps.get(hop, 0.0), self.cap(hop)
        g = (traffic - CONG_THRESH * cap) / traffic if traffic > CONG_THRESH * cap else 0.0
        return CONG_WEIGHT * g + 1      # uwaga: g < 0,3, więc przy wadze 1 dodatkowy hop zawsze przeważa

    def qos_route(self, src, dst):
        """CSP (3) rozwiązany dokładnie na ścieżkach kandydujących (zamiast heurystyki LARAC):
        min koszt wśród ścieżek o długości <= Dmax; remis -> pierwsza z listy (najkrótsza, najmniejszy dpid)"""
        paths = self.paths[(src, dst)]
        dmax = len(paths[0]) - 1 + DMAX_SLACK
        feasible = [p for p in paths if len(p) - 1 <= dmax] or paths
        return min(feasible, key=lambda p: sum(self.link_cost(h) for h in self.topo.path_ports(p)))

    def _congestion_events(self):
        """Stan przeciążenia każdego łącza; zmiana stanu -> przeniesienie przepływów QoS.
        (1) łącze luźne staje się przeciążone; (2) łącze przeciążone jest luźne przez DECONG_PERIODS okresów"""
        changed = []
        for hop in self.link_peer:
            util = self.link_bps.get(hop, 0.0) / self.cap(hop)
            st = self.cong.setdefault(hop, {"congested": False, "clear": 0})
            if util > CONG_THRESH:
                if not st["congested"]:
                    st["congested"] = True
                    changed.append(f"{self._hop_name(hop)} congested {util:.0%}")
                st["clear"] = 0
            elif st["congested"]:
                st["clear"] += 1
                if st["clear"] >= DECONG_PERIODS:
                    st["congested"], st["clear"] = False, 0
                    changed.append(f"{self._hop_name(hop)} clear")
        if changed:
            self._flush_video_flows(", ".join(changed))

    def _flush_video_flows(self, reason):
        """Usunięcie reguł wszystkich przepływów wideo na wszystkich przełącznikach; następny pakiet
        każdego z nich trafi jako Packet-In i dostanie trasę policzoną na świeżych kosztach"""
        flows = [f for f, cls in self.flow_class.items() if cls == "video"]
        for flow in flows:
            self.active.pop(flow, None)      # wymuszenie nowego wyboru przy Packet-In
            for dp in self.datapaths.values():
                ofp, parser = dp.ofproto, dp.ofproto_parser
                dp.send_msg(parser.OFPFlowMod(
                    datapath=dp, command=ofp.OFPFC_DELETE, priority=70,
                    out_port=ofp.OFPP_ANY, out_group=ofp.OFPG_ANY,
                    match=self._flow_match(parser, flow)))
        self.logger.info("OpenQoS reroute: %s -> %d QoS flows flushed", reason, len(flows))

    def _hop_name(self, hop):
        return f"{self.topo.names[hop[0]]}:{hop[1]}->{self.topo.names[self.link_peer[hop]]}"


    # ---------- ARP ----------
    def _handle_arp(self, datapath, in_port, pkt_arp):
        """Obsługa pakietów ARP"""
        self._learn(pkt_arp.src_ip, pkt_arp.src_mac, datapath.id, in_port)

        if pkt_arp.opcode != arp.ARP_REQUEST or pkt_arp.src_ip == pkt_arp.dst_ip:
            return  # Ignorowanie pakietów ARP, które nie są zapytaniem

        gw_ip, _ = self.topo.gateways[datapath.id]
        host = self.topo.hosts.get(pkt_arp.dst_ip)

        if pkt_arp.dst_ip == gw_ip:
            mac = GW_MAC
        elif host is not None and host.dpid == datapath.id and host.mac:
            mac = host.mac
        else:
            return  # Zapytanie o adres spoza tego przełącznika

        self.logger.debug("ARP %s asks for %s -> %s", pkt_arp.src_ip, pkt_arp.dst_ip, mac)

        self._send_arp(datapath, in_port, arp.ARP_REPLY, mac, pkt_arp.dst_ip, pkt_arp.src_mac, pkt_arp.src_ip)


    def _learn(self, ip, mac, dpid, port):
        """Sprawdzenie hosta z ruchu względem topologii; uzupełnienie MAC, jeśli go nie ma."""
        if ip == "0.0.0.0":
            return  # ARP probe (sprawdzanie duplikatu adresu) - nie ma jeszcze adresu

        host = self.topo.hosts.get(ip)
        if host is None or (host.dpid, host.port) != (dpid, port):
            self.logger.warning("Unexpected host %s/%s on %s port %d",
                                ip, mac, self.topo.names[dpid], port)
            return

        if host.mac != mac:
            if host.mac:
                self.logger.warning("MAC of %s changed: %s -> %s", ip, host.mac, mac)
            host.mac = mac
            self._install_host_rule(dpid, ip, mac, port)

    def _send_arp(self, datapath, out_port, opcode, src_mac, src_ip, dst_mac, dst_ip):
        """Wysyłanie pakietu ARP"""
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        eth_dst = "ff:ff:ff:ff:ff:ff" if opcode == arp.ARP_REQUEST else dst_mac

        pkt = packet.Packet()
        pkt.add_protocol(ethernet.ethernet(dst=eth_dst, src=src_mac,
                                            ethertype=ether_types.ETH_TYPE_ARP))

        pkt.add_protocol(arp.arp(opcode=opcode, src_mac=src_mac, src_ip=src_ip,
                                    dst_mac=dst_mac, dst_ip=dst_ip))
        pkt.serialize()
        actions = [parser.OFPActionOutput(out_port)]
        datapath.send_msg(parser.OFPPacketOut(datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER,
                                            in_port=ofproto.OFPP_CONTROLLER,
                                            actions=actions, data=pkt.data))

    def _flow_key(self, pkt, ip_pkt):
        """(protokół, IP src, IP dst, port src, port dst); porty None, gdy ich brak (ICMP)"""
        src_port = None
        dst_port = None

        l4 = pkt.get_protocol(tcp.tcp) or pkt.get_protocol(udp.udp)
        if l4 is not None:
            src_port = l4.src_port
            dst_port = l4.dst_port
        return (ip_pkt.proto, ip_pkt.src, ip_pkt.dst, src_port, dst_port)

    def _flow_match(self, parser, flow):
        """OFPMatch dla przepływu"""
        proto, src, dst, src_port, dst_port = flow
        fields = {"eth_type": ether_types.ETH_TYPE_IP, "ip_proto": proto,
                  "ipv4_src": src, "ipv4_dst": dst}
        if proto == in_proto.IPPROTO_TCP:
            fields.update(tcp_src=src_port, tcp_dst=dst_port)
        elif proto == in_proto.IPPROTO_UDP:
            fields.update(udp_src=src_port, udp_dst=dst_port)
        return parser.OFPMatch(**fields)

    def _route_flow(self, datapath, in_port, pkt, ip_pkt, data, dst_edge):
        """Nowy przepływ do obcej podsieci: wybór ścieżki, reguły na każdym hopie, Packet-Out"""
        src_edge = datapath.id
        flow = self._flow_key(pkt, ip_pkt)
        video = (ip_pkt.tos >> 2) == VIDEO_DSCP
        now = time.time()

        cached = self.active.get(flow)
        if cached is not None and now - cached[1] < 2:
            # Pakiet z tego samego przepływu przed instalacją reguły - ta sama ścieżka
            path = cached[0]
            new = False
        else:
            loads = [self.path_load(p) for p in self.paths[(src_edge, dst_edge)]]
            self.flow_class[flow] = "video" if video else "be"
            self.flow_last[flow] = now
            path = self.select_path(flow, src_edge, dst_edge, video)
            self.active[flow] = (path, now)
            new = True
        hops = self.topo.path_ports(path)

        # Reguły od końca ścieżki do początku
        for dpid, out_port in reversed(hops):
            dp = self.datapaths.get(dpid)
            if dp is None:
                self.logger.warning("Switch %s not connected - flow %s dropped",
                                    self.topo.names[dpid], flow)
                return
            parser = dp.ofproto_parser
            meter = out_port if (POLICY == "qos" and not video
                                 and (dpid, out_port) in self.topo.reserved) else None
            self.add_flow(dp, 70, self._flow_match(parser, flow),
                          [parser.OFPActionOutput(out_port)], idle_timeout=10, meter_id=meter)


        # Pierwszy pakiet przyszedł do kontrolera, więc trzeba go samodzielnie wysłać dalej
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        datapath.send_msg(parser.OFPPacketOut(
            datapath=datapath, buffer_id=ofproto.OFP_NO_BUFFER, in_port=in_port,
            actions=[parser.OFPActionOutput(hops[0][1])], data = data))

        if new:
            self.logger.info("Flow %s -> %s (%s, loads %s)", flow,
                             " -> ".join(self.topo.names[d] for d in path),
                             "video" if video else "be",
                             " ".join(f"{l:.0%}" for l in loads))

    def _monitor(self):
        """Co 1 s: zapytanie o statystyki portów do każdego połączonego przełącznika"""
        while True:
            for datapath in list(self.datapaths.values()):
                parser = datapath.ofproto_parser
                ofproto = datapath.ofproto
                datapath.send_msg(parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY))
                datapath.send_msg(parser.OFPFlowStatsRequest(datapath))

            busy = [f"{self.topo.names[d]}:{p}->{self.topo.names[self.link_peer[(d, p)]]} "
                    f"{bps / 1e6:.2f}Mb/s {bps / self.cap((d, p)):.0%}"
                    for (d, p), bps in sorted(self.link_bps.items()) if bps > 100_000]
            if busy:
                self.logger.info("Links: %s", ", ".join(busy))

            now = time.time()
            self.active = {f: v for f, v in self.active.items() if now - v[1] < 2}
            self.pending = {h: [e for e in l if e[2] > now] for h, l in self.pending.items()}
            for flow in [f for f, t in self.flow_last.items() if now - t > FLOW_CLASS_TTL]:
                del self.flow_last[flow]
                self.flow_class.pop(flow, None)
            if LAYERS >= 3 and POLICY == "qos":
                self._update_meters()
            if POLICY == "openqos":
                self._congestion_events()

            hub.sleep(1)

    def _update_meters(self):
        """Warstwa 3: dostosowanie stawki metera do mierzonego wideo"""
        for hop in self.topo.reserved:
            dp = self.datapaths.get(hop[0])
            if dp is None:
                continue
            rate = max(int(self.be_limit(hop) / 1000), 1)
            last = self.meter_rate.get(hop)
            if last is not None and abs(rate - last) < METER_STEP_KBPS:
                continue
            ofp, parser = dp.ofproto, dp.ofproto_parser
            dp.send_msg(parser.OFPMeterMod(
                datapath=dp, command=ofp.OFPMC_MODIFY,
                flags=ofp.OFPMF_KBPS | ofp.OFPMF_BURST, meter_id=hop[1],
                bands=[parser.OFPMeterBandDrop(rate=rate, burst_size=50)]))
            self.meter_rate[hop] = rate
            self.logger.info("Meter %s port %d: BE limit %d kb/s",
                             self.topo.names[hop[0]], hop[1], rate)

    def cap(self, hop):
        """Przepustowość łącza (dpid, port) z topologii [b/s]"""
        return self.topo.capacity.get(hop, 10_000_000)

