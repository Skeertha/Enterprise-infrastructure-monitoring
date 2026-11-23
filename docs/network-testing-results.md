# Network Monitoring – Testing Results

## 1. Overview

This document records the automated testing results for the network monitoring components in the Enterprise Infrastructure Monitoring project.

## 2. Network Collector Coverage

| Collector | Test coverage |
|---|---|
| TCPCollector | Connection success, connection errors, invalid settings and connection configuration |
| IPCollector | IPv4, IPv6, reachable and unreachable targets, IP metadata |
| DNSCollector | Successful and failed hostname resolution, duplicate address handling |
| NetworkInterfaceCollector | Interface details, missing interfaces and missing interface statistics |

## 3. Automated Test Execution

Test command:

```powershell
python -m pytest tests/test_optional_collectors.py -v
```

Latest verified result:
- Tests collected: 48
- Tests passed: 48
- Tests failed: 0

## 4. Full Project Test Suite

Test command:

```powershell
python -m pytest tests -v
```

Latest verified result:
- Tests collected: 81
- Tests passed: 81
- Tests failed: 0
- Execution time: 3.27 seconds
- Python version: 3.15.2

## 5. Manual Network Troubleshooting

The following checks were performed using Windows PowerShell:

| Test | Observed result |
|---|---|
| Network interface inspection | Wi-Fi adapter Up |
| Gateway connectivity | 0% packet loss |
| Public IP connectivity | 0% packet loss |
| DNS resolution | Successful |
| TCP port 443 | Successful |
| TCP port 81 | Connection unsuccessful |
| Invalid hostname | NXDOMAIN |
| Reserved documentation IP | 100% packet loss |

## 6. Tools and Technologies

- Python 3.15.2
- pytest
- PowerShell
- TCP/IP
- ICMP
- DNS
- SQLite

## 7. Conclusion

The project includes automated tests for TCP connectivity, IP reachability, DNS resolution and network interface monitoring.

Additional edge-case tests validate connection configuration, IPv6 metadata, missing interface statistics and duplicate DNS address handling.

Manual troubleshooting exercises were also performed to compare successful and unsuccessful network operations with the behavior covered by the automated tests.