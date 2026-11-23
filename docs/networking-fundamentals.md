\# Networking Fundamentals: OSI Layer 2, Layer 3 and TCP/IP



\## 1. Overview



This document explains the networking concepts used in the Enterprise Infrastructure Monitoring project, including network interfaces, IP reachability, DNS resolution and TCP connectivity.



It also documents the relationship between OSI networking layers and the monitoring capabilities implemented in Python.



\## 2. OSI Model



The OSI model describes network communication through seven layers.



| Layer | Name | Purpose |

|---|---|---|

| 7 | Application | Network services such as HTTP and DNS |

| 6 | Presentation | Data formatting, encoding and encryption |

| 5 | Session | Establishes and manages communication sessions |

| 4 | Transport | TCP and UDP communication |

| 3 | Network | IP addressing and routing |

| 2 | Data Link | MAC addressing and Ethernet frames |

| 1 | Physical | Cables, signals and physical connectivity |



\## 3. Layer 2 - Data Link



Layer 2 handles communication within a local network.



Important concepts:

\- MAC addresses

\- Ethernet frames

\- Network interface status

\- Switching

\- VLANs



\### Project implementation



The NetworkInterfaceCollector uses Python's psutil library to inspect network interfaces.



It collects:

\- Interface name

\- MAC address

\- IPv4 and IPv6 addresses

\- Interface up/down status

\- Network interface speed



A configured interface that is down is reported as a WARNING.



Note: This collector reads local interface information. It does not currently perform Ethernet frame capture, VLAN inspection or switch-level monitoring.



\## 4. Layer 3 - Network



Layer 3 handles IP addressing and communication between networks.



Important concepts:

\- IPv4 and IPv6

\- ICMP

\- Routing

\- Default gateways

\- Subnet masks



\### Project implementation



The IPCollector checks IP reachability using the system ping command.



It records:

\- Target IP address

\- IP version

\- ICMP reachability status

\- Success or failure message



A failed ping indicates that the target did not respond to the ICMP check. Firewalls, ICMP filtering, routing problems or an unavailable host may cause this result.



Note: This is a basic reachability check, not a complete routing-table or network-path analysis.



\## 5. DNS Resolution



DNS translates hostnames into IP addresses.



\### Project implementation



The DNSCollector uses Python's socket.getaddrinfo() function to resolve hostnames.



It records:

\- Hostname

\- Resolved IP addresses

\- Number of unique addresses

\- Resolution status



Duplicate resolved addresses are removed from the reported results.



A resolution failure is reported as CRITICAL.



\## 6. TCP Connectivity



TCP provides reliable, connection-oriented communication.



\### Project implementation



The TCPCollector uses socket.create\_connection() to test whether a TCP connection can be established with a configured host and port.



It handles:

\- Connection timeout

\- DNS resolution errors

\- Connection refused errors

\- Other socket errors

\- Response-time classification



The collector also uses configured connection timeouts and target ports.



\## 7. Troubleshooting Workflow



When a network check fails, use this sequence:



1\. Check whether the network interface is up.

2\. Verify the target IP address.

3\. Test IP reachability using ping.

4\. Check DNS resolution for the hostname.

5\. Test TCP connectivity to the required port.

6\. Review monitoring results and error messages.

7\. Record the findings for further investigation.



Useful Windows PowerShell commands include:



```powershell

Get-NetIPConfiguration

Get-NetAdapter

ipconfig /all

ping 8.8.8.8

nslookup google.com

Test-NetConnection google.com -Port 443

```



\## 8. Current Implementation Scope



| Capability | Status |

|---|---|

| Network interface monitoring | Implemented |

| IPv4/IPv6 reachability | Implemented |

| DNS resolution | Implemented |

| TCP connectivity | Implemented |

| Automated collector tests | Implemented |

| Packet capture | Not implemented |

| VLAN inspection | Not implemented |

| Routing table analysis | Not implemented |

| BGP/OSPF | Practised in a separate FRRouting lab |

| MPLS | Not completed |



The complete project test suite currently contains 81 passing tests, including network collector coverage.



\## 9. Technologies



\- Python 3.15.2

\- TCP/IP

\- ICMP

\- DNS

\- psutil

\- socket

\- SQLite

\- pytest

\- Windows PowerShell



\## 10. Conclusion



The project provides basic network infrastructure monitoring across selected Layer 2, Layer 3, DNS and TCP connectivity checks.



These checks help identify interface, reachability, name-resolution and connection issues. Automated tests validate normal behavior and selected edge cases.



Advanced capabilities such as packet capture, VLAN inspection and routing-table analysis remain outside the current implementation scope.

