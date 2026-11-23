# TCP/IP Troubleshooting Lab

> Note: This document records manual Windows PowerShell networking exercises. These are separate from the automated Python network collector tests documented in `network-testing-results.md`.

## Lab 1: IP Configuration and Network Interface Troubleshooting

### Objective

Inspect Windows network interfaces and identify their IP configuration using PowerShell.

### Tool

Windows PowerShell

### Exercise 1: Display IP configuration

Run:

```powershell
ipconfig /all
```

Observe:
- Network adapter name
- IPv4 address
- Subnet mask
- Default gateway
- DNS servers
- Physical (MAC) address

### Exercise 2: Display network interfaces

Run:

```powershell
Get-NetAdapter
```

Observe:
- Interface name
- Interface status
- Link speed
- MAC address

### Exercise 3: Display IP addresses

Run:

```powershell
Get-NetIPAddress
```

Observe:
- IP address
- Address family (IPv4 or IPv6)
- Interface alias
- Prefix length

### Exercise 4: Troubleshooting questions

1. Which network interface is currently connected?
2. Does the interface have an IPv4 address?
3. Is a default gateway configured?
4. Which DNS servers are configured?
5. Are any adapters disconnected or disabled?

### Expected outcome

Understand how to inspect local network configuration and identify common interface or IP configuration issues.

### Safety note

Do not publish your private IP addresses, MAC addresses, or other personal network details in public GitHub documentation.

### Lab 1 - Exercise 2: Observations

Command executed:

```powershell
Get-NetAdapter
```

Results:

- Wi-Fi adapter: Up
- Wi-Fi link speed: 72.2 Mbps
- Ethernet adapter: Disconnected
- Ethernet link speed: 0 bps

Conclusion:

The Wi-Fi network adapter is active. The Ethernet adapter is disconnected, which is expected when a wired connection is not in use.

### Lab 1 - Exercise 5: Gateway Connectivity Test

Command:

```powershell
ping <default-gateway>
```

Results:
- Packets sent: 4
- Packets received: 4
- Packet loss: 0%
- Minimum response time: 1 ms
- Maximum response time: 52 ms
- Average response time: 15 ms

Conclusion:

The default gateway responded successfully to all ICMP echo requests. No packet loss was observed during this test.

### Lab 1 - Exercise 6: Public IP Connectivity

Command:

```powershell
ping 8.8.8.8
```

Results:
- Packets sent: 4
- Packets received: 4
- Packet loss: 0%
- Minimum latency: 32 ms
- Maximum latency: 438 ms
- Average latency: 136 ms

Conclusion:

The public IP address responded to all four ICMP requests. Internet IP reachability was successful. One response showed higher latency, indicating variation during the test.

### Lab 1 - Exercise 7: DNS Resolution

Command:

```powershell
nslookup google.com
```

Results:
- Hostname: google.com
- DNS query: Successful
- IPv4 address: Resolved
- IPv6 address: Resolved
- DNS server reverse name: Unidentified

Conclusion:

DNS resolution successfully returned both IPv4 and IPv6 addresses. The DNS server name was not identified, but this did not prevent successful resolution.

### Lab 1 - Exercise 8: TCP Connectivity Test

Command:

```powershell
Test-NetConnection google.com -Port 443
```

Results:
- Destination: google.com
- Destination port: 443
- Network interface: Wi-Fi
- TCP connection: Successful
- TcpTestSucceeded: True

Conclusion:

The computer successfully established a TCP connection to the destination on port 443. This confirms TCP connectivity to the tested HTTPS endpoint.

### Lab 2 - Exercise 1: TCP Connection Failure

Command:

```powershell
Test-NetConnection google.com -Port 81
```

Observed results:
- PingSucceeded: True
- TcpTestSucceeded: False
- Remote port: 81
- TCP connection: Failed

Analysis:

The destination responded to ICMP ping, but the TCP connection to port 81 was unsuccessful.

Possible causes:
- No service listening on the destination port
- Firewall restrictions
- Network security policies

Conclusion:

Successful ICMP reachability does not guarantee that a TCP service is accessible. Network troubleshooting should test both IP reachability and application-specific TCP connectivity.

### Lab 2 - Exercise 2: DNS Resolution Failure

Command:

```powershell
nslookup invalid-domain-12345.example
```

Observed result:
- DNS query: Failed
- Response: Non-existent domain
- Error: NXDOMAIN

Analysis:

The DNS resolver responded that the requested hostname does not exist.

Conclusion:

DNS resolution failures can occur because of incorrect hostnames or domains that do not exist. NXDOMAIN is a DNS response, not necessarily a network connectivity failure.

### Lab 2 - Exercise 3: IP Reachability Failure

Command:

```powershell
ping 192.0.2.1
```

Observed results:
- Packets sent: 4
- Packets received: 0
- Packet loss: 100%
- Response: Request timed out

Analysis:

The destination did not respond to ICMP echo requests. The address 192.0.2.1 belongs to the TEST-NET-1 range, reserved for documentation and examples. It is not intended to represent a real public destination..

Conclusion:

The test demonstrates how an IP reachability failure appears in ping output. A timeout alone does not prove that a real network is down because ICMP may be filtered.

## Overall Lab Conclusion

The exercises covered practical Windows network troubleshooting using PowerShell.

Key observations:
- Inspected network adapters and IP configuration.
- Verified gateway and public IP reachability.
- Tested DNS hostname resolution and NXDOMAIN responses.
- Validated TCP connectivity on ports 443 and 81.
- Compared successful ICMP reachability with unsuccessful TCP connectivity.
- Observed an ICMP timeout using a reserved documentation IP address.

These exercises provided practical exposure to Layer 2 and Layer 3 troubleshooting, DNS resolution and TCP connectivity.

Note: These manual exercises are separate from the automated Python collector tests.