# Status projektu (ostatnia aktualizacja: 2026-09-29)                                
                                                                                    
## Działa                                                                            
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
                                                                                    
## Nie działa / nie zrobione                                                         
- Limity pasma (`tc tbf`) — FAZA 2, następny krok                                    
- Warianty B/C (SDN, Ryu) — nierozpoczęte                                            
                                                                                    
## Znane pułapki (żeby nie odkrywać ponownie)                                        
- `rate:` pod `links` w Containerlab nie istnieje — limity przez `tc` (skrypt)       
- Web UI na porcie 8090 bywa nieaktualny — weryfikować przez `containerlab inspect` /
`docker exec`                                                                          
- Obraz frr:9.0.1 NIE ładuje /etc/frr/frr.conf (docker-start bez vtysh -b) — config  
przez ospfd.conf                                                                       
- Host ma trasę default od dockera (eth0 mgmt) — bramę dodawać przez `ip route       
replace`                                                                               
- ECMP z hashem L3 (domyślny) nie rozrzuca przepływów między parą podsieci — wymagany
sysctl L4                                                                              
                                                                                    
## Następny krok                                                                     
- Faza 2: limity `tc tbf` (10 Mb/s leaf-spine, 100 Mb/s host-leaf) 