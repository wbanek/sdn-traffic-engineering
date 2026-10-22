import os 

from topo import Topology
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls       
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4

TOPO_FILE = os.environ.get("TOPO_FILE", "/topologies/sdn.clab.yaml")

GW_MAC = "02:00:00:00:00:fe"  # Stały adres MAC bramy


class Fabric(app_manager.RyuApp):
    # Określenie używanej wersji protokołu OpenFlow (OpenFlow 1.3)
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Fabric, self).__init__(*args, **kwargs)
        self.topo = Topology(TOPO_FILE)
        self.logger.info("Topology %s: %d switches, %d hosts",
                        TOPO_FILE, len(self.topo.switches), len(self.topo.hosts))

        # Trasy domyślne: dla każdego przełącznika brzegowego drzewo najkrótszych ścieżek do niego
        self.routes = {edge: self.topo.next_hops_to(edge) for edge in self.topo.gateways}

        # Słownik przechowujący informacje o przełącznikach
        self.datapaths = {}

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
            match = parser.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                    ipv4_dst=(str(net.network_address), str(net.netmask)))
            actions = [parser.OFPActionOutput(next_hops[dpid])]
            self.add_flow(datapath, 50, match, actions)

        # Doręczenie do lokalnych hostów (MAC znany z topologii)
        for host in self.topo.hosts.values():
            if host.dpid == dpid and host.mac:
                self._install_host_rule(dpid, host.ip, host.mac, host.port)


    def add_flow(self, datapath, priority, match, actions, idle_timeout=0):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Tworzenie instrukcji (instructions) dla przepływu
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
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
            self.logger.debug("Unrouted IPv4 on %s port %d: %s -> %s",
                              self.topo.names[datapath.id], in_port, ipv4_pkt.src, ipv4_pkt.dst)

    # ---------- ARP ----------
    def _handle_arp(self, datapath, in_port, pkt_arp):
        """Obsługa pakietów ARP"""
        self._learn(pkt_arp.src_ip, pkt_arp.src_mac, datapath.id, in_port)

        if pkt_arp.opcode != arp.ARP_REQUEST or pkt_arp.src_ip == pkt_arp.dst_ip:
            return  # Ignorowanie pakietów ARP, które nie są zapytaniam
        
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
