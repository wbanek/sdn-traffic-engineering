import ipaddress
import re
from collections import deque

import yaml

RE_DPID = re.compile(r"datapath-id=([0-9a-fA-F]+)")
RE_PORT = re.compile(r"add-port br0 (\S+).*ofport_request=(\d+)")
RE_MAC = re.compile(r"ip link set dev \S+ address (\S+)")
RE_ADDR = re.compile(r"ip addr add (\S+) dev (\S+)")
RE_GW = re.compile(r"ip route replace default via (\S+)")
RE_TBF = re.compile(r"tc\s+qdisc\s+add\s+dev\s+(\S+)\s+root\s+tbf\s+rate\s+(\d+)(\w+)")
UNITS = {"kbit": 1_000, "mbit": 1_000_000, "gbit": 1_000_000_000}


class Host:
    def __init__(self, name, ip, mac, net, gw,dpid, port):
        self.name = name
        self.ip = ip
        self.mac = mac
        self.net = net
        self.gw = gw
        self.dpid = dpid
        self.port = port

    def __repr__(self):
        return f"{self.name}({self.ip} {self.mac} @ {self.dpid:#x}:{self.port})"

#  --- Wczytanie węzłów ---
class Topology:
    def __init__(self, path):
        with open(path) as f:
            data = yaml.safe_load(f)["topology"]

        self.switches = {}
        self.names = {}
        ports = {}
        host_cmds = {}
        self.capacity = {}

        for name, node in data["nodes"].items():
            text = "\n".join(node.get("exec") or [])
            m = RE_DPID.search(text)
            if m:
                dpid = int(m.group(1), 16)
                self.switches[name] = dpid
                self.names[dpid] = name
                ports[dpid] = {i: int(p) for i, p in RE_PORT.findall(text)}
                for dev, num, unit in RE_TBF.findall(text):
                    self.capacity[(dpid, ports[dpid][dev])] = int(num) * UNITS[unit.lower()]

            elif RE_ADDR.search(text):
                host_cmds[name] = text

        # --- Łącza ---
        self.adj = {d: {} for d in self.switches.values()}
        attach = {}
        for link in data.get("links", []):
            a, b = (tuple(e.split(":")) for e in link["endpoints"])
            for (here, here_if), (there, _) in ((a, b), (b, a)):
                if here not in self.switches:
                    continue
                here_dpid = self.switches[here]
                out_port = ports[here_dpid][here_if]
                if there in self.switches:
                    self.adj[here_dpid][self.switches[there]] = out_port
                elif there in host_cmds:
                    attach[there] = (here_dpid, out_port)

        # --- HOSTY ---
        self.hosts = {}
        self.gateways = {}
        for name, text in host_cmds.items():
            iface = ipaddress.ip_interface(RE_ADDR.search(text).group(1))
            mac = RE_MAC.search(text)
            gw = RE_GW.search(text).group(1)
            dpid, port = attach[name]
            h = Host(name, str(iface.ip), mac.group(1).lower() if mac else None,
                        iface.network, gw, dpid, port)
            self.hosts[h.ip] = h
            self.gateways[dpid] = (gw, iface.network)

        self.video_tree()

    def is_edge(self, dpid):
        return dpid in self.gateways

    def host_ports(self, dpid):
        return {h.port for h in self.hosts.values() if h.dpid == dpid}

    def edge_of(self, ip):
        addr = ipaddress.ip_address(ip)
        for dpid, (_, net) in self.gateways.items():
            if addr in net:
                return dpid
        return None

    def next_hops_to(self, dst):
        """Drzewo najkrótszych ścieżek do dst: {dpid: port wyjściowy w stronę dst}."""
        out, seen, queue = {}, {dst}, deque([dst])
        while queue:
            cur = queue.popleft()
            for nb in sorted(self.adj[cur]):
                if nb not in seen:
                    seen.add(nb)
                    out[nb] = self.adj[nb][cur]
                    queue.append(nb)
        return out

    def hop_count(self, src, dst):
        """Liczba hopów najkrótszej ścieżki src -> dst albo None, gdy brak połączenia"""
        dist = {src: 0}
        queue = deque([src])
        while queue:
            cur = queue.popleft()
            if cur == dst:
                return dist[cur]
            for nb in self.adj[cur]:
                if nb not in dist:
                    dist[nb] = dist[cur] + 1
                    queue.append(nb)
        return None

    def paths(self, src, dst, k=4, slack=1):
        """Do k ścieżek prostych src -> dst (listy dpid), najkrótsze najpierw.
        Brane są ścieżki o długości co najwyżej (najkrótsza + slack) hopów"""

        if src == dst:
            return [[src]]
        shortest = self.hop_count(src, dst)
        if shortest is None:
            return []
        limit = shortest + slack
        found = []

        def dfs(node, path):
            if node == dst:
                found.append(list(path))
                return
            if len(path) - 1 >= limit:
                return
            for nb in sorted(self.adj[node]):
                if nb not in path:
                    path.append(nb)
                    dfs(nb, path)
                    path.pop()

        dfs(src, [src])
        found.sort(key=lambda p: (len(p), p))
        return found[:k]

    def path_ports(self, path):
        """[(dpid, port wyjściowy), ...] dla każdego hopa ścieżki oprócz ostatniego"""
        return [(a, self.adj[a][b]) for a, b in zip(path, path[1:])]

    
    def _bfs_tree(self, root):
        """Drzewo najkrótszych ścieżek z korzenia: {węzeł: rodzic}; remis -> najpierw węzły
        tranzytowe, potem mniejszy dpid (łącza między przełącznikami brzegowymi zostają dla best-effort)"""
        parent, queue = {root: None}, deque([root])
        while queue:
            cur = queue.popleft()
            for nb in sorted(self.adj[cur], key=lambda d: (self.is_edge(d), d)):
                if nb not in parent:
                    parent[nb] = cur
                    queue.append(nb)
        return parent

    def _prune(self, parent, terminals):
        """Zostawia tylko gałęzie prowadzące do węzłów z terminals"""
        keep = set()
        for x in terminals:
            while x is not None and x not in keep:
                keep.add(x)
                x = parent[x]
        return {n: p for n, p in parent.items() if n in keep}

    @staticmethod
    def _tree_path(parent, a, b):
        """Jedyna ścieżka a -> b w drzewie (przez wspólnego przodka)"""
        up, x = [], a
        while x is not None:
            up.append(x)
            x = parent[x]
        down, x = [], b
        while x not in up:
            down.append(x)
            x = parent[x]
        return up[:up.index(x) + 1] + down[::-1]

    def video_tree(self):
        """Rezerwa wideo: drzewo zakorzenione w węźle tranzytowym (jeśli brak - w dowolnym),
        wybranym tak, by best-effort miał jak najwięcej ścieżek poza rezerwą,
        a ścieżki wideo były jak najmniej wydłużone"""
        edges = sorted(self.gateways)
        roots = [d for d in sorted(self.switches.values()) if not self.is_edge(d)]
        roots = roots or sorted(self.switches.values())

        best = None
        for root in roots:
            parent = self._prune(self._bfs_tree(root), edges)
            links = {frozenset((c, p)) for c, p in parent.items() if p is not None}
            free, stretch = [], 0
            for a in edges:
                for b in edges:
                    if a == b:
                        continue
                    stretch += len(self._tree_path(parent, a, b)) - len(self.paths(a, b)[0])
                    free.append(sum(1 for p in self.paths(a, b)
                                    if not any(frozenset(l) in links for l in zip(p, p[1:]))))
            key = (min(free, default=0), sum(free), -stretch, -root)
            if best is None or key > best[0]:
                best = (key, root, parent, links)

        _, self.vroot, self.vparent, self.vlinks = best
        # łącza rezerwy jako skierowane (dpid nadawcy, port) - do meterów i pomiarów
        self.reserved = {(a, self.adj[a][b]) for l in self.vlinks
                         for a, b in (tuple(l), tuple(l)[::-1])}

    def video_path(self, a, b):
        """Ścieżka wideo między przełącznikami brzegowymi (po drzewie rezerwy)"""
        return self._tree_path(self.vparent, a, b)
