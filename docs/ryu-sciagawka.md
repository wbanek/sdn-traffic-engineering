# Ryu: ściągawka (`@set_ev_cls`, zdarzenia, skróty)

Wersja: Ryu 4.34, OpenFlow 1.3. Źródło dekoratora: `ryu/controller/handler.py`.

## Czym jest `@set_ev_cls`
**set_ev_cls** = *set event class*. Dekorator mówi Ryu: „tę metodę wywołaj, gdy przyjdzie zdarzenie typu X, a przełącznik jest w fazie Y”.

```python
def set_ev_cls(ev_cls, dispatchers=None)
```
| Argument | Co to | Uwagi |
|---|---|---|
| `ev_cls` | klasa zdarzenia (*event class*) | jedna albo lista: `[EventA, EventB]` |
| `dispatchers` | faza połączenia z przełącznikiem, w której zdarzenie ma trafić do metody | jedna, lista albo `None` (= wszystkie fazy) |

Dekorator niczego nie wywołuje. Dopisuje do metody atrybut `callers`, a `ryu-manager` przy ładowaniu aplikacji rejestruje ją jako handler. Sygnatura handlera: `def nazwa(self, ev):`.

## `dispatchers`: fazy połączenia OpenFlow
```
TCP connect → HELLO ⇄ HELLO → FEATURES_REQUEST → FEATURES_REPLY → SET_CONFIG → praca
             └─ HANDSHAKE ─┘  └──────── CONFIG ────────┘                   └─ MAIN ─┘
rozłączenie → DEAD
```
| Stała | Faza | Typowe użycie |
|---|---|---|
| `HANDSHAKE_DISPATCHER` | wymiana Hello, uzgadnianie wersji OF | prawie nigdy w aplikacji |
| `CONFIG_DISPATCHER` | Ryu wysłał Features Request i czeka na odpowiedź | `EventOFPSwitchFeatures`: reguła table-miss i reguły proaktywne |
| `MAIN_DISPATCHER` | normalna praca | `PacketIn`, `PortStatus`, odpowiedzi na statystyki, `FlowRemoved` |
| `DEAD_DISPATCHER` | przełącznik się rozłączył | sprzątanie stanu |

> **Pułapka:** gdy zdarzenie zmienia fazę, Ryu dopasowuje handler według fazy **sprzed** zmiany. `SwitchFeatures` przenosi przełącznik z CONFIG do MAIN, więc handler z `MAIN_DISPATCHER` nigdy się nie wywoła. Musi być `CONFIG_DISPATCHER`. Zły dispatcher nie daje błędu, handler po prostu milczy.

> `ryu-manager --verbose` loguje zdarzenie tylko wtedy, gdy jakaś aplikacja je konsumuje.

## `ev_cls`: najważniejsze zdarzenia
Klasy w `ryu.controller.ofp_event` powstają automatycznie: komunikat `OFPPacketIn` daje zdarzenie `EventOFPPacketIn`.

| Zdarzenie | Dispatcher | Kiedy | Zastosowanie |
|---|---|---|---|
| `EventOFPSwitchFeatures` | CONFIG | przełącznik się przedstawił (dpid, liczba tabel) | reguły proaktywne, table-miss, ARP |
| `EventOFPPacketIn` | MAIN | pakiet bez pasującej reguły trafił do kontrolera | ARP proxy bramy, decyzja LLLB/C dla nowego przepływu |
| `EventOFPPortStatus` | MAIN | port w górę lub w dół | wykrycie awarii łącza |
| `EventOFPPortStatsReply` | MAIN | odpowiedź na `OFPPortStatsRequest` | obciążenie łączy (Δtx_bytes) |
| `EventOFPFlowStatsReply` | MAIN | odpowiedź na `OFPFlowStatsRequest` | ruch per reguła |
| `EventOFPFlowRemoved` | MAIN | reguła wygasła (wymaga `OFPFF_SEND_FLOW_REM`) | sprzątanie stanu przepływów |
| `EventOFPErrorMsg` | dowolny | przełącznik odrzucił komunikat | debug złego matcha lub akcji |
| `EventOFPStateChange` | `[MAIN, DEAD]` | zmiana fazy | lista aktywnych przełączników |

Odpowiedzi `...StatsReply` przychodzą tylko na Twoje zapytania (np. pętla co 1 s).

## Co jest w `ev`
```python
msg      = ev.msg                  # odebrany komunikat OpenFlow
dp       = msg.datapath            # obiekt przełącznika
dpid     = dp.id                   # unikalny numer przełącznika
ofp      = dp.ofproto              # stałe protokołu (OFPP_*, OFPFC_* ...)
parser   = dp.ofproto_parser       # klasy komunikatów (OFPMatch, OFPFlowMod ...)
in_port  = msg.match['in_port']    # (PacketIn) port wejściowy
```

## Szkielet aplikacji
```python
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub

class Fabric(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.datapaths = {}
        hub.spawn(self._monitor)                 # osobny wątek: pętla statystyk

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def features(self, ev):
        dp = ev.msg.datapath; ofp = dp.ofproto; parser = dp.ofproto_parser
        match = parser.OFPMatch()                # pusty match = wszystko
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst))

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state(self, ev):
        if ev.state == MAIN_DISPATCHER: self.datapaths[ev.datapath.id] = ev.datapath
        else:                           self.datapaths.pop(ev.datapath.id, None)

    def _monitor(self):
        while True:
            for dp in self.datapaths.values():
                dp.send_msg(dp.ofproto_parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY))
            hub.sleep(1)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats(self, ev):
        for s in ev.msg.body:
            self.logger.debug("dp=%x port=%d tx_bytes=%d", ev.msg.datapath.id, s.port_no, s.tx_bytes)

    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status(self, ev):
        down = ev.msg.desc.state & ev.msg.datapath.ofproto.OFPPS_LINK_DOWN
        self.logger.info("dp=%x port=%d %s", ev.msg.datapath.id, ev.msg.desc.port_no, "DOWN" if down else "UP")

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        ...  # ARP proxy / wybór ścieżki
```
> Handlery działają w lekkich wątkach eventlet: zamiast `time.sleep()` używaj `hub.sleep()`, inaczej zablokujesz cały kontroler.

## Słowniczek skrótów
| Skrót | Rozwinięcie | Znaczenie |
|---|---|---|
| `ev` | event | obiekt zdarzenia przekazywany do handlera |
| `cls` | class | klasa (tu: klasa zdarzenia) |
| `OFP` | OpenFlow Protocol | prefiks wszystkiego z OpenFlow |
| `ofproto` | OpenFlow protocol | moduł ze stałymi danej wersji (np. `ofproto_v1_3`) |
| `parser` | `ofproto_parser` | klasy komunikatów do budowania i parsowania |
| `dp` | datapath | przełącznik OpenFlow (OVS `br0`) |
| `dpid` | datapath ID | 64-bitowy identyfikator przełącznika |
| `msg` | message | komunikat OpenFlow |
| `xid` | transaction ID | numer wiążący zapytanie z odpowiedzią |
| `OFPT_*` | OFP Type | typ komunikatu (`OFPT_PACKET_IN`, `OFPT_FLOW_MOD`) |
| `OFPP_*` | OFP Port | porty specjalne: `CONTROLLER`, `FLOOD`, `ANY`, `IN_PORT` |
| `OFPFC_*` | OFP Flow Command | `ADD`, `MODIFY`, `DELETE` w `OFPFlowMod` |
| `OFPFF_*` | OFP Flow Flag | np. `SEND_FLOW_REM`: powiadom o wygaśnięciu reguły |
| `OFPIT_*` | OFP Instruction Type | `APPLY_ACTIONS`, `GOTO_TABLE`, `METER` |
| `OFPAT_*` | OFP Action Type | typy akcji (output, set_field, set_queue, group) |
| `OFPCML_NO_BUFFER` | Controller Max Length, no buffer | wysyłaj do kontrolera cały pakiet, bez buforowania |
| `OFP_NO_BUFFER` / `buffer_id` | – | czy pakiet jest zbuforowany w przełączniku (Packet-Out) |
| `OFPR_*` | OFP Reason | powód Packet-In: `NO_MATCH`, `ACTION` |
| `OFPPS_*` | OFP Port State | np. `LINK_DOWN` |
| `OXM` | OpenFlow eXtensible Match | format pól matcha w OF1.3 (`eth_type`, `ipv4_dst`, `ip_dscp`) |
| `FlowMod` | Flow Modification | dodanie, zmiana lub usunięcie reguły |
| `PacketIn` / `PacketOut` | – | pakiet z przełącznika do kontrolera / z kontrolera do przełącznika |
| table-miss | – | reguła priorytet 0 z pustym matchem: co zrobić, gdy nic nie pasuje |
| `hub` | – | warstwa nad eventlet (wątki, `sleep`) w Ryu |
