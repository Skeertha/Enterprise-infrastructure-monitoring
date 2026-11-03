# FRR BGP and OSPF Routing Lab

## Overview
A three-router routing lab built with FRRouting (FRR) in separate Linux network namespaces.

## Environment
- FRRouting: 10.5.1
- Platform: Ubuntu on WSL2
- Tools: Linux network namespaces, veth interfaces, iproute2, vtysh

## Topology

| Router | Loopback | Autonomous System |
|---|---|---:|
| R1 | 1.1.1.1/32 | 65001 |
| R2 | 2.2.2.2/32 | 65002 |
| R3 | 3.3.3.3/32 | 65003 |

| Link | Address on first router | Address on second router |
|---|---|---|
| R1–R2 | R1: 10.12.12.1/30 | R2: 10.12.12.2/30 |
| R2–R3 | R2: 10.23.23.1/30 | R3: 10.23.23.2/30 |

## Protocol Configuration

### OSPF
OSPF was enabled on all three routers. The transit networks and loopback interfaces were advertised in area 0.

Verification:
```bash
sudo ip netns exec R1 vtysh -N R1 -c "show ip ospf neighbor"
sudo ip netns exec R2 vtysh -N R2 -c "show ip ospf neighbor"
sudo ip netns exec R3 vtysh -N R3 -c "show ip ospf neighbor"











```

### BGP
External BGP was configured between R1 (AS 65001), R2 (AS 65002), and R3 (AS 65003).

Verification:
```bash
for r in R1 R2 R3; do
    echo "===== $r BGP ====="
    sudo ip netns exec "$r" vtysh -N "$r" -c "show ip bgp summary"
done
```

Result: Both eBGP sessions were established.

## Connectivity Tests

IPv4 forwarding was enabled on R2 to allow traffic to transit between R1 and R3.

```bash
sudo ip netns exec R2 sysctl -w net.ipv4.ip_forward=1
sudo ip netns exec R1 ping -c 4 3.3.3.3
sudo ip netns exec R3 ping -c 4 1.1.1.1
```

Result:
- R1 to R3 loopback: 4/4 packets received.
- R3 to R1 loopback: 4/4 packets received.
- Packet loss: 0% in both tests.

## Evidence Summary
- Three isolated router namespaces configured.
- Two OSPF adjacencies established.
- Two eBGP sessions established across three autonomous systems.
- BGP and OSPF routes verified in router tables.
- Bidirectional loopback connectivity verified with ping.

## Scope Notes
This lab demonstrates routing protocol configuration and verification in a Linux-based virtual environment. It does not represent production network deployment. MPLS and SONiC/SAI are not covered by this lab.
